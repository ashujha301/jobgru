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
| prompts, example prompt, job search prompt | Run `$JOBGRU_HOME/.venv/bin/python $JOBGRU_HOME/scripts/jobgru_prompts.py` or `jobgru prompts` |
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
| **Claude Code / Codex** | **Playwright MCP tools only** (`playwright.browser_navigate`, `browser_snapshot`, `browser_click`) — install once: `jobgru mcp install` |
| **No browser tools** | Run sheet writes + ATS only; report that LeadGru/job-board phases were skipped |

**Codex:** for LinkedIn/job-board browsing, call the **`playwright` MCP server tools directly** (`playwright.browser_navigate` etc.). Do NOT use the bundled browser-control skill / `node_repl` browser runtime — it is a different browser with no LinkedIn session. If `playwright` tools are not listed, tell the user to run `jobgru mcp install` and restart the Codex session.

The Playwright profile lives at `~/.jobgru/browser-profile` — LinkedIn login persists between sessions. Sign in once, reuse forever.

User completes MFA/CAPTCHA manually in the visible browser window.

**LinkedIn pacing is always on** (Jobgru LinkedIn Jobs + LeadGru). Read it in `$JOBGRU_HOME/.cursor/skills/jobgru/SKILL.md` and `leadgru/SKILL.md`. Default: **40s sleep before every LinkedIn navigate** except the first after lock; one LinkedIn tab; stop on CAPTCHA/rate-limit with no retries. LinkedIn has **no job-count cap**; LeadGru writes **at most 5 people + company people page**. Do not skip pacing because the user omitted “go slow”.

## Quick commands

```bash
jobgru help
jobgru check
jobgru mcp install
jobgru filter
jobgru prompts
jobgru delete --rows 42-44
```

## Manual user steps (never automate)

1. Copy Google Sheet template → File → Make a copy (tab: `Job Applications`)
2. `gcloud auth login --enable-gdrive-access --update-adc`
3. Copy resume PDF to `$JOBGRU_HOME/data/resumes/` (global install does not copy PDFs automatically)

Template: https://docs.google.com/spreadsheets/d/18TQRl1dh0Ivdk8YbxkdiWb6__XkpHM32T1ohPTuMJ_4/edit
