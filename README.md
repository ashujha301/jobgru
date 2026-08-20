# Jobgru Automation

Find verified jobs, write them to your **Job Applications** Google Sheet, then automatically find LinkedIn contacts, outreach notes, and ATS resume scores — **one prompt, full pipeline**.

Works in **Cursor, Claude Code, Codex**, or any agent — install once, use `/jobgru` from any chat.

| Phase | Skill | What it does |
| --- | --- | --- |
| **Setup** | `jobgru-setup` | First-time setup, help, health check |
| **Phase 1 — Jobgru** | `jobgru` | Search boards → verify → append up to 50 jobs/run (LinkedIn max 25) |
| **Phase 2 — LeadGru** | `leadgru` | LinkedIn leads + notes (automatic, parallel) |
| **Phase 2b — ATSScore** | `atsscore` | Resume fit scores (Python, parallel) |

---

## First-time setup — one command

Run this in your terminal. The installer walks you through everything interactively:

```bash
curl -fsSL https://raw.githubusercontent.com/ashujha301/jobgru/main/install.sh | bash
```

**Private repo:** you need git access to `github.com/ashujha301/jobgru`.

### What the installer does (in order)

| Step | What happens | You do |
| --- | --- | --- |
| 1 | Installs engine, skills, CLI, Playwright MCP | Wait |
| 2 | Checks **Google Cloud SDK** (`gcloud`) | Install via Homebrew if offered, or install manually |
| 3 | **Google sign-in** | Press **Y** → browser opens → sign in with your Google account |
| 4 | **Google Sheet** | Press **Y** to open template → **File → Make a copy** → paste **your copy URL** |
| 5 | Verifies sheet (tab, headers, formulas, write test) | Fix and retry if it fails |
| 6 | **LinkedIn login** (Codex/Claude only) | Press **Y** → sign in → press **ENTER** in terminal |
| 7 | Runs **`jobgru check`** | Should show **READY** (resume optional) |

Every prompt accepts **skip** — you can finish later with `jobgru setup` / `jobgru mcp login`.

**Resume is optional during install.** Add it anytime:

```bash
cp your-resume.pdf ~/.jobgru/data/resumes/
```

Or in chat: `Jobgru add resume` (attach PDF).

### After install — first job search

**Codex / Claude Code:** start a **new session** (MCP tools load at session start).

```text
Find 3 software engineer jobs on LinkedIn in Bangalore. Add them to my Job Applications sheet.
```

Or open [prompts/jobgru-run.md](prompts/jobgru-run.md), fill filters, paste into chat.

### What a successful run looks like

- New rows in your **Job Applications** Google Sheet
- **ATSScore** filled (columns I & J) if resume is present
- **LeadGru** filled (Leads column) if LinkedIn login worked
- Run record saved at `~/.jobgru/data/runs/`

---

## Manual setup (fallback)

Use this if you skipped steps during install or use a non-interactive terminal.

<details>
<summary>Click to expand manual steps</summary>

### Prerequisites

