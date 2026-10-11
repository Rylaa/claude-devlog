"""python3 -I ~/.claude/skills/devlog/test_devlog.py — sahte transcript üzerinde parser kontrolü."""
import importlib.util, json, tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location("devlog", Path(__file__).with_name("devlog.py"))
devlog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(devlog)
devlog.project_of = lambda cwd: "demo"


def rec(t, typ, content, **kw):
    return json.dumps({"type": typ, "timestamp": f"2026-10-11T10:00:0{t}Z", "cwd": "/repo",
                       "gitBranch": "main", "message": {"role": typ, "content": content}, **kw})


with tempfile.TemporaryDirectory() as d:
    main = Path(d) / "s1.jsonl"
    main.write_text("\n".join([
        json.dumps({"type": "ai-title", "aiTitle": "Login ekranı"}),
        rec(1, "user", "login ekranını yap<system-reminder>gizli</system-reminder>"),
        rec(2, "assistant", [{"type": "tool_use", "id": "e1", "name": "Edit", "input": {"file_path": "/repo/a.swift"}}]),
        rec(3, "assistant", [{"type": "tool_use", "id": "c1", "name": "Bash", "input": {"command": "git commit -m x"}}]),
        rec(4, "user", [{"type": "tool_result", "tool_use_id": "c1", "content": "[main abc1234def] feat: login\n 1 file changed"}]),
        rec(5, "user", [{"type": "text", "text": "<task-notification>bitti</task-notification>"}]),
        rec(6, "assistant", [{"type": "text", "text": "Login ekranı hazır."}]),
        rec(7, "user", "<command-name>/review</command-name><command-args>son commit</command-args>"),
    ]))
    sub = Path(d) / "s1/subagents/agent-1.jsonl"
    sub.parent.mkdir(parents=True)
    sub.write_text(rec(8, "assistant", [{"type": "tool_use", "id": "e2", "name": "Write", "input": {"file_path": "/repo/b.swift"}}], isSidechain=True))

    s = devlog.build(main)
    t1, t2 = s["turns"]
    assert s["title"] == "Login ekranı" and s["branch"] == "main", s
    assert t1["prompt"] == "login ekranını yap", t1
    assert t1["files"] == ["a.swift"] and t1["commits"] == ["abc1234 feat: login"], t1
    assert t1["result"] == "Login ekranı hazır.", t1
    assert t2["prompt"] == "/review son commit" and t2["files"] == ["b.swift"], t2
    print("ok")
