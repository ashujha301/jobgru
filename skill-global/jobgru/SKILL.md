---
name: jobgru
description: Jobgru global router — setup, help, check, filter, delete, mcp, and job-search pipeline. Use when the user says /jobgru, Jobgru setup, Jobgru help, Jobgru check, Jobgru filter, Jobgru delete, Jobgru mcp, or asks for a job search. All engine commands run from JOBGRU_HOME (~/.jobgru), not the current workspace.
---

# Jobgru (global router)

**JOBGRU_HOME:** `~/.jobgru` (set by installer). If missing, fall back to repo root when opened as a project.

All shell commands use `$JOBGRU_HOME/.venv/bin/python $JOBGRU_HOME/scripts/...` with `cwd=$JOBGRU_HOME`.

## Route by intent

| User says | Read and follow |
| --- | --- |
| setup, first time, sheet URL, add resume | `$JOBGRU_HOME/.cursor/skills/jobgru-setup/SKILL.md` → **setup** |
| help | Run `$JOBGRU_HOME/.venv/bin/python $JOBGRU_HOME/scripts/jobgru_help.py` |
| check | Run `$JOBGRU_HOME/.venv/bin/python $JOBGRU_HOME/scripts/jobgru_check.py --json` |
| mcp, browser setup, playwright | Run `$JOBGRU_HOME/.venv/bin/python $JOBGRU_HOME/scripts/jobgru_mcp.py status` or `jobgru mcp install` |
| filter, saved filters, job search filters | `$JOBGRU_HOME/.cursor/skills/jobgru-setup/SKILL.md` → **filter** |
| delete rows, remove jobs from sheet | `$JOBGRU_HOME/.cursor/skills/jobgru-setup/SKILL.md` → **delete** |
| job search, find jobs, pipeline | `$JOBGRU_HOME/.cursor/skills/jobgru/SKILL.md` (+ leadgru, atsscore after Phase 1) |

Resolve `JOBGRU_HOME`:
```bash
test -d ~/.jobgru/scripts && echo ~/.jobgru || pwd
```

## Browser contract

| Agent | Browser tools |
| --- | --- |
| **Cursor** | Cursor Browser (browser_navigate, browser_snapshot, browser_click, …) |
| **Claude Code / Codex** | Playwright MCP — install once: `jobgru mcp install` |
| **No browser tools** | Run sheet writes + ATS only; report that LeadGru/job-board phases were skipped |

User completes MFA/CAPTCHA manually in the visible browser window.

## Quick commands

```bash
jobgru help
jobgru check
jobgru mcp install
jobgru filter prompt
jobgru delete --rows 42-44
```

## Manual user steps (never automate)

1. Copy Google Sheet template → File → Make a copy (tab: `Job Applications`)
2. `gcloud auth login --enable-gdrive-access --update-adc`
3. Copy resume PDF to `$JOBGRU_HOME/data/resumes/` (global install does not copy PDFs automatically)

Template: https://docs.google.com/spreadsheets/d/18TQRl1dh0Ivdk8YbxkdiWb6__XkpHM32T1ohPTuMJ_4/edit