- AI agent: **Cursor**, **Claude Code**, or **Codex CLI**
- **Google Cloud SDK** — [install](https://cloud.google.com/sdk/docs/install)
- Resume PDF (optional, for ATS)

### 1. Copy the Google Sheet template

1. Open: https://docs.google.com/spreadsheets/d/18TQRl1dh0Ivdk8YbxkdiWb6__XkpHM32T1ohPTuMJ_4/edit
2. **File → Make a copy** → tab must stay **`Job Applications`**
3. Save **your copy's URL** (not the template URL)

> Jobgru writes via **your Google account** (`gcloud auth`). That account must be **Editor/Owner** on the sheet.

| Situation | Jobgru can write? |
| --- | --- |
| Template link | No — copy only |
| Your copy after Make a copy | **Yes** (you are Owner) |
| Someone else's sheet as Viewer | No — need Editor |

### 2. Install Jobgru

```bash
curl -fsSL https://raw.githubusercontent.com/ashujha301/jobgru/main/install.sh | bash
```

Engine-only (skip wizard): append nothing — wizard runs by default. Developers: `./install.sh --local . --skip-setup`

### 3. Google auth

```bash
gcloud auth login --enable-gdrive-access --update-adc
```

### 4. Connect sheet

```bash
jobgru setup --url "https://docs.google.com/spreadsheets/d/YOUR_COPY_ID/edit"
```

### 5. LinkedIn (Codex / Claude Code)

```bash
jobgru mcp login
```

### 6. Verify

```bash
jobgru check   # should show READY
```

</details>

Update after each release: **`jobgru update`**

---

## Browser setup by agent

| Agent | Browser for LeadGru | Setup |
| --- | --- | --- |
| **Cursor** | Cursor Browser (built-in) | Sign into LinkedIn in Cursor before a pipeline run |
| **Claude Code** | Playwright MCP | Installer or `jobgru mcp login` |
| **Codex** | Playwright MCP | Installer or `jobgru mcp login` |

**Jobs + ATS run without LinkedIn login.** Only LeadGru (LinkedIn contacts) needs a signed-in session.

**Fallback (in-chat login)** — if `jobgru mcp login` doesn't work, start a **new** Codex/Claude session and paste:

```text
Use the playwright MCP tool browser_navigate to open https://www.linkedin.com/login — do not use any built-in browser skill.
Wait while I sign in manually. Do not continue until I say I'm logged in.
```

Sign in, then say: **I'm logged in to LinkedIn**

> Register MCP **before** starting a Codex/Claude session. Only **one** agent can use the browser profile at a time.

### Backfill leads after a partial run

If jobs were added but LeadGru was skipped:

```text
LeadGru backfill rows 42-43 — use Playwright MCP with my signed-in LinkedIn session only.
```

### Why LeadGru sometimes skips

| Phase | Can use web search? | Needs signed-in browser? |
| --- | --- | --- |
| Jobgru (find jobs) | Yes | No |
| ATSScore (resume fit) | N/A (Python) | No |
| LeadGru (LinkedIn people) | No | **Yes** |

---

## Chat commands (any agent, any folder)

| Command | Action |
| --- | --- |
| **Jobgru setup** + sheet URL | Agent configures venv, config, resume |
| **Jobgru help** | Full command guide (setup, check, mcp, filter, delete, pipeline) |
| **Jobgru check** | Verify everything is ready |
| **Jobgru mcp** | Install/check Playwright MCP (Claude + Codex browser) |
| **Jobgru filter** | List all filter types for job-search prompts |
| **Jobgru delete** | Delete sheet rows (42, 42-44, 42,43,44) |
| **/jobgru** + job search | Full pipeline (jobs → leads → ATS) |

Prompts: [setup.md](prompts/setup.md) · [help.md](prompts/help.md) · [check.md](prompts/check.md) · [filter.md](prompts/filter.md) · [delete.md](prompts/delete.md)

---

## Quick reference — terminal commands

```bash
jobgru help          # all commands
jobgru check         # is everything ready?
jobgru setup --url "SHEET_URL" --name "Your Name"
jobgru mcp status    # is Playwright MCP registered?
jobgru mcp login     # sign into LinkedIn again
jobgru filter        # see filter types for prompts
jobgru delete --rows 42-44   # delete test rows
jobgru update        # pull latest from main
jobgru uninstall     # remove global install
```

---

## Option B — open as repo (developers)

Clone this repo and open in an agent. Skills live in `.cursor/skills/`. Same chat commands work; engine uses repo root instead of `~/.jobgru`.

Local install from a clone (interactive wizard):

```bash
./install.sh --local /path/to/this/repo
```

Skip wizard (engine only): `./install.sh --local . --skip-setup`

See [AGENTS.md](AGENTS.md) and [docs/SETUP.md](docs/SETUP.md).

---

## Troubleshooting

Run **`jobgru check`** first.

| Problem | Fix |
| --- | --- |
| Auth failed | `gcloud auth login --enable-gdrive-access --update-adc` |
| Sheet write failed / permission denied | Use **your copy** URL (not template). Account in `gcloud auth` must be **Editor/Owner** on that sheet — Viewer is not enough. Solo setup: Make a copy + same Google account. No need for “anyone with link → Editor”. |
| No browser / LeadGru skipped | `jobgru mcp install --force` then `jobgru mcp login` — sign into LinkedIn in Playwright once |
| ATS skipped | Copy resume to `~/.jobgru/data/resumes/` or attach in chat: Jobgru add resume |
| Wrong sheet | Recopy template; tab = `Job Applications` |

Details: [docs/SETUP.md](docs/SETUP.md)

---

## For agents

| Intent | Read |
| --- | --- |
| Global `/jobgru` | `~/.cursor/skills/jobgru/SKILL.md` or [skill-global/jobgru/SKILL.md](skill-global/jobgru/SKILL.md) |
| Setup / help / check | `$JOBGRU_HOME/.cursor/skills/jobgru-setup/SKILL.md` |
| Job pipeline | `$JOBGRU_HOME/.cursor/skills/jobgru/SKILL.md` |

Never edit the Google Sheet via browser typing — use `scripts/sheets_write.py` only.
