#!/usr/bin/env python3
"""Claude Code geliştirme günlüğü.

Transcript'leri (~/.claude/projects) oturum başına küçük özetlere arşivler
(~/.claude/devlog/sessions) ve gün/proje bazlı rapor basar.

  devlog.py hook                 Stop hook: stdin'deki oturumu arşivler
  devlog.py sync                 değişen tüm transcript'leri arşivler
  devlog.py [today|yesterday|YYYY-MM-DD|7d|A..B] [proje]   o günün/aralığın raporu
  devlog.py last [proje]         her projede en son ne yapıldı
"""
import json, os, re, subprocess, sys
from collections import Counter
from datetime import datetime, timedelta, date
from pathlib import Path

HOME = Path.home()
PROJECTS = HOME / ".claude/projects"
ARCHIVE = HOME / ".claude/devlog/sessions"
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
SKIP_PREFIX = ("<task-notification", "<teammate-message", "<local-command", "[Request interrupted",
               "This session is being continued", "Context handoff", "Caveat:")
COMMIT_RE = re.compile(r"^\[[^\]\s]+(?: \(root-commit\))? ([0-9a-f]{7,40})\] (.+)$", re.M)
PR_RE = re.compile(r"https://github\.com/[\w.-]+/[\w.-]+/pull/\d+")
REMINDER_RE = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)


def clean_prompt(text):
    text = REMINDER_RE.sub("", text).strip()
    m = re.search(r"<command-name>/?(.*?)</command-name>", text)
    if m:
        args = re.search(r"<command-args>(.*?)</command-args>", text, re.S)
        return ("/" + m.group(1) + " " + (args.group(1) if args else "")).strip()
    return "" if text.startswith(SKIP_PREFIX) else text


def result_text(content):
    if isinstance(content, str):
        return content
    return "\n".join(b.get("text", "") for b in content or [] if isinstance(b, dict))


