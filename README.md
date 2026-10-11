# claude-devlog

A readable daily summary of what you built with Claude Code, project by project, plus a one-command view of the last thing done in each project.

- **Nothing is missed.** The source is every Claude Code session transcript (`~/.claude/projects`): terminal, Desktop, SDK-driven apps and subagents.
- **Always up to date.** An async Stop hook archives a compact digest of the session to `~/.claude/devlog/sessions/` after every turn. Every report also re-scans all changed transcripts first, so the report is complete even if the hook missed something.
- **Durable.** The archive survives Claude Code's transcript cleanup.
- **Commits come from git.** Pulled with `git log`, filtered to your own email.

## Install

```
/plugin marketplace add Rylaa/claude-devlog
/plugin install devlog@claude-devlog
```

Requires only `python3` (3.9+). No other dependencies.

## Usage

| Command | Output |
|---|---|
| `/devlog:devlog` | Today's summary: what was done per project, plus open items |
| `/devlog:devlog yesterday` · `/devlog:devlog 2026-10-09` | Summary of a specific day |
| `/devlog:devlog week` | Last 7 days, built from the daily summaries |
| `/devlog:devlog week <project>` | What was built in one project over the last 7 days |
| `/devlog:devlog 2026-10-05..2026-10-11 <project>` | One project over any date range |
| `/devlog:devlog last` | The last thing done in each project |
| `/devlog:devlog last <project>` | Latest state of one project |

Asking "what did we do today?" or "what was last done in project X?" works too.

Daily summaries are saved to `~/.claude/devlog/daily/<date>.md`.

You can also get the raw report from the terminal, without Claude:

```
python3 skills/devlog/devlog.py today      # yesterday | 2026-10-09 | 7d | A..B, optional [project]; last [project]; sync
```

## How it works

`skills/devlog/devlog.py` extracts from each transcript the user prompts, Claude's final reply per turn, edited files, commits and PRs. It archives them as one small JSON file per session. Reports are built from the archive by day and by project, with worktrees grouped under their main repository. Repeated one-shot automation calls that start with the same template (for example `claude -p` judges or classifiers) are hidden; the report only shows how many there were.

Test: `python3 skills/devlog/test_devlog.py`
