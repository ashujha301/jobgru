---
name: leadgru
description: Jobgru pipeline Phase 2 — find LinkedIn hiring contacts for new Job Applications rows, write 4–10 profile links into Leads, and fill Add note Message from sheet templates. Runs automatically after Jobgru appends rows (pipeline mode), in parallel with ATSScore. Also use standalone when the user explicitly asks to backfill Leads for existing to apply rows without re-running Jobgru.
---

# LeadGru (Pipeline Phase 2)

For every `to apply` row with empty Leads, find relevant LinkedIn people, write profile links into `Leads`, and fill a paste-ready note into `Add note Message`. Only the coordinator writes to the sheet — via `scripts/sheets_write.py` (Google Sheets API). **Never use Cursor Browser to type into sheet cells.**

LinkedIn discovery uses **agent browser tools** (Cursor Browser, Playwright MCP, or Chrome DevTools MCP). Sheet writes use **Sheets API only**.

## Browser tools

| Platform | LinkedIn / people search |
| --- | --- |
| **Cursor** | Cursor Browser + CDP (`browser_navigate`, `browser_snapshot`, `browser_cdp`) |
| **Claude Code / Codex** | Playwright MCP or Chrome DevTools MCP (navigate, snapshot, evaluate) |

Sign into LinkedIn in the browser before LeadGru. User completes MFA/CAPTCHA manually.

## Pipeline mode (default)

**When:** Jobgru Phase 1 just finished and verified sheet append. **Triggered automatically** — no separate user prompt.

**Scope:** Process **only** rows `start_row` through `end_row` from the Jobgru run JSON (the rows just appended this session).

```bash
# Example: Jobgru appended rows 27–31
START_ROW=27
END_ROW=31
.venv/bin/python scripts/sheets_write.py read --range "A${START_ROW}:H${END_ROW}"
```

Rules in pipeline mode:

- Do **not** ask the user to confirm before starting
- Do **not** process older empty-Leads rows unless the user explicitly requested a backfill run
- If a row in range already has Leads, skip it and note in run JSON
- After all rows in range: `format-layout`, verify, update combined run JSON
- Return control to Jobgru completion report (one summary for both phases)

## Standalone mode (backfill only)

**When:** User explicitly asks for LeadGru only (e.g. "run LeadGru", "fill leads for empty rows") **without** a Jobgru run in the same session.

**Scope:** All eligible rows in the sheet (`A2:H500`) where Status is `to apply` and Leads (G) is empty.

Use [prompts/leadgru-run.md](../../prompts/leadgru-run.md) for standalone backfill prompts.

## Prerequisites (user setup)

Run **Jobgru check** first: `.venv/bin/python scripts/jobgru_check.py` — or say **Jobgru check** in chat.

Setup guide: [jobgru-setup skill](../jobgru-setup/SKILL.md) and [README.md](../../README.md).

If auth fails, ask user to run `gcloud auth login --enable-gdrive-access --update-adc`.

Before LeadGru: user must be **signed into LinkedIn** in the agent browser (Premium helps).

All shell commands assume **current working directory = project root**.

## Destination sheet (constants)

Read **`config/sheet.json`** at the start of every run (copy from `config/sheet.json.example` if missing).

| Constant | Source |
| --- | --- |
| Sheet URL | `sheet_url` in `config/sheet.json` |
| Spreadsheet ID | `spreadsheet_id` in `config/sheet.json` |
| Tab name | `tab` in `config/sheet.json` |
| Resume link default | `resume_link` in config, or cell **O2** on the sheet |
| Write script | `scripts/sheets_write.py` |
| Python | `.venv/bin/python` |
| Run summaries | Combined in `data/runs/<YYYY-MM-DD-HHMM>.json` (pipeline) or `data/runs/leadgru-<YYYY-MM-DD-HHMM>.json` (standalone) |
| User guide | `README.md` |
| Auth setup | `scripts/SHEETS-API-SETUP.md` |
| Pipeline Phase 1 | `.cursor/skills/jobgru/SKILL.md` |
| Standalone prompt | `prompts/leadgru-run.md` |

### Column layout

