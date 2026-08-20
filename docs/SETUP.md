# Jobgru — setup reference and troubleshooting

**Start here:** [README.md](../README.md) — one `curl | bash` command runs the interactive setup wizard.

This doc is for troubleshooting and technical detail.

---

## Interactive installer wizard

```bash
curl -fsSL https://raw.githubusercontent.com/ashujha301/jobgru/main/install.sh | bash
```

The installer prompts you through (each step skippable):

1. Engine + venv + router skills + `jobgru` CLI + Playwright MCP
2. **gcloud** — offers Homebrew install on macOS if missing
3. **Google auth** — `gcloud auth login --enable-gdrive-access --update-adc`
4. **Sheet** — opens template in browser, waits for your copy URL, validates tab/headers/formulas/write
5. **LinkedIn** — `jobgru mcp login` (Codex/Claude; Cursor uses built-in browser)
6. **`jobgru check`** — should show READY (resume optional)

Skip the wizard (engine only):

```bash
./install.sh --local /path/to/repo --skip-setup
```

Verify a configured sheet without full check:

```bash
~/.jobgru/.venv/bin/python ~/.jobgru/scripts/jobgru_verify_sheet.py
```

---

## Quick reference: chat commands

| Command | Prompt file |
| --- | --- |
| Jobgru setup | [prompts/setup.md](../prompts/setup.md) |
| Jobgru help | [prompts/help.md](../prompts/help.md) |
| Jobgru check | [prompts/check.md](../prompts/check.md) |
| Jobgru mcp | `jobgru mcp install` / [docs/SETUP.md#browser-and-mcp](#browser-and-mcp) |
| Jobgru filter | [prompts/filter.md](../prompts/filter.md) |
| Jobgru delete | [prompts/delete.md](../prompts/delete.md) |

Agent skill: [.cursor/skills/jobgru-setup/SKILL.md](../.cursor/skills/jobgru-setup/SKILL.md)

---

## Health check CLI

```bash
.venv/bin/python scripts/jobgru_check.py          # human-readable
.venv/bin/python scripts/jobgru_check.py --json   # for agents
```

Exit code `0` = ready; `1` = fix failures.

### What each check verifies

| ID | Checks |
| --- | --- |
| `python` | Python 3.10+ |
| `venv` | `.venv` exists |
| `deps` | `googleapiclient`, `pypdf` installed |
| `gcloud_cli` | `gcloud` on PATH |
| `config` | `config/sheet.json` with real spreadsheet ID |
| `sheet_tab` | Tab `Job Applications` exists |
| `sheet_headers` | Row 1 headers A1:J1 match template |
| `sheet_formulas` | Summary COUNT formulas M2:M7 |
| `sheet_dropdown` | Status dropdown on D2 |
| `sheet_auth` | Sheets API read works |
| `sheet_write` | Sheets API write test |
| `resume` | PDF in `data/resumes/` (**warn** if missing) |
| `resume_manifest` | `manifest.json` synced |
| `install_mode` | `global (~/.jobgru)` or `repo` |
| `browser_tools` | Agent should confirm browser MCP / Cursor Browser (**warn**) |

---

## Terminal agents (Claude Code, Codex)

### Browser and MCP {#browser-and-mcp}

| Agent | Browser | Setup |
| --- | --- | --- |
| **Cursor** | Cursor Browser (built-in) | None |
| **Claude Code** | Playwright MCP → Chrome | `jobgru mcp install` |
| **Codex** | Playwright MCP → Chrome | `jobgru mcp install` |

```bash
jobgru mcp install    # registers Playwright for Claude + Codex
jobgru mcp status     # verify registration
```

Manual equivalent:

```bash
claude mcp add playwright -- npx @playwright/mcp@latest
codex mcp add playwright -- npx @playwright/mcp@latest
```

[install.sh](../install.sh) runs `jobgru mcp install` automatically when `claude` / `codex` CLIs are on PATH.

**Why LeadGru skipped but jobs worked:** Jobgru can find listings via public web search without a browser. LeadGru searches LinkedIn *people* and requires a **signed-in** Playwright browser session.

### LinkedIn login for LeadGru (Codex / Claude Code — one time)

The installer offers this automatically. To do it manually:

```bash
jobgru mcp login    # opens LinkedIn login in the Jobgru browser profile
```

Sign in (MFA ok), then **press ENTER in the terminal** — don't close the browser yourself. Session saves to `~/.jobgru/browser-profile`.

In-chat fallback (new Codex/Claude session):

```text
Use the playwright MCP tool browser_navigate to open https://www.linkedin.com/login — do not use any built-in browser skill.
Wait while I sign in manually. Stop until I say I'm logged in.
```

Sign in in the browser window (MFA ok). Then say **"I'm logged in to LinkedIn"**.

**Backfill leads** for rows already on the sheet:

```text
LeadGru backfill rows 42-43 — use Playwright MCP with my signed-in LinkedIn session.
```

Without browser tools, Jobgru still runs sheet writes + ATS; LeadGru is skipped.

### Global install commands

```bash
curl -fsSL https://raw.githubusercontent.com/ashujha301/jobgru/main/install.sh | bash
jobgru help
jobgru check
jobgru mcp install
jobgru filter
jobgru filters
jobgru delete --rows 42-44
jobgru update
jobgru uninstall
```

Engine directory: `~/.jobgru`

**Resume (global install):** PDFs are not copied by the installer. Copy manually:

```bash
cp ~/path/to/resume.pdf ~/.jobgru/data/resumes/
```

Or attach PDF during **Jobgru setup** in chat.

---

## Template sheet

**Starter template:** https://docs.google.com/spreadsheets/d/18TQRl1dh0Ivdk8YbxkdiWb6__XkpHM32T1ohPTuMJ_4/edit

File → Make a copy copies dropdowns, colors, column widths, and formulas.

Tab must stay **`Job Applications`**. Spreadsheet title can be anything.

### Summary formulas (column M)

| Row | Label | Formula |
| --- | --- | --- |
| M2 | Total Applied | `=COUNTA(D2:D989)` |
| M3 | Interviews | `=COUNTIF(D2:D989, "Interview")` |
| M4 | Rejections | `=COUNTIF(D2:D989, "Rejected")` |
| M5 | Total Selected | `=COUNTIF(D2:D989, "Selected")` |
| M6 | Total Assesments | `=COUNTIF(D3:D989, "Assesment")` |
| M7 | Total Contacted | `=COUNTIF(D4:D989, "Contacted")` |

**Status dropdown (column D):** Applied, Rejected, Interview, Selected, Assesment, Contacted, To Apply.

Jobgru writes new rows with Status `to apply` (lowercase). Change to `To Apply` from the dropdown after applying.

---

## Google auth

### Recommended

```bash
gcloud auth login --enable-gdrive-access --update-adc
```

### Does not work

| Command | Problem |
| --- | --- |
| `gcloud auth login` alone | `403 insufficient scopes` |
| `gcloud auth application-default login --scopes=.../spreadsheets` | *"This app is blocked"* |

Alternatives: [scripts/SHEETS-API-SETUP.md](../scripts/SHEETS-API-SETUP.md) (OAuth desktop client, service account)

---

## Config (agent-managed)

Users should **not** edit `config/sheet.json` manually. The agent writes it via:

```bash
.venv/bin/python scripts/sheet_config.py set --url "https://docs.google.com/spreadsheets/d/..." --name "Your Name"
```

---

## Resume (optional — ATS)

- Attach PDF during **Jobgru setup**, or say "add resume" with attachment
- Agent saves to `$JOBGRU_HOME/data/resumes/` (global: `~/.jobgru/data/resumes/`)
- Global install does **not** copy PDFs from the repo — copy manually or attach in chat
- No PDFs → ATS skipped automatically

See [data/resumes/README.md](../data/resumes/README.md)

---

## Prompt filters (pipeline runs)

Copy and edit [prompts/jobgru-run.md](../prompts/jobgru-run.md), or run `jobgru filter` for the full catalog.

| Filter | Examples |
| --- | --- |
| Count | 3, 10, up to 30 |
| Boards | LinkedIn only, LinkedIn + Wellfound |
| Role/domain | AI Engineer, Backend Engineer |
| Similar roles | include Full Stack if stack matches |
| Location | Bangalore, India |
| Work | remote / hybrid / onsite |
| Experience | 0–4 years |
| Skills | Python, FastAPI, LLMs |
| Exclude | Data Scientist, internships |
| Posting age | 30 days |
| Staffing agencies | yes / no |
| ATS scoring | yes / no |

---

## Column layout

| Col | Header | Phase |
| --- | --- | --- |
| A | Company Name | Jobgru writes |
| B | Position | Jobgru writes |
| C | Apply link | Jobgru writes |
| D | Status | Jobgru writes (`to apply`) |
| E | Date Applied | Jobgru writes |
| F | Details if any | Jobgru writes (incl. Skills) |
| G | Leads | LeadGru writes |
| H | Add note Message | LeadGru writes |
| I | ATS score | ATSScore writes |
| J | Suggestions on Resume | ATSScore writes |
| L–Q | Summary, templates | Template / user once |

Details format (column F): `Pay: …, Exp: …, … | Skills: Python, FastAPI, …`

---

## CLI reference

| Command | Purpose |
| --- | --- |
| `scripts/jobgru_check.py` | Full setup health check |
| `scripts/sheet_config.py set --url …` | Write config |
| `scripts/sheets_write.py test --cleanup` | Auth smoke test |
| `scripts/sheets_write.py read --range "A2:H500"` | Read for dedupe |
| `scripts/ats_score.py score --all` | ATS scoring |
| `scripts/init_template_sheet.py` | Regenerate shareable template (maintainers) |

---

## Troubleshooting

| Problem | Fix |
| --- | --- |
| Jobgru check fails on `gcloud_cli` | Install [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) |
| Jobgru check fails on `config` | Run Jobgru setup with sheet URL |
| Jobgru check fails on `sheet_tab` | Rename tab to `Job Applications` |
| Jobgru check fails on headers/formulas/dropdown | Recopy template |
| Sheet not updating | Re-run gcloud auth command |
| Jobs added but no Leads | LinkedIn blocked — run [leadgru-run.md](../prompts/leadgru-run.md) |
| No ATS scores | Add resume via setup or [atsscore-run.md](../prompts/atsscore-run.md) |
| Browser sheet edits vanish | Expected — use Sheets API scripts only |

---

## Architecture: keep scripts, not MCP

| Layer | Tool |
| --- | --- |
| Sheet writes | `scripts/sheets_write.py` |
| Job boards + LinkedIn | Agent browser |
| ATS | `scripts/ats_score.py` |

Optional Google Drive MCP for read-only inspection only. Each user runs their own Google auth.

---

## Sharing the template (maintainers)

```bash
.venv/bin/python scripts/init_template_sheet.py --trash-old OLD_TEMPLATE_ID
```

Share new template as **Viewer**. Users **File → Make a copy**.

---

## Multi-agent use

See [AGENTS.md](../AGENTS.md). Skills in `.cursor/skills/` are portable markdown for any agent.
