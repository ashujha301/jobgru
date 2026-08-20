---
name: jobgru
description: Jobgru pipeline Phase 1 — coordinate parallel job-board researchers to find and verify up to 50 unique jobs per run (LinkedIn max 25/run), deduplicate against the Job Applications Google Sheet, append rows via scripts/sheets_write.py, then automatically run LeadGru (Phase 2) and ATSScore (Phase 2b) in parallel for those new rows. Use when the user asks for Jobgru, job search, filtered openings, or to fill the tracker from LinkedIn, Wellfound, Indeed, YC Jobs, or other boards. One user prompt runs all phases; do not stop after sheet append.
---

# Jobgru (Pipeline Phase 1)

Coordinate parallel read-only researchers across job boards, verify each listing, deduplicate, and append up to **50 unique jobs per run** to the Job Applications tracker (LinkedIn capped at **25/run** for rate-limit safety). **Only the coordinator writes to the sheet** — always via `scripts/sheets_write.py` (Google Sheets API). **Never use agent browser tools to type into sheet cells** (Enter/Tab does not commit edits). Sheet writes = Sheets API only.

## Browser tools (job boards + LinkedIn)

Use whichever browser automation the agent has:

| Platform | Tools |
| --- | --- |
| **Cursor** | Cursor Browser (`browser_navigate`, `browser_snapshot`, `browser_click`, `browser_cdp`, …) |
| **Claude Code / Codex** | Playwright MCP or Chrome DevTools MCP (`navigate`, `snapshot`, `click`, `type`, …) |

If **no browser tools** are available, stop after sheet/ATS phases and report LeadGru skipped.

User completes MFA/CAPTCHA manually in the visible browser.

## Pipeline (mandatory)

Jobgru is **Phase 1** of a three-phase pipeline. **Do not report the run complete after appending jobs.**

After Phase 1 sheet write is verified:

1. Record `start_row` and `end_row` for the rows just appended.
2. **Immediately launch Phase 2 in parallel:**
   - **LeadGru** — read [`.cursor/skills/leadgru/SKILL.md`](../leadgru/SKILL.md), pipeline mode for `start_row`–`end_row` (fills G/H via LinkedIn browser).
   - **ATSScore** — read [`.cursor/skills/atsscore/SKILL.md`](../atsscore/SKILL.md), run `scripts/ats_score.py score --all` (fills **I: ATS score**, **J: Suggestions on Resume**). Skip if no resumes in `data/resumes/` or prompt says `ATS scoring: no`.
3. Wait for both tracks to finish (LeadGru may take longer).
4. Run `format-layout` once after both complete.
5. Save one combined run summary to `data/runs/<YYYY-MM-DD-HHMM>.json` with all phases.
6. Report **one completion summary** covering jobs appended + leads filled + ATS scores.

**Exception:** If LinkedIn blocks during LeadGru, report Phase 1 complete and LeadGru partial — ATSScore may still complete. Do **not** re-run Phase 1.

Standalone backfill: LeadGru alone → leadgru skill; ATS alone → atsscore skill.

## Help and check (before pipeline)

If the user says **Jobgru help** or **Jobgru check** (or setup is incomplete), read and follow [`.cursor/skills/jobgru-setup/SKILL.md`](../jobgru-setup/SKILL.md) instead of starting Phase 1.

- **help** — print the two manual steps + what the agent automates
- **check** — run `.venv/bin/python scripts/jobgru_check.py --json` and report pass/fail

Before the **first pipeline run**, suggest `Jobgru check` if setup may be incomplete.

## Prerequisites (user setup)

Complete setup via [jobgru-setup skill](../jobgru-setup/SKILL.md) or [README.md](../../README.md) (two manual steps: copy template sheet + `gcloud auth login --enable-gdrive-access --update-adc`).

Quick verify:

```bash
.venv/bin/python scripts/jobgru_check.py
```

If auth fails mid-run, stop and ask user to re-run gcloud auth. Do **not** fall back to browser sheet edits.

All shell commands run from **JOBGRU_HOME** (`~/.jobgru` after global install, else this repo root):