| Column | Header | This skill |
| --- | --- | --- |
| A | Company Name | Read only |
| B | Position | Read only |
| C | Apply link | Read only |
| D | Status | Read only; work when `to apply` |
| E | Date Applied | Never touch |
| F | Details if any | Read only |
| G | Leads | **Write** when empty |
| H | Add note Message | **Write** when empty |
| I | ATS score | Read only (ATSScore writes) |
| J | Suggestions on Resume | Read only (ATSScore writes) |
| Q | Add Note Template | Read only (rows Q2–Q7) |
| K+ | Summary, resume, etc. | Read only |

Older rows may have apply URLs inside column F instead of column C; still process them normally.

## Which rows to process

Process when all true:

1. Status (column D) is `to apply` (case-insensitive)
2. Company Name (column A) present
3. Leads (column G) empty

Skip when Status is not `to apply` or Leads already has names, `/in/` URLs, or company page links.

If Add note Message (column H) is filled, still fill Leads when empty; do not overwrite the note.

Process every matching row in the batch.

- **Pipeline mode:** rows `start_row`–`end_row` from Jobgru run only (typically 5–10 companies)
- **Standalone mode:** all eligible rows in `A2:H500`

## Coordinator workflow

### Pipeline mode (after Jobgru)

1. Receive `start_row`, `end_row` from Jobgru handoff (or read from `data/runs/<latest>.json`).
2. **Read batch + templates** (Sheets API):
   ```bash
   .venv/bin/python scripts/sheets_write.py read --range "A${START_ROW}:H${END_ROW}"
   .venv/bin/python scripts/sheets_write.py read --range "Q1:Q7"
   ```
