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
- Playwright MCP for Claude Code / Codex (browser automation)

Update after each release: **`jobgru update`** (pulls latest from `main`).

---

## First time? You only do 2 things

### 1. Copy the Google Sheet template

1. Open: https://docs.google.com/spreadsheets/d/18TQRl1dh0Ivdk8YbxkdiWb6__XkpHM32T1ohPTuMJ_4/edit
2. **File → Make a copy** → tab must stay **`Job Applications`**
3. In any agent chat:

```text
Jobgru setup — I copied the template. My sheet: <YOUR URL>. My name: <YOUR NAME>
```

Or terminal:

```bash
jobgru setup --url "https://docs.google.com/spreadsheets/d/..." --name "Your Name"
```

### 2. Google auth (terminal — once)

```bash
gcloud auth login --enable-gdrive-access --update-adc
```

Then: **`Jobgru check`** or `jobgru check`

---

## Chat commands (any agent, any folder)

| Command | Action |
| --- | --- |
| **Jobgru setup** + sheet URL | Agent configures venv, config, resume |
| **Jobgru help** | Step-by-step instructions |
| **Jobgru check** | Verify everything is ready |
| **/jobgru** + job search prompt | Full pipeline |

Prompts: [prompts/setup.md](prompts/setup.md) · [help.md](prompts/help.md) · [check.md](prompts/check.md)

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
jobgru check
jobgru setup --url "SHEET_URL" --name "Your Name"
jobgru update
jobgru uninstall
```

---

## Troubleshooting

Run **`jobgru check`** first.

| Problem | Fix |
| --- | --- |
| Auth failed | `gcloud auth login --enable-gdrive-access --update-adc` |
| No browser / no leads | Install Playwright MCP (installer does this) or use Cursor |
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