```bash
export JOBGRU_HOME="${JOBGRU_HOME:-$HOME/.jobgru}"
test -d "$JOBGRU_HOME/scripts" || JOBGRU_HOME="$(pwd)"
cd "$JOBGRU_HOME"
.venv/bin/python scripts/...
```

## Destination sheet (constants)

Read **`config/sheet.json`** at the start of every run (copy from `config/sheet.json.example` if missing). Scripts default to the same file.

| Constant | Source |
| --- | --- |
| Sheet URL | `sheet_url` in `config/sheet.json` |
| Spreadsheet ID | `spreadsheet_id` in `config/sheet.json` |
| Tab name | `tab` in `config/sheet.json` (default `Job Applications`) |
| Resume link default | `resume_link` in config, or cell **O2** on the sheet |
| Write script | `scripts/sheets_write.py` |
| Python | `.venv/bin/python` (create venv per README) |
| Run summaries | `data/runs/<YYYY-MM-DD-HHMM>.json` |
| Pending rows (staging) | `data/runs/pending-rows-<YYYY-MM-DD>.json` |
| Board runbooks | `data/board-runbooks/*.json` (see [Board runbook protocol](#board-runbook-protocol)) |
| ATS resumes | `data/resumes/` + `manifest.json` (see [ATSScore](../atsscore/SKILL.md)) |
| User guide | `README.md` |
| Setup / help / check | `.cursor/skills/jobgru-setup/SKILL.md` |
| Auth setup | `scripts/SHEETS-API-SETUP.md` |

### Columns this skill may write

Jobgru writes **A–F only** on new rows. G/H left blank for LeadGru; **I/J left blank for ATSScore**.

| Column | Header | New-row rule |
| --- | --- | --- |
| A | Company Name | Employer from listing |
| B | Position | Listing title as written |
| C | Apply link | Direct job/apply URL only — **plain text column, no dropdown/validation** |
| D | Status | Always `to apply` |
| E | Date Applied | Date added, `D/M/YYYY` |
| F | Details if any | Pay, exp, visa, arrangement, location, posted date, **Skills** — **no Apply link here** |
| G | Leads | Leave blank (LeadGru fills) |
| H | Add note Message | Leave blank (LeadGru fills) |
| I | ATS score | Leave blank (ATSScore fills) |
| J | Suggestions on Resume | Leave blank (ATSScore fills) |

**Sheet headers (row 1):** I1 = `ATS score`, J1 = `Suggestions on Resume`. Jobgru does not write row 1 unless headers are missing — then:

```bash
.venv/bin/python scripts/sheets_write.py write --range "I1:J1" --json '[["ATS score", "Suggestions on Resume"]]'
```

Older rows (before Aug 2026) may still have apply URLs inside column F; do not rewrite them. New rows always use column C for the URL.

### Never touch

- Existing rows and their Status, Leads, Add note Message (except filling C+F on rows this run just appended, if backfilling)
- Columns K+: Summary, Count, Latest Resume, Add Note Template (shifted after ATS columns I/J insert)

## Per-run limits

- Target: user-requested count, **max 50 verified unique jobs per run** (hard cap)
- **LinkedIn Jobs: max 25 accepted jobs per run** — protects account from rate limits; stop LinkedIn at 25 even if user asks for more
- Other boards share the remaining quota up to the 50 total (single board, multiple boards in parallel, or mix & match — user chooses in prompt)
- Stop early if sources are exhausted or blocked (report partial status)
- **One** LinkedIn researcher only
- Do not loosen filters to hit the target

## Coordinator workflow

1. **Read existing sheet rows** for dedupe (Sheets API — do not rely on browser):
   ```bash
   .venv/bin/python scripts/sheets_write.py read --range "A2:H500"
   ```
   Fallback read: Drive MCP `read_file_content` with `fileId` = `spreadsheet_id` from `config/sheet.json`
2. Build duplicate index: normalized company + similar role, plus canonical apply URLs from **column C** (fallback: parse `Apply:` from column F on older rows).
3. **Read board runbooks** for every board in the user prompt:
   ```bash
   ls data/board-runbooks/
   # Read each relevant JSON, e.g. data/board-runbooks/linkedin-jobs.json
   ```
4. Collect missing hard filters from the user (ask only for unknowns).
5. Launch parallel **read-only** researchers (Task/subagents or `/multitask`) — each must follow [Board runbook protocol](#board-runbook-protocol) for their board:
   - Wellfound → `data/board-runbooks/wellfound.json`
   - LinkedIn Jobs → `data/board-runbooks/linkedin-jobs.json` (one researcher)
   - Indeed, YC Jobs, remote boards → runbook if `status: active`, else discovery mode
6. Each researcher returns structured candidates — **never writes to the sheet**.
7. Coordinator verifies full listings, applies filters and user Notes, deduplicates.
8. **Write accepted rows** — follow [Sheet write runbook](#sheet-write-runbook-exact-steps) below. Capture `START_ROW` and `END_ROW`.
9. **Pipeline Phase 2 — LeadGru + Phase 2b ATSScore (parallel, automatic)** — follow [Pipeline handoff](#pipeline-handoff-phase-2--2b). Do not stop for user input.
10. Save combined run summary to `data/runs/<YYYY-MM-DD-HHMM>.json`.

---

## Board runbook protocol

Job boards have stable filter URLs and extract patterns. Store them in `data/board-runbooks/{board-id}.json`. **Read runbooks before searching — do not rediscover navigation for known boards.**

LeadGru uses the same pattern for LinkedIn people search (see leadgru skill). Jobgru runbooks cover **job listing navigation only**.

### Runbook mode (default — `status: active`)

1. Read `data/board-runbooks/{board-id}.json`.
2. Build search URLs: substitute `{KEYWORD}` from prompt role filters (one URL per keyword group — e.g. SWE, backend, backend AI → 3–4 URLs max per board per run).
3. Open `search_urls[0]` in Cursor Browser → run `extract_js` via `browser_cdp` → `Runtime.evaluate` with `returnByValue: true`.
4. **Health check (free — no separate pre-audit):** if extracted links >= `min_links`, runbook is valid → rotate remaining `search_urls`, collect candidates.
5. Verify **finalists only** using the runbook's `verify` method (`webfetch_listing` or `browser_listing`) — **one path per listing, never both**.

### Failure ladder (links < min_links)

Try in order; stop when links >= `min_links`:

1. Next `search_urls[]` entry (if not yet tried).
2. `fallback_urls[]` (max 2).
3. One bounded discovery navigate (see Discovery mode below).
4. **Patch runbook JSON** with working URL/extract snippet; set `last_ok` to today.
5. If still broken: set board `status: needs_manual_review` in run JSON `boards.{id}` and skip board this run.

### Discovery mode (new board — `status: no_runbook_yet` or missing file)

Bounded to **max 5 navigates + 1 CDP per page**:

1. Try obvious filtered search URL from `discovery.hints` in stub runbook (if any).
2. CDP extract job links; note URL pattern and link shape.
3. Verify 1–2 sample listings.
4. On success (>= `min_links`): write/update `data/board-runbooks/{board-id}.json` with `status: active`, `search_urls`, `extract_js`, `verify`.
5. On failure: report board unavailable; **do not save a broken runbook**.

### Hard rules (token savings)

| Rule | Why |
| --- | --- |
| One verify path per listing | Pass 2 double-fetched browser + WebFetch on same URL |
| WebSearch only as last resort | Pass 1 ran ~40 `site:wellfound.com` / `site:linkedin.com/jobs` loops |
| No repeating same search URL in one pass | Pass 2 ran 4–5 near-identical LinkedIn URLs |
| No generic Wellfound `/jobs` page | Pass 1 wasted navigates on unfiltered page |
| If < 5 total candidates after primary searches | One broader search URL or one WebSearch, then stop |

### Coverage (runbooks do not narrow filters)

- `search_urls` rotate across prompt role keywords — never a single narrow query.
- Role matching, Note overrides, staffing/senior exclusions, and full-listing read stay in this skill — runbooks only handle **getting to listings**.
- Runbooks patch on failure only — do not auto-edit this SKILL.md file.

### Seed runbooks (Aug 2026)

| board-id | File | Notes |
| --- | --- | --- |
| `linkedin-jobs` | `data/board-runbooks/linkedin-jobs.json` | f_WT, f_E, f_TPR filters; `/jobs/view/` extract |
| `wellfound` | `data/board-runbooks/wellfound.json` | `/role/l/{slug}/india`; company `/jobs` deep-dive |
| `remote-rocketship` | `data/board-runbooks/remote-rocketship.json` | `?jobTitle={KEYWORD}&sort=DateAdded`; remote aggregator |
| `dailyremote` | `data/board-runbooks/dailyremote.json` | category pages + search; fresh 24h listings |
| `remoteok` | `data/board-runbooks/remoteok.json` | `/remote-{slug}-jobs` tag pages; salary tags |
| `weworkremotely` | `data/board-runbooks/weworkremotely.json` | `search?term=`; Region field per listing |
| `remotive` | `data/board-runbooks/remotive.json` | category pages; free tier hides some company names |
| `himalayas` | `data/board-runbooks/himalayas.json` | stub — Cloudflare blocks WebFetch, browser only |
| `working-nomads` | `data/board-runbooks/working-nomads.json` | stub — discovery on first use |
| `indeed` | `data/board-runbooks/indeed.json` | stub — anti-bot, browser only |
| `yc-jobs` | `data/board-runbooks/yc-jobs.json` | stub — discovery on first use |

**Remote-first prompts:** when the prompt says remote / work-from-home and names no boards, prefer active remote boards (Remote Rocketship, RemoteOK, We Work Remotely, DailyRemote, Remotive) alongside LinkedIn — they share the non-LinkedIn quota.

---

## Researcher output format

Each candidate must include:

```json
{
  "source": "Wellfound",
  "company": "Example Inc",
  "position": "ML Engineer",
  "location": "Remote — India",
  "work_arrangement": "Remote",
  "pay": "₹25L–₹40L",
  "experience": "2–4 years",
  "visa": "Not stated",
  "posted_date": "1 week ago",
  "apply_url": "https://wellfound.com/jobs/...",
  "listing_url": "https://wellfound.com/jobs/...",
  "skills": ["Python", "FastAPI", "PostgreSQL", "LLM"],
  "match_notes": ["domain match", "remote match"]
}
```

Researchers must open the full job post. Search snippets are not enough.

## Intake filters

Collect before searching:

- Job title(s) and target domain
- Location and remote country/time-zone rules
- Work arrangement: remote, hybrid, onsite, any
- Experience level
- Visa rule: required, preferred, irrelevant, exclude
- Must-haves and exclusions
- Optional: pay, employment type, posting age, company size
- **Note** after filters (optional override)

### Notes override default skip rules

User notes after filters override defaults. Examples:

- `dont skip if the exp matches` → include when experience matches even if title wording differs
- `include if visa is not stated` → do not skip for missing visa
- `onsite ok in Bangalore only` → onsite only for that location

Notes never authorize guessing facts, bypassing logins, or modifying existing rows.

## Role matching: same domain, not exact title

Include when title + description match the requested domain. Exclude different domains even with keyword overlap.

For AI/ML searches, include: AI Engineer, ML Engineer, Applied AI, GenAI/LLM, Founding AI, Software Engineer AI/ML when description is AI/ML work.

## De-duplicate by company + role

Primary key: **normalized company + similar role**.

Also skip when normalized apply URL in column C (or legacy `Apply:` in column F) already exists in sheet or this run.

Same company + different domain is not a duplicate.

Cross-board duplicates: keep one row with the most direct apply URL; note `also on <board>` in Details.

## Details if any (column F — no apply link)

Every new row **must** have a working apply URL in **column C**. Rows without column C fail quality check.

**Exact string formula** (single line, column F only):

```
Pay: {pay}, Exp: {experience}, Visa: {visa}, {work_arrangement}, {location}, Posted: {posted_date} | Skills: {skill1}, {skill2}, ...
```

Substitute from verified listing; use `Not stated` when unknown. `{work_arrangement}` is exactly one of: `Remote`, `Hybrid`, or `Onsite`.

**Skills (required for new rows):** extract **5–12 concrete skills/keywords** from the listing description while it is open for verification (e.g. Python, FastAPI, Kubernetes, LLM). Comma-separated after `| Skills:`. Used by ATSScore — no extra fetch at ATS time.

**Column C (Apply link):** bare URL only, e.g. `https://wellfound.com/jobs/123456-ml-engineer`

Rules:

- Column C = direct job or apply URL from the board where verified
- Do **not** put `Apply:` or the URL in column F
- If found on multiple boards: note `also on {board}` at end of column F text
- Do not invent pay, visa, or experience

Example row fields:

| Column | Value |
| --- | --- |
| C | `https://wellfound.com/jobs/123456-ml-engineer` |
| F | `Pay: ₹25L–₹45L, Exp: 3+ years, Visa: Not stated, Onsite, Bengaluru, Posted: 2 days ago \| Skills: Python, FastAPI, REST APIs, PostgreSQL` |

## Sheet write runbook (exact steps)

**Do not use browser clicks, F2, Enter, Tab, or formula bar** to write cells — confirmed broken in Cursor Browser (edits show in UI but never save to Drive).

### Step 0 — One-time auth (user machine)

If any write returns `403 insufficient scopes` or auth error, ask the user to run:

```bash
gcloud auth login --enable-gdrive-access --update-adc
```

Account must be the sheet owner. **Do not** use `gcloud auth application-default login --scopes=.../spreadsheets` (Google blocks with "This app is blocked").

Install deps once (user):

```bash
python3 -m venv .venv
.venv/bin/pip install -r scripts/requirements.txt
```

Smoke test before first real write:

```bash
.venv/bin/python scripts/sheets_write.py test --cleanup
```

Expect stdout: `OK: Sheets API write verified`

### Step 1 — Find first empty row

```bash
START_ROW=$(.venv/bin/python scripts/sheets_write.py first-empty)
echo "First empty row: $START_ROW"
```

`first-empty` scans column A from row 2; returns the row number (e.g. `22`).

### Step 2 — Build row JSON file

Save accepted jobs to `data/runs/pending-rows-<YYYY-MM-DD>.json`.

**Exact JSON shape** — array of rows, each row is **8 strings** `[A, B, C, D, E, F, G, H]`:

```json
[
  [
    "Company Name",
    "Position Title",
    "https://example.com/job/123",
    "to apply",
    "19/8/2026",
    "Pay: ₹20L–₹30L, Exp: 2–4 years, Visa: Not stated, Remote, India, Posted: 1 week ago | Skills: Python, FastAPI, PostgreSQL, LLM",
    "",
    ""
  ]
]
```

Column rules for every row:

| Index | Column | Value |
| --- | --- | --- |
| 0 | A Company Name | From listing |
| 1 | B Position | Listing title as written |
| 2 | C Apply link | Bare apply URL |
| 3 | D Status | Always exactly `to apply` |
| 4 | E Date Applied | Run date as `D/M/YYYY` (no leading zeros), e.g. `19/8/2026` |
| 5 | F Details if any | Details formula string (no URL) |
| 6 | G Leads | Always `""` (LeadGru fills later) |
| 7 | H Add note Message | Always `""` (LeadGru fills later) |

Build row from each verified candidate:

```python
skills_str = ", ".join(skills[:12])  # 5–12 from listing
details = (
    f"Pay: {pay}, Exp: {experience}, Visa: {visa}, "
    f"{work_arrangement}, {location}, Posted: {posted_date} | Skills: {skills_str}"
)
row = [company, position, apply_url, "to apply", date_str, details, "", ""]
```

### Step 3 — Write rows to sheet

Use `--start-row` with the value from Step 1. For N jobs starting at row R, API updates `A{R}:H{R+N-1}`.

```bash
.venv/bin/python scripts/sheets_write.py append \
  --file data/runs/pending-rows-<YYYY-MM-DD>.json \
  --start-row "$START_ROW"
```

Success output includes:

```json
{
  "updatedRange": "'Job Applications'!A22:H26",
  "updatedRows": 5,
  "updatedCells": 40
}
```

If auth fails, stop and tell user to run Step 0 — do not fall back to browser typing.

### Step 4 — Verify write persisted

```bash
END_ROW=$((START_ROW + NUM_JOBS - 1))
.venv/bin/python scripts/sheets_write.py read --range "A${START_ROW}:H${END_ROW}"
```

Confirm every row has Company, Position, apply URL in column C, `to apply`, date, Details in column F with `Skills:` suffix (no URL in F).

Optional cross-check: Drive MCP `read_file_content` with `fileId` from `config/sheet.json` — new companies must appear at bottom.

### Step 5 — Update run JSON (Phase 1 fields)

Set in `data/runs/<YYYY-MM-DD-HHMM>.json` (LeadGru fields added after Phase 2):

```json
{
  "pipeline": {
    "phase1": "jobgru",
    "phase2": "leadgru",
    "status": "phase1_complete"
  },
  "start_row": 22,
  "end_row": 26,
  "rows_appended": 5,
  "companies": ["Example Inc", "Another Co"],
  "boards": {
    "linkedin-jobs": {
      "runbook_used": true,
      "runbook_patched": false,
      "discovery_performed": false,
      "candidates_found": 12
    },
    "wellfound": {
      "runbook_used": true,
      "runbook_patched": false,
      "discovery_performed": false,
      "candidates_found": 8
    }
  },
  "sheet_write_status": "complete",
  "sheet_write_method": "sheets_api",
  "sheet_rows_written": "A22:H26"
}
```

---

## Pipeline handoff (Phase 2 + 2b)

**Trigger:** Immediately after Step 4 verify passes. **No user prompt required.**

Launch **LeadGru** and **ATSScore in parallel**:

### LeadGru (Phase 2)

1. Read [`.cursor/skills/leadgru/SKILL.md`](../leadgru/SKILL.md).
2. Pass `start_row`, `end_row`; process rows in range where Status is `to apply` and Leads (G) empty.
3. LinkedIn search → write G/H per row.

### ATSScore (Phase 2b)

1. Read [`.cursor/skills/atsscore/SKILL.md`](../atsscore/SKILL.md).
2. Skip if `data/resumes/` has no PDFs/manifest entries, or prompt contains `ATS scoring: no`.
3. Run (can start immediately — no browser):

   ```bash
   .venv/bin/python scripts/ats_score.py score --all
   ```

4. Backfills **all** `to apply` rows with empty I, not only new rows.

### After both complete

```bash
.venv/bin/python scripts/sheets_write.py format-layout
.venv/bin/python scripts/sheets_write.py read --range "A${START_ROW}:J${END_ROW}"
```

Update run JSON:

```json
{
  "pipeline": { "phase1": "jobgru", "phase2": "leadgru", "phase2b": "atsscore", "status": "complete" },
  "start_row": 22,
  "end_row": 26,
  "leadgru_rows_processed": [22, 23, 24, 25, 26],
  "leadgru_status": "complete",
  "leadgru_skipped": [],
  "atsscore_status": "complete",
  "atsscore_rows_scored": [22, 23, 24, 25, 26, 15],
  "atsscore_skipped_no_data": [15],
  "resumes_used": ["Backend SWE"]
}
```

If LeadGru partial: `"leadgru_status": "blocked"`. ATSScore may still be `"complete"`.

**Do not** ask the user to run LeadGru or ATSScore separately. **Do not** end the session after Phase 1.

### Step 6 — Sheet layout (overflow)

If Details (F), Leads (G), or Add note (H) text spills into neighboring columns, run:

```bash
.venv/bin/python scripts/sheets_write.py format-layout
```

This sets wrap text, top alignment, column widths, frozen header row, and auto-resizes row heights. Safe to re-run anytime.

### All sheet commands (reference)

Run from **project root**:

| Command | Purpose |
| --- | --- |
| `.venv/bin/python scripts/sheets_write.py first-empty` | First empty row in column A |
| `.venv/bin/python scripts/sheets_write.py read --range "A2:H500"` | Read for dedupe |
| `.venv/bin/python scripts/sheets_write.py append --file FILE --start-row N` | Write N rows at row N |
| `.venv/bin/python scripts/sheets_write.py read --range "A{N}:H{M}"` | Verify after write |
| `.venv/bin/python scripts/sheets_write.py test --cleanup` | Auth smoke test |
| `.venv/bin/python scripts/sheets_write.py format-layout` | Wrap text + column widths (run after batch writes if cells overflow) |

Optional flags (defaults are correct for Jobgru):

- `--spreadsheet-id` (optional; defaults to `config/sheet.json`)
- `--tab "Job Applications"`

Full setup doc: `scripts/SHEETS-API-SETUP.md`. User guide: `README.md`.

### Column C rules

- Bare URL only — no `Apply:` prefix
- Plain text column — **no dropdown or data validation** on column C
- If column C accidentally gets validation (e.g. after column insert), clear via Sheets API `setDataValidation` with `rule: null` on column C

## Do not use Cursor Browser for sheet writes

Browser automation **does not persist** edits to Google Sheets in this environment. Confirmed failure mode:

| Action tried | Result |
| --- | --- |
| Navigate to sheet URL | OK |
| Click cell / F2 / type in editor | Text shows in UI only |
| Press Enter or Tab | **Does not commit** — cell stays in edit mode |
| Drive export / Sheets API read | **No new data** |

Do **not** open duplicate sheet tabs. Do **not** retry browser fill loops. Use the [Sheet write runbook](#sheet-write-runbook-exact-steps) only.

## Safety

- Do not bypass logins, CAPTCHAs, paywalls, or rate limits
- Stop a board on verification challenges; report as unavailable
- Never apply, message employers, or change board settings
- Stop LinkedIn activity on account warnings

## Quality check

Before **pipeline** completion (Phase 1 + Phase 2):

**Phase 1 (Jobgru):**

1. Up to 50 rows appended (or fewer with source-exhaustion report; LinkedIn capped at 25)
2. Every row has Company, Position, apply URL in column C, `to apply`, date, Details in F
3. No duplicate company+similar-role against pre-run snapshot
4. Existing rows and columns K+ unchanged
5. **Sheets API verify** passed: `read --range "A{start}:H{end}"` matches written JSON; F includes `Skills:`
6. Run JSON has `sheet_write_status: complete` and `sheet_write_method: sheets_api`

**Phase 2 — LeadGru (automatic)**

7. Every row in `[start_row, end_row]` has Leads (G) filled (4–10 `/in/` URLs or company page)
8. Every row in `[start_row, end_row]` has Add note Message (H) filled from templates
9. LeadGru run JSON fields populated

**Phase 2b — ATSScore (automatic, parallel)**

10. `score --all` run when resumes present (or skip documented)
11. Column **I (ATS score)** filled for scored rows; no-data comment for rows missing Skills
12. Column **J (Suggestions on Resume)** filled for successfully scored rows

**Final**

13. `format-layout` run after both Phase 2 tracks
14. Run JSON has `pipeline.status: complete` (or `partial` with skipped rows listed)

## Completion report

Report **one combined summary** in chat and save to `data/runs/`:

**Phase 1 — Jobgru**

- Sheet link
- Boards searched (runbook used / patched / discovery per board)
- Rows appended (count, row numbers, companies)
- Per-board: reviewed / included / excluded / unavailable
- Duplicates skipped
- Notes applied
- Access limitations

**Phase 2 — LeadGru (automatic)**

- Rows processed (row # + company + leads count per row)
- Rows skipped (if any) and why
- LinkedIn limits (CAPTCHA, rate limit) if any

**Phase 2b — ATSScore (automatic)**

- ATS status: complete | skipped (no resumes / disabled)
- Rows scored (row # + best score)
- Rows skipped — no Skills in Details
- Resumes used

**Pipeline**

- Pipeline status: `complete` | `partial`
