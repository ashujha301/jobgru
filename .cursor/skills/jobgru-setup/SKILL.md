---
name: jobgru-setup
description: Jobgru first-time setup, help, and health check. Use when the user says Jobgru setup, first time, configure sheet, update sheet link, add resume, Jobgru help, or Jobgru check. Handles venv, pip install, config/sheet.json, resume PDF placement, and sheet profile writes — user only manually copies the Google Sheet template and runs gcloud auth.
---

# Jobgru Setup

Onboarding skill for new users. **Never ask users to edit `config/sheet.json` or other code files manually** — the agent writes config after the user pastes their sheet URL.

The user only does **two things manually**:

1. Copy the [starter template](https://docs.google.com/spreadsheets/d/18TQRl1dh0Ivdk8YbxkdiWb6__XkpHM32T1ohPTuMJ_4/edit) → **File → Make a copy** → tab must stay **`Job Applications`**
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

If unclear, run **check** first and report what's missing.

---

## Help mode

Print this exactly (adapt template URL from `config/sheet.json.example` → `template_sheet_url` if needed):

```
Jobgru — quick start
════════════════════

YOU do (2 steps):
  1. Open template → File → Make a copy → keep tab name "Job Applications"
     Template: https://docs.google.com/spreadsheets/d/18TQRl1dh0Ivdk8YbxkdiWb6__XkpHM32T1ohPTuMJ_4/edit
  2. Terminal auth (sheet owner Google account):
     gcloud auth login --enable-gdrive-access --update-adc

AGENT does (say "Jobgru setup" in chat):
  • Create Python venv + install dependencies
  • Save your sheet URL to config/sheet.json
  • Set resume link + name on sheet (O2, Q2–Q7) if you provide them
  • Save resume PDF to data/resumes/ if you attach one
  • Run Jobgru check

After setup:
  • Say "Jobgru check" to verify everything
  • Use prompts/jobgru-run.md for your first job search

Details: README.md | Troubleshooting: docs/SETUP.md
```

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
