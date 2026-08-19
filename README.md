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

## First-time setup (step by step)

Follow these steps in order. Each one builds on the last.

### Step 0 — What you need

- An AI agent: **Cursor**, **Claude Code**, or **Codex CLI**
- **Google Cloud SDK** — `gcloud` command works in terminal ([install](https://cloud.google.com/sdk/docs/install))
- A **resume PDF** on your computer (optional but enables ATS scoring)
- ~10 minutes

### Step 1 — Copy the Google Sheet template

1. Open the template (viewer access is fine — you only copy from it):

   https://docs.google.com/spreadsheets/d/18TQRl1dh0Ivdk8YbxkdiWb6__XkpHM32T1ohPTuMJ_4/edit

2. **File → Make a copy**
3. Tab name must stay **`Job Applications`**
4. Save **your copy's URL** — you'll use it in Step 4

> **Do not paste the template URL into Jobgru setup.** The template is read-only. Always use your own copy.

#### Who can Jobgru write to the sheet?

Jobgru writes through **your Google account** (`gcloud auth login`). That account must have **Editor** or **Owner** on the sheet — not Viewer, not Commenter.

| Situation | What to do | Jobgru can write? |
| --- | --- | --- |
| **Template link** (above) | Copy only — never use in setup | No |
| **Your copy** after File → Make a copy | You are **Owner** automatically | **Yes** |
| Your copy stays **private** (only you) | Fine — Owner + same `gcloud` account | **Yes** |
| **Someone else's sheet** shared with you as Viewer | Ask them to share you as **Editor** | No until you're Editor |
| Your copy but **`gcloud auth` is a different account** | Re-auth with the sheet owner account | No |

**You do NOT need** “Anyone with the link → Editor” for normal solo setup. After **Make a copy**, you already own the sheet.

### Step 2 — Google auth (terminal, once)

Sign in with the **same Google account** that owns your copied sheet:

```bash
gcloud auth login --enable-gdrive-access --update-adc
```

### Step 3 — Install Jobgru (terminal)

One command — works from any directory:

```bash
curl -fsSL https://raw.githubusercontent.com/ashujha301/jobgru/main/install.sh | bash
```

**Private repo:** you need git access to `github.com/ashujha301/jobgru`.

This installs:

- Engine at **`~/.jobgru`**
- Router skill **`/jobgru`** in Cursor, Claude Code, and Codex
- Terminal command **`jobgru`**
- Playwright MCP for Claude Code and Codex (LeadGru browser)

When the installer asks **"Sign into LinkedIn now?"** → type **`y`**

- Browser opens → sign into LinkedIn (MFA ok)
- **Press ENTER in the terminal** when done (don't close the browser yourself)

If you skipped LinkedIn during install, run anytime:

```bash
jobgru mcp login
```

Session saves to **`~/.jobgru/browser-profile`** and is reused automatically.

Update after each release: **`jobgru update`**

### Step 4 — Connect your sheet (terminal)

Replace with your copy URL and name:

```bash
jobgru setup --url "https://docs.google.com/spreadsheets/d/YOUR_COPY_ID/edit" --name "Your Name"
```

Or in chat:

```text
Jobgru setup — I copied the template. My sheet: <YOUR COPY URL>. My name: <YOUR NAME>
```

### Step 5 — Add your resume (optional, for ATS scoring)

Terminal:

```bash
mkdir -p ~/.jobgru/data/resumes
cp /path/to/your/resume.pdf ~/.jobgru/data/resumes/
```

Or attach the PDF in chat and say:

```text
Jobgru add resume
```

### Step 6 — Health check (terminal)

```bash
jobgru check
```

You want **`READY`** at the end.

| Check | Expected |
| --- | --- |
| `sheet_write` | OK |
| `sheet_formulas` | OK |
| `resume` | OK (after Step 5) or warn if skipped |
| browser / MCP | registered for Codex / Claude Code |

If anything fails, fix what `jobgru check` tells you before running a job search.

### Step 7 — Run your first job search

**Codex / Claude Code:** start a **new session** after install — MCP tools load only at session start.

Simple test prompt:

```text
Find 3 software engineer jobs on LinkedIn in Bangalore. Add them to my Job Applications sheet.
```

Or open [prompts/jobgru-run.md](prompts/jobgru-run.md), fill your filters, and paste into chat.

### Step 8 — What a successful run looks like

- New rows in your **Job Applications** Google Sheet
- **ATSScore** filled (columns I & J) if resume is present
- **LeadGru** filled (Leads column) if LinkedIn login worked
- Run record saved at `~/.jobgru/data/runs/`

---

## Browser setup by agent

| Agent | Browser for LeadGru | Setup |
| --- | --- | --- |
| **Cursor** | Cursor Browser (built-in) | Sign into LinkedIn in Cursor before a pipeline run |
| **Claude Code** | Playwright MCP | Step 3 above (`jobgru mcp login`) |
| **Codex** | Playwright MCP | Step 3 above (`jobgru mcp login`) |

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

Local install from a clone:

```bash
./install.sh --local /path/to/this/repo
```

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
