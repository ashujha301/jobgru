# LeadGru standalone run prompt (backfill only)

Use this **only** when Jobgru already ran but Leads (G) / Add note Message (H) were never filled — e.g. LinkedIn blocked mid-pipeline, or an older row was added manually.

For a normal run, use [jobgru-run.md](jobgru-run.md) instead — LeadGru runs automatically as Phase 2.

```text
Use the leadgru skill in STANDALONE mode (read full SKILL.md — LinkedIn + Sheets API runbooks).

Google Sheet:
Google Sheet (read URL from config/sheet.json → sheet_url):

Step 1 — Read via Sheets API (not browser):
  scripts/sheets_write.py read --range "A2:H"
  scripts/sheets_write.py read --range "Q1:Q7"

Process every row where Status (column D) is "to apply" and Leads (column G) is empty.
Do NOT limit to a specific row range unless the user named one (e.g. "rows 27–31 only").

Step 2 — LinkedIn (Cursor Browser, one company at a time):
  browser_navigate → browser_lock → for each row:
    (0) If apply link (column C) is linkedin.com/jobs/view/... — open job page first;
        extract "Meet the hiring team" / job poster / any /in/ profiles on the listing (priority leads)
    (1) people search URL → CDP extract → fill remaining slots up to 5 total
  browser_unlock when done
  Primary URL: https://www.linkedin.com/search/results/people/?keywords={COMPANY}&origin=GLOBAL_SEARCH_HEADER
  Use .linked-area CDP pattern from skill; WebSearch to verify /in/ slugs — never guess URLs.
  Job-posting profiles go FIRST in column G; dedupe URLs; merge with search results (max 5 /in/).

Step 3 — Write each row immediately via Sheets API (NOT browser):
  scripts/sheets_write.py write --range "G{R}:H{R}" --json '[["<leads>", "<note>"]]'

Step 4 — Verify and layout:
  scripts/sheets_write.py read --range "A{start}:H{end}"
  scripts/sheets_write.py format-layout

Target **at most 5** verified people per row + last line `Company: linkedin.com/company/.../people/`.
Add note: rotate Q2–Q7, fill with `scripts/leadgru_notes.py fill` (≤ 200 chars, Hi, + Thanks, no names). Do not overwrite existing H.

Do not send messages, InMails, connection requests, or applications.
Stop and report CAPTCHA, login, or rate-limit warnings on LinkedIn.
Skip rows that are not "to apply" or already have Leads.
```

## Example: backfill specific rows

```text
Use the leadgru skill in STANDALONE mode.

Backfill rows 27–31 only (Cisco, WisdomAI, UNO Digital Bank, Margn AI, Snapfix).
Leads (G) is empty on all five; Status is to apply.

Follow leadgru skill runbook. Write G/H via Sheets API. format-layout when done.
```