def parse(path, main):
    """Transcript'ten (zaman, tür, değer) olayları çıkarır. Yan zincirden yalnız dosya/commit/PR."""
    events, meta, wanted = [], {}, {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            # hız: ilgilenmediğimiz tool_result satırlarını parse etme (dosya içerikleri dev olabilir)
            if '"tool_result"' in line and not any(i in line for i in wanted):
                continue
            if not ('"ai-title"' in line or '"user"' in line or '"assistant"' in line):
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("type") not in ("user", "assistant", "ai-title"):
                continue
            if rec["type"] == "ai-title":
                meta["title"] = rec.get("aiTitle")
                continue
            meta.setdefault("cwd", rec.get("cwd"))
            if rec.get("gitBranch"):
                meta["branch"] = rec["gitBranch"]
            t, side = rec.get("timestamp"), (not main) or rec.get("isSidechain")
            content = (rec.get("message") or {}).get("content")
            if rec["type"] == "user":
                if isinstance(content, list):
                    for b in content:
                        if b.get("type") == "tool_result" and b.get("tool_use_id") in wanted:
                            out = result_text(b.get("content"))
                            if wanted.pop(b["tool_use_id"]) == "commit":
                                events += [(t, "commit", f"{s[:7]} {m}") for s, m in COMMIT_RE.findall(out)]
                            else:
                                events += [(t, "pr", u) for u in dict.fromkeys(PR_RE.findall(out))]
                if side or rec.get("isMeta"):
                    continue
                text = content if isinstance(content, str) else "\n".join(
                    b.get("text", "") for b in content or [] if b.get("type") == "text")
                text = clean_prompt(text)
                if text:
                    events.append((t, "prompt", text))
            else:
                for b in content or []:
                    if b.get("type") == "text" and not side and b.get("text", "").strip():
                        events.append((t, "result", b["text"].strip()))
                    elif b.get("type") == "tool_use":
                        inp = b.get("input") or {}
                        if b.get("name") in EDIT_TOOLS:
                            p = inp.get("file_path") or inp.get("notebook_path")
                            if p:
                                events.append((t, "file", p))
                        elif b.get("name") == "Bash":
                            cmd = inp.get("command", "")
                            if "git commit" in cmd:
                                wanted[b.get("id")] = "commit"
                            elif "gh pr create" in cmd:
                                wanted[b.get("id")] = "pr"
    return events, meta


_project_cache = {}


def project_of(cwd):
    if not cwd:
        return "?"
    if cwd in _project_cache:
        return _project_cache[cwd]
    name = None
    try:  # worktree'ler ana repo adına toplanır
        common = subprocess.run(["git", "-C", cwd, "rev-parse", "--path-format=absolute", "--git-common-dir"],
                                capture_output=True, text=True, timeout=5).stdout.strip()
        if common:
            name = Path(common).parent.name
    except Exception:
        pass
    if not name:
        m = re.search(r"/\.t3/worktrees/([^/]+)", cwd)
        if "/.t3/scratch/" in cwd:
            name = "scratch"
        elif m:
            name = m.group(1)
        else:
            name = Path(cwd.split("/.claude/worktrees/")[0]).name or cwd
    _project_cache[cwd] = name
    return name


def build(main_path):
    events, meta = parse(main_path, True)
    for sub in main_path.with_suffix("").glob("subagents/**/*.jsonl"):
        events += parse(sub, False)[0]
    events.sort(key=lambda e: e[0] or "")
    cwd = meta.get("cwd") or ""
    turns, cur = [], None
    for t, kind, val in events:
        if kind == "prompt" or cur is None:
            cur = {"t": t, "prompt": val if kind == "prompt" else "(devam)", "files": [], "commits": [], "prs": [], "result": ""}
            turns.append(cur)
            if kind == "prompt":
                continue
        if kind == "result":
            cur["result"] = val
        elif kind == "file":
            val = val[len(cwd) + 1:] if cwd and val.startswith(cwd + "/") else val
            if val not in cur["files"]:
                cur["files"].append(val)
        else:
            cur[kind + "s"].append(val)
    return {"id": main_path.stem, "project": project_of(cwd), "cwd": cwd, "title": meta.get("title"),
            "branch": meta.get("branch"), "turns": turns}


def archive(main_path):
    out = ARCHIVE / (main_path.stem + ".json")
    newest = max([main_path.stat().st_mtime] + [p.stat().st_mtime for p in main_path.with_suffix("").glob("subagents/**/*.jsonl")])
    if out.exists() and out.stat().st_mtime >= newest:
        return
    d = build(main_path)
    if "t3code-claude-title" in d["cwd"] or not d["turns"]:
        return  # T3'ün başlık üretme oturumları ve boş oturumlar gürültü
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(f".{os.getpid()}.tmp")  # hook ve sync aynı anda yazabilir
    tmp.write_text(json.dumps(d, ensure_ascii=False))
    tmp.replace(out)


def sync():
    for p in PROJECTS.glob("*/*.jsonl"):
        try:
            archive(p)
        except Exception as e:  # tek bozuk transcript raporu durdurmasın
            print(f"[devlog] atlandı {p.name}: {e}", file=sys.stderr)


def local(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()


def short(s, n):
    s = " ".join(s.split())
    return s if len(s) <= n else s[:n] + "…"


def sessions():
    """(gerçek, otomasyon) oturumlar. Aynı şablonla başlayan >=3 tek turluk, dosyasız oturum otomasyon sayılır
    (claude -p yargıçları, T3 branch adı üretimi, tek başına /clear vb.)."""
    ss = [json.loads(p.read_text()) for p in ARCHIVE.glob("*.json")]
    oneshot = lambda s: len(s["turns"]) == 1 and not any(s["turns"][0][k] for k in ("files", "commits", "prs"))
    key = lambda s: s["turns"][0]["prompt"][:50]
    n = Counter(key(s) for s in ss if oneshot(s))
    auto = lambda s: oneshot(s) and n[key(s)] >= 3
    return [s for s in ss if not auto(s)], [s for s in ss if auto(s)]


def fmt_turn(tu):
    lines = [f"- {local(tu['t']):%m-%d %H:%M} ▸ {short(tu['prompt'], 200)}"]
    if tu["result"]:
        lines.append(f"  → {short(tu['result'], 300)}")
    if tu["files"]:
        more = f" (+{len(tu['files']) - 8})" if len(tu["files"]) > 8 else ""
        lines.append(f"  dosyalar: {', '.join(tu['files'][:8])}{more}")
    lines += [f"  commit: {c}" for c in tu["commits"]] + [f"  PR: {u}" for u in tu["prs"]]
    return lines


def git_commits(cwds, start, end):
    """Aralıktaki kendi commit'lerin, git'in kendisinden (transcript'te görünmeyen `commit -q`, subagent commit'leri dahil)."""
    seen = {}
    for cwd in cwds:
        git = lambda *a: subprocess.run(["git", "-C", cwd, *a], capture_output=True, text=True, timeout=10).stdout
        try:
            email = git("config", "user.email").strip()
            out = git("log", "--all", f"--author={email}", f"--since={start} 00:00", f"--until={end + timedelta(days=1)} 00:00",
                      "--date=format:%m-%d %H:%M", "--format=%h %ad %s") if email else ""
        except Exception:
            continue
        for line in out.splitlines():
            seen.setdefault(line.split(" ", 1)[0], line)
    return list(seen.values())


def report(start, end, only=None):
    by_proj, real, auto = {}, *sessions()
    in_range = lambda tu: tu["t"] and start <= local(tu["t"]).date() <= end
    if only:
        real = [s for s in real if only.lower() in s["project"].lower()]
        auto = [s for s in auto if only.lower() in s["project"].lower()]
    for s in real:
        turns = [tu for tu in s["turns"] if in_range(tu)]
        if turns:
            by_proj.setdefault(s["project"], []).append((s, turns))
    hidden = Counter(s["project"] for s in auto if in_range(s["turns"][0]))
    label = (str(start) if start == end else f"{start} → {end}") + (f" · {only}" if only else "")
    out = [f"# Claude Code günlüğü — {label}", ""]
    if not by_proj:
        out.append("Bu aralıkta kayıt yok.")
    last = lambda item: max(tu["t"] for _, ts in item[1] for tu in ts)
    for proj, items in sorted(by_proj.items(), key=last, reverse=True):
        n = sum(len(ts) for _, ts in items)
        out.append(f"## {proj} — {len(items)} oturum, {n} istek, son: {local(last((proj, items))):%m-%d %H:%M}")
        commits = git_commits({s["cwd"] for s, _ in items if s["cwd"]}, start, end)
        if commits:
            out.append(f"git commit'leri ({len(commits)}): " + " | ".join(commits[:25]) + (" …" if len(commits) > 25 else ""))
        for s, ts in sorted(items, key=lambda x: x[1][0]["t"]):
            out.append(f"### {local(ts[0]['t']):%m-%d %H:%M} · {s['title'] or '(başlıksız)'} · {s['branch'] or '-'} · {s['cwd']}")
            for tu in ts:
                out += fmt_turn(tu)
        out.append("")
    if hidden:
        out.append("_Gizlenen tekrarlı otomasyon oturumları: " + ", ".join(f"{p} ({n})" for p, n in hidden.most_common()) + "_")
    return "\n".join(out)


def last_report(only=None, k=3):
    latest = {}
    for s in sessions()[0]:
        for tu in s["turns"]:
            if tu["t"]:
                latest.setdefault(s["project"], []).append((tu["t"], s, tu))
    out = ["# Projelerde en son ne yapıldı", ""]
    for proj, rows in sorted(latest.items(), key=lambda kv: max(r[0] for r in kv[1]), reverse=True):
        if only and only.lower() not in proj.lower():
            continue
        rows.sort(key=lambda r: r[0])
        s = rows[-1][1]
        out.append(f"## {proj} — son: {local(rows[-1][0]):%Y-%m-%d %H:%M} · {s['title'] or '(başlıksız)'} · {s['branch'] or '-'}")
        for _, _, tu in rows[-k:]:
            out += fmt_turn(tu)
        out.append("")
    return "\n".join(out)


def main(argv):
    arg = argv[0] if argv else "today"
    if arg == "hook":
        archive(Path(json.load(sys.stdin)["transcript_path"]))
        return
    sync()
    if arg == "sync":
        return
    if arg == "last":
        print(last_report(argv[1] if len(argv) > 1 else None))
        return
    today = date.today()
    if arg == "today":
        start = end = today
    elif arg == "yesterday":
        start = end = today - timedelta(days=1)
    elif re.fullmatch(r"\d+d", arg):
        start, end = today - timedelta(days=int(arg[:-1]) - 1), today
    elif ".." in arg:  # 2026-10-05..2026-10-11
        start, end = map(date.fromisoformat, arg.split(".."))
    else:
        start = end = date.fromisoformat(arg)
    print(report(start, end, argv[1] if len(argv) > 1 else None))


if __name__ == "__main__":
    main(sys.argv[1:])
