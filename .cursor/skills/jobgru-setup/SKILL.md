---
name: jobgru-setup
description: Jobgru first-time setup, help, and health check. Use when the user says Jobgru setup, first time, configure sheet, update sheet link, add resume, Jobgru help, or Jobgru check. Handles venv, pip install, config/sheet.json, resume PDF placement, and sheet profile writes — user only manually copies the Google Sheet template and runs gcloud auth.
---

# Jobgru Setup

Onboarding skill for new users. **Never ask users to edit `config/sheet.json` or other code files manually** — the agent writes config after the user pastes their sheet URL.

The user only does **two things manually**:

1. Copy the [starter template](https://docs.google.com/spreadsheets/d/18TQRl1dh0Ivdk8YbxkdiWb6__XkpHM32T1ohPTuMJ_4/edit) → **File → Make a copy** → tab must stay **`Job Applications`**
   - Template link is **viewer** — that is OK for copying only. **Do not** paste the template URL into Jobgru setup.
   - Your **copy** must be owned by you (**Editor/Owner**). Viewer-only access to someone else's sheet will not work.
   - `gcloud auth login` must use the **same Google account** that owns your copy.
2. Run in terminal: `gcloud auth login --enable-gdrive-access --update-adc`

Everything else is handled by this skill.

---

## Mode detection

| User says | Mode |
| --- | --- |
| "Jobgru setup", "first time", pasted sheet URL + name | **setup** |
| "update sheet", new sheet URL | **configure-sheet** |
| uploads resume PDF, "add resume" | **add-resume** |
| "Jobgru help" | **help** |
| "Jobgru check" | **check** |
| "Jobgru mcp", browser setup, playwright | **mcp** |
| "Jobgru filter", save/show filters | **filter** |
| "Jobgru delete", delete rows | **delete** |

If unclear, run **check** first and report what's missing.

---

## Help mode

Run and print output:

```bash
.venv/bin/python scripts/jobgru_help.py
```

Or terminal: `jobgru help`

Do not paraphrase — show the full command list from the script.

---

## MCP mode (browser for Claude Code / Codex)

Check status:

```bash
.venv/bin/python scripts/jobgru_mcp.py status
```

Install Playwright MCP for Claude + Codex:

```bash
jobgru mcp install
```

Explain to the user:
- **Cursor** uses built-in browser — no MCP step.
- **Claude Code / Codex** need Playwright MCP for LeadGru (LinkedIn people search).
- Job search can sometimes work via web search without browser; LeadGru always needs a live browser.

---

## Filter mode

Show saved filters:

```bash
.venv/bin/python scripts/jobgru_filters.py show
```

Save filters (example):

```bash
.venv/bin/python scripts/jobgru_filters.py set \
  --count 3 \
  --sources "LinkedIn Jobs" \
  --roles "Software Engineer,SWE AI" \
  --location "Bangalore" \
  --exclude-roles "Data Scientist,Data Engineer" \
  --note "Do not skip similar SWE roles if experience matches"
```

Print ready job-search prompt:

```bash
.venv/bin/python scripts/jobgru_filters.py prompt
```

If user gives filters in chat, parse them into `filter set` flags, save, then show `filter prompt` output for the next pipeline run.

---

## Delete mode

Ask which rows if not provided (single `42`, list `42,43,44`, or range `42-44`).

Preview first:

```bash
.venv/bin/python scripts/sheets_write.py delete-rows --rows "42-44" --dry-run
```

After user confirms, delete and compact:

```bash
.venv/bin/python scripts/sheets_write.py delete-rows --rows "42-44"
```

Or: `jobgru delete --rows 42-44`

Deleting rows shifts remaining data up — row numbers re-order automatically. Report `next_empty_row` from script output.

---

## Check mode

Run from project root:

```bash
.venv/bin/python scripts/jobgru_check.py --json
```

Parse JSON. For each check with `status: fail`:

- Show `id`, `message`, `fix`
- If `manual: true`, tell user they must do it (sheet copy or gcloud auth)
- If `fix_command` is set and not manual, offer to run it for them

For `status: warn` (usually `resume`), mention ATS is optional.

Report **READY** when `ready: true`, else **NOT READY** with numbered fix list.

Human-readable fallback:

```bash
.venv/bin/python scripts/jobgru_check.py
```

---

## Setup mode (automated steps — run in order)

All commands from **project root**.

### 1. Python environment

```bash
python3 -m venv .venv
.venv/bin/pip install -r scripts/requirements.txt
```

Skip steps that already pass in check.

### 2. Save sheet config

Parse spreadsheet ID from user's pasted URL:

```bash
.venv/bin/python scripts/sheet_config.py set --url "<SHEET_URL>" --name "<YOUR_NAME>" --resume-link "<RESUME_URL>"
```

If only URL given, omit optional flags. Tab is always `Job Applications`.

### 3. Apply profile to sheet (if name or resume link provided)

Requires gcloud auth. After config is saved:

```bash
.venv/bin/python -c "
from setup_sheet_profile import apply_user_profile
from sheet_config import get_spreadsheet_id, get_tab, get_resume_link_default, get_your_name
from sheets_write import sheets_service
svc = sheets_service()
apply_user_profile(svc, get_spreadsheet_id(), get_tab(),
    resume_link=get_resume_link_default(), your_name=get_your_name())
print('OK: O2 and Q2-Q7 updated')
"
```

If auth fails here, tell user to run gcloud command and continue after.

### 4. Save resume PDF (if user attached one in chat)

- Save to `data/resumes/<sanitized-filename>.pdf` (gitignored)
- Run: `.venv/bin/python scripts/ats_score.py sync`

### 5. Run check

```bash
.venv/bin/python scripts/jobgru_check.py --json
```

Report results. If only `sheet_auth` / `sheet_write` fail → user needs gcloud auth (step 2 manual).

---

## Configure-sheet mode

Same as setup steps 2–3–5 when user provides a new sheet URL. Do not recreate venv unless check fails `venv` or `deps`.

---

## Add-resume mode

1. Save uploaded PDF to `data/resumes/`
2. `.venv/bin/python scripts/ats_score.py sync`
3. Run check (resume should pass)

---

## Hard rules

- **Never** tell users to open or edit `config/sheet.json` — use `scripts/sheet_config.py set`
- **Never** use Cursor Browser to edit sheet cells — use `setup_sheet_profile.py` or Sheets API scripts
- After setup, point user to [prompts/jobgru-run.md](../../prompts/jobgru-run.md) for first pipeline run
- Tab name must be **`Job Applications`** (spreadsheet title can be anything)

---

## Reference files

| File | Purpose |
| --- | --- |
| [README.md](../../README.md) | User-facing quick start |
| [docs/SETUP.md](../../docs/SETUP.md) | Troubleshooting |
| [prompts/setup.md](../../prompts/setup.md) | Copy-paste setup prompt |
| [prompts/check.md](../../prompts/check.md) | Copy-paste check prompt |
| [scripts/jobgru_check.py](../../scripts/jobgru_check.py) | Health check CLI |
| [scripts/sheet_config.py](../../scripts/sheet_config.py) | Config read/write |