3. Filter eligible rows in range (Status `to apply`, Leads empty).
4. **LinkedIn pass** — one company at a time → [LinkedIn search runbook](#linkedin-search-runbook-exact-steps).
5. **Write each row immediately** after that company's leads are verified → [Sheet write runbook](#sheet-write-runbook-exact-steps).
6. **Verify** batch: `read --range "A${START_ROW}:H${END_ROW}"`.
7. `format-layout`.
8. Update combined run JSON with `leadgru_rows_processed`, `leadgru_status`.
9. `browser_lock` with `action: unlock` when all LinkedIn work is done.

### Standalone mode (backfill)

1. **Read rows + templates** (Sheets API — do not open sheet in browser):
   ```bash
   .venv/bin/python scripts/sheets_write.py read --range "A2:H500"
   .venv/bin/python scripts/sheets_write.py read --range "Q1:Q7"
   ```
2. Filter eligible rows (Status `to apply`, Leads empty).
3. **LinkedIn pass** — one company at a time → [LinkedIn search runbook](#linkedin-search-runbook-exact-steps).
4. **Write each row immediately** after that company's leads are verified → [Sheet write runbook](#sheet-write-runbook-exact-steps).
5. **Verify** batch with Sheets API read.
6. `format-layout`.
7. Optional: save summary to `data/runs/leadgru-<YYYY-MM-DD-HHMM>.json`.
8. `browser_lock` with `action: unlock` when all LinkedIn work is done.

## Concurrency limits

- **One** LinkedIn company search at a time (no parallel LinkedIn tabs)
- Write each row immediately after that company's search completes
- Stop on CAPTCHA, login challenge, or rate-limit warning — report and skip remaining companies

## Who to find

Priority for the row's Position:

1. Recruiters, Talent Acquisition, HR, People Ops, sourcers
2. Hiring managers (Engineering Manager, Head of Engineering, VP Eng, AI/ML lead)
3. Team leads matching the role

For small companies (~50 employees or founding/startup roles):

4. CEO, Founder, CTO, Founding Engineer, other founding ICs

Only add people whose LinkedIn headline or current experience shows this company. Skip unrelated functions unless the company is tiny.

## How many people

- Target **4–10** verified profiles per row
- If fewer than 4 after real search: write all found **and** company LinkedIn page
- If none verified: write company page only
- Never leave Leads blank on a processed row

## Leads format (column G)

```
Name — Title — https://www.linkedin.com/in/<handle>/
Name — Title — https://www.linkedin.com/in/<handle>/
Company: https://www.linkedin.com/company/<handle>/
```

Rules:

- One person per line, newline-separated
- Use `linkedin.com/in/` URLs only (strip `?` query params)
- Trailing slash on URLs is fine
- Last line always `Company: <linkedin.com/company/...>` when people count is under 4 **or** as extra context (test run included company page on all 5 rows — acceptable)
- Title from LinkedIn card headline or role at company

## Add note Message (column H)

### Read templates

Templates live in column **Q**, rows **Q2–Q7** (header in Q1):

```bash
.venv/bin/python scripts/sheets_write.py read --range "Q1:Q7"
```

### Fill formula

Pick one template per row; **rotate templates 1–6** across rows in the batch (row 1 of batch → Q2, row 2 → Q3, … row 6 → Q7, row 7 → Q2 again).

Substitute:

| Placeholder | Source |
| --- | --- |
| `{Position}` | Column B (Position) — use full title as written |
| `{Company}` | Column A (Company Name) — use full name as written |
| `{Link}` | Resume URL from cell **O2**, or `resume_link` in `config/sheet.json` |

Always change `Hi {Name},` → `Hi,`. **Do not** include any lead name.

Write only if Add note Message (column H) is empty.

Example output (template 1, row 22):

```
Hi, I just applied for the AI Engineer role at Businessonbot (Y Combinator W21) and would truly appreciate a referral or a quick push to the hiring team. Here's my resume for you: https://bit.ly/ajha Thank you so much! - Ayush Jha
```

---

## LinkedIn search runbook (exact steps)

**Use Cursor Browser for LinkedIn only.** Do not type into the Google Sheet.

### Browser lock order

1. `browser_tabs` with `action: list` — check for an existing LinkedIn tab
2. If LinkedIn tab exists: `browser_lock` with `action: lock` **first**
3. If no tab: `browser_navigate` to LinkedIn search URL, then `browser_lock` with `action: lock`
4. When **all** companies done: `browser_lock` with `action: unlock`

Correct order: navigate (if needed) → lock → searches → unlock.

### Per-company search (repeat for each row)

**Step 1 — Normalize company name for search**

- Strip parentheticals for the keyword: `Businessonbot (Y Combinator W21)` → search `BusinessOnBot` or `Businessonbot`
- Keep full name in Add note Message (column A value)
- If company has a different LinkedIn brand name, search both (see [Known company aliases](#known-company-aliases-aug-2026-test))

**Step 2 — Primary people search URL**

Navigate to (URL-encode `{KEYWORD}`):

```
https://www.linkedin.com/search/results/people/?keywords={KEYWORD}&origin=GLOBAL_SEARCH_HEADER
```

Examples that worked (Aug 2026 test):

| Row | Company (sheet) | Search keyword / URL |
| --- | --- | --- |
| 22 | Businessonbot (Y Combinator W21) | `BusinessOnBot` |
| 23 | SuperProfile | `"SuperProfile" Cosmofeed` (employees list under Cosmofeed) |
| 24 | Boock.ai | `Boock.ai` |
| 25 | Prodigal | `Prodigal` |
| 26 | HackerRank | `HackerRank` |

**Step 3 — If primary search returns unrelated people**

Try in order (stop when you have 4+ verified profiles):

1. Add disambiguator: `"SuperProfile" Gurgaon creator`, `"SuperProfile" creator platform`
2. Company people page: `https://www.linkedin.com/company/{handle}/people/`
3. Hiring-role keyword (only if company name alone fails): `{COMPANY} recruiter OR talent` — **often returns noise**; prefer company name search

**Do not** rely on generic `recruiter OR talent OR founder` as the first query — test run showed it returns unrelated profiles.

**Step 4 — Extract profile URLs via CDP**

Use `browser_cdp` → `Runtime.evaluate` with `returnByValue: true`. Prefer `.linked-area` card text to verify employment.

**Pattern A — filter by company in card text (best, worked for Boock.ai, Prodigal, SuperProfile):**

```javascript
Array.from(document.querySelectorAll('a[href*="/in/"]')).map(a => ({
  href: a.href.split('?')[0],
  t: a.closest('.linked-area')?.innerText?.slice(0, 200) || ''
})).filter(x => /COMPANY_REGEX/i.test(x.t))
  .reduce((acc, x) => { if (!acc.find(y => y.href === x.href)) acc.push(x); return acc; }, [])
  .slice(0, 8)
```

Replace `COMPANY_REGEX` with company name variants (e.g. `boock`, `prodigal`, `superprofile|cosmofeed`).

**Pattern B — result list containers:**

```javascript
Array.from(document.querySelectorAll('li.reusable-search__result-container, div[data-chameleon-result-urn]'))
  .map(li => {
    const a = li.querySelector('a[href*="/in/"]');
    const title = li.innerText;
    return a ? { href: a.href.split('?')[0], title: title.split('\n').slice(0, 4).join(' | ') } : null;
  }).filter(Boolean).filter(x => /COMPANY_REGEX/i.test(x.title)).slice(0, 8)
```

**Pattern C — entity-result divs (when card text empty):**

```javascript
Array.from(document.querySelectorAll('div.entity-result__content')).map(div => {
  const a = div.querySelector('a[href*="/in/"]');
  return a ? { href: a.href.split('?')[0], t: div.innerText.slice(0, 160) } : null;
}).filter(Boolean).filter(x => /COMPANY_REGEX/i.test(x.t)).slice(0, 6)
```

**Pattern D — quick dump when cards match visually (Businessonbot first pass):**

```javascript
Array.from(document.querySelectorAll('a[href*="/in/"]')).slice(0, 30)
  .map(a => ({ href: a.href.split('?')[0], text: a.innerText.trim().slice(0, 120) }))
  .filter(x => x.text.length > 2)
```

Manually filter results to people showing the target company in snapshot/card text.

**Step 5 — Verify URLs before writing**

- **Never guess** `/in/` slugs from names (e.g. `dhruv-grover-ml` was wrong; correct slug required WebSearch)
- If CDP returns names but empty/wrong hrefs: `WebSearch` with `site:linkedin.com/in {Full Name} {Company}`
- Optionally open a profile with `browser_click` on snapshot ref to confirm employment
- Strip query params: `a.href.split('?')[0]`

**Step 6 — Company LinkedIn page**

Find via search card or WebSearch. Format: `Company: https://www.linkedin.com/company/{handle}/`

Known handles from test run:

| Company (sheet) | Company page |
| --- | --- |
| Businessonbot | `https://www.linkedin.com/company/businessonbot/` |
| SuperProfile | `https://www.linkedin.com/company/cosmofeed/` (brand is Cosmofeed on LinkedIn) |
| Boock.ai | `https://www.linkedin.com/company/boock-ai/` |
| Prodigal | `https://www.linkedin.com/company/prodigaltech/` |
| HackerRank | `https://www.linkedin.com/company/hackerrank/` |

**Step 7 — Scroll if needed**

If fewer than 4 results visible: `browser_scroll` direction `down`, amount `800`, re-run CDP extract.

### Known company aliases (Aug 2026 test)

| Sheet name | LinkedIn search notes |
| --- | --- |
| SuperProfile | Employees often show **Cosmofeed**; search `"SuperProfile" Cosmofeed` |
| Businessonbot (Y Combinator W21) | LinkedIn brand **BusinessOnBot** |
| Boock.ai | Match `/boock/i` in card text |
| Prodigal | Match `/prodigal/i` or `/@\s*prodigal|at prodigal/i` in card |
| HackerRank | Large company — prioritize TA (`Talent Acquisition`) + eng leadership |

### What not to do on LinkedIn

- Do not send messages, InMails, or connection requests
- Do not run parallel LinkedIn searches in multiple tabs
- Do not guess profile URL slugs without verification
- Do not add people whose card does not mention the target company (unless company is tiny and they are clearly founders)

---

## Sheet write runbook (exact steps)

**Do not use Cursor Browser** to type into Leads (G) or Add note Message (H) — same commit failure as Jobgru (Enter/Tab does not persist).

### Step 0 — Auth check

If any write returns `403` or auth error:

```bash
gcloud auth login --enable-gdrive-access --update-adc
.venv/bin/python scripts/sheets_write.py test --cleanup
```

### Step 1 — Build leads text and note for row R

From verified LinkedIn results + template rotation (see [Add note Message](#add-note-message-column-h)).

### Step 2 — Write G and H in one call

```bash
.venv/bin/python scripts/sheets_write.py write \
  --range "G${R}:H${R}" \
  --json '[["<leads text with \n newlines>", "<add note message>"]]'
```

Use `--json` with a 2-element array `[leads, note]` — handles newlines in leads correctly.

Alternative (two calls):

```bash
.venv/bin/python scripts/sheets_write.py write --range "G${R}" --value "<leads text>"
.venv/bin/python scripts/sheets_write.py write --range "H${R}" --value "<add note message>"
```

**Batch write** (multiple rows after all searches — less preferred; write per row is safer):

```python
from scripts.sheets_write import sheets_service, write_range
service = sheets_service()
write_range(service, "<spreadsheet_id from config/sheet.json>", "Job Applications", f"G{R}:H{R}", [[leads, note]])
```

### Step 3 — Verify

```bash
.venv/bin/python scripts/sheets_write.py read --range "A${R}:H${R}"
```

Confirm: G has `/in/` URLs, H has `Hi,` + role + company + resume link, D still `to apply`.

### Step 4 — Sheet layout (overflow)

After writing Leads and Add note Message, ensure long text wraps inside columns (not spilling into neighbors):

```bash
.venv/bin/python scripts/sheets_write.py format-layout
```

Column widths: F=240px, G=280px, H=300px, O (templates)=300px. Re-run anytime.

### Step 5 — Run JSON

**Pipeline mode** — merge into Jobgru run file:

```json
{
  "pipeline": { "phase1": "jobgru", "phase2": "leadgru", "status": "complete" },
  "start_row": 27,
  "end_row": 31,
  "leadgru_rows_processed": [27, 28, 29, 30, 31],
  "leadgru_status": "complete",
  "leadgru_skipped": [],
  "linkedin_method": "cursor_browser_cdp",
  "notes": ["SuperProfile → Cosmofeed on LinkedIn"]
}
```

**Standalone mode** — separate file `data/runs/leadgru-<YYYY-MM-DD-HHMM>.json`:

```json
{
  "mode": "standalone",
  "rows_processed": [22, 23, 24, 25, 26],
  "sheet_write_method": "sheets_api",
  "linkedin_method": "cursor_browser_cdp"
}
```

### All sheet commands (reference)

| Command | Purpose |
| --- | --- |
| `read --range "A2:H500"` | Find eligible rows |
| `read --range "Q1:Q7"` | Load Add note templates |
| `write --range "G{R}:H{R}" --json '[["...", "..."]]'` | Write leads + note |
| `read --range "A{R}:H{R}"` | Verify one row |
| `format-layout` | Wrap text + column widths (F/G/H/I/J/Q) — run after batch if overflow |
| `test --cleanup` | Auth smoke test |

Optional flags: `--spreadsheet-id`, `--tab "Job Applications"`.

---

## Do not use Cursor Browser for sheet writes

Browser automation **does not persist** Google Sheet edits in this environment. Confirmed same failure as Jobgru:

| Action tried | Result |
| --- | --- |
| Navigate to sheet URL | OK |
| Click cell / type in editor | Text shows in UI only |
| Press Enter or Tab | **Does not commit** |
| Sheets API read | **No new data** |

Use Sheets API for columns G and H only. Use Cursor Browser for LinkedIn only.

Do **not** open duplicate sheet tabs for writing.

---

## Safety

- Do not send messages, InMails, connection requests, or applications
- Do not guess employment at the company
- Stop LinkedIn on warnings; report and continue to next company if safe

## Quality check

1. Processed rows still have Status `to apply` in column D
2. No pre-filled Leads rows changed
3. Each new Leads cell (G) has 4–10 verified `/in/` links, or fewer + company page, or company page alone
4. Every `/in/` URL verified (not guessed slugs)
5. Add note Message (H) has role, company, resume link, greeting `Hi,`, no lead names
6. Columns A–F, E, K+ unchanged; **I (ATS score)** and **J (Suggestions on Resume)** untouched by LeadGru
7. Sheets API verify passed for processed range

## Completion report

**Pipeline mode:** Do not publish a separate LeadGru report — Jobgru coordinator merges Phase 2 into the combined completion summary.

**Standalone mode:** Report in chat and save to `data/runs/`:

- Mode: standalone backfill
- Eligible rows processed (row numbers + companies)
- Skipped (Leads already filled or Status not `to apply`)
- Per row: people count, company page included Y/N
- LinkedIn access limits (CAPTCHA, login, rate limit)
- Any company alias notes (e.g. SuperProfile → Cosmofeed)
- Sheet link
