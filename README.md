# Jobgru Automation

Find verified jobs, write them to your **Job Applications** Google Sheet, then automatically find LinkedIn contacts, outreach notes, and ATS resume scores — **one prompt, full pipeline**.

Works in **Cursor, Claude Code, Codex**, or any agent — install once, use `/jobgru` from any chat.

| Phase | Skill | What it does |
| --- | --- | --- |
| **Setup** | `jobgru-setup` | First-time setup, help, health check |
| **Phase 1 — Jobgru** | `jobgru` | Search boards → verify → append 5–10 jobs/run |
| **Phase 2 — LeadGru** | `leadgru` | LinkedIn leads + notes (automatic, parallel) |
| **Phase 2b — ATSScore** | `atsscore` | Resume fit scores (Python, parallel) |

---

## Install globally (recommended)

One command — works from any directory:

```bash
curl -fsSL https://raw.githubusercontent.com/ashujha301/jobgru/main/install.sh | bash
```

**Private repo:** you need git access to `github.com/ashujha301/jobgru` (clone auth or make public later).

Local testing before publish:

```bash
./install.sh --local /path/to/this/repo
```

This installs:

- Engine at **`~/.jobgru`**
- Router skill **`/jobgru`** in Cursor, Claude Code, and Codex skill folders
- Terminal command **`jobgru`**
- Playwright MCP for Claude Code / Codex (`jobgru mcp install`)

After install:

```bash
jobgru mcp install          # browser for Claude + Codex (Cursor: built-in)
cp resume.pdf ~/.jobgru/data/resumes/   # for ATS scoring
jobgru check
```

Update after each release: **`jobgru update`** (pulls latest from `main`).

---

## First time? You only do 2 things

### 1. Copy the Google Sheet template

**Open the template (viewer access is OK — you only copy from it):**

https://docs.google.com/spreadsheets/d/18TQRl1dh0Ivdk8YbxkdiWb6__XkpHM32T1ohPTuMJ_4/edit

**Then: File → Make a copy** → tab must stay **`Job Applications`**

> **Do not paste the template URL into Jobgru setup.** The template is read-only. You need **your own copy** where you are Owner/Editor.

| What you use | Access needed | Jobgru can write? |
| --- | --- | --- |
| Template link (above) | Viewer | No — copy only, never use in setup |
| **Your copy** (after Make a copy) | **Owner / Editor** (automatic) | **Yes** — paste this URL in setup |
| Someone else's shared sheet | Viewer or Commenter | No — permission denied |
| Your copy + wrong Google account in `gcloud auth` | — | No — account must match sheet owner |

**Use your copy's URL** in chat or terminal:

```text
Jobgru setup — I copied the template. My sheet: <YOUR COPY URL>. My name: <YOUR NAME>
```

```bash
jobgru setup --url "https://docs.google.com/spreadsheets/d/YOUR_COPY_ID/edit" --name "Your Name"
```

### 2. Google auth (terminal — once)

Sign in with the **same Google account** that owns your copied sheet:

```bash
gcloud auth login --enable-gdrive-access --update-adc
```

Then verify: **`Jobgru check`** or `jobgru check` → should show **READY** and `sheet_write: OK`.

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

## Run your first job search

When check shows **READY**:

1. Sign into **LinkedIn** in the agent browser
2. Open [prompts/jobgru-run.md](prompts/jobgru-run.md), fill filters, paste into chat
3. Wait ~45–180 min for new sheet rows

---

## Option B — open as repo (developers)

Clone this repo and open in an agent. Skills live in `.cursor/skills/`. Same chat commands work; engine uses repo root instead of `~/.jobgru`.

See [AGENTS.md](AGENTS.md) and [docs/SETUP.md](docs/SETUP.md).

---

## Terminal CLI

```bash
jobgru help
jobgru check
jobgru setup --url "SHEET_URL" --name "Your Name"
jobgru mcp install
jobgru filter
jobgru filters
jobgru delete --rows 42-44
jobgru update
jobgru uninstall
```

---

## Troubleshooting

Run **`jobgru check`** first.

| Problem | Fix |
| --- | --- |
| Auth failed | `gcloud auth login --enable-gdrive-access --update-adc` |
| Sheet write failed / permission denied | Use **your copy** URL (not template); you must be Editor/Owner; `gcloud auth` same account |
| No browser / LeadGru skipped | `jobgru mcp install` (Claude/Codex) or use Cursor |
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
