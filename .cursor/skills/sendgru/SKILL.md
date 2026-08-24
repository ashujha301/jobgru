---
name: sendgru
description: Jobgru on-demand — send LinkedIn connection invites with add-note text for user-named sheet rows. Only Status applied; 2 people per row from Leads; appends Sent add note to column H after success (does not replace the note). Never runs in the Jobgru pipeline. Use when the user says SendGru, send add notes, send connection notes, or names rows to send invites.
---

# SendGru (on-demand connection + note)

Send LinkedIn **Connect → Add a note → Send** for rows the user names. **Never** runs automatically after Jobgru or LeadGru.

LeadGru is unchanged: it still finds **5 people + company people page** on `to apply` rows. SendGru only sends to **2** of those people so you cover more companies per week.

## Hard rules

| Rule | Value |
| --- | --- |
| Trigger | User must name rows (`4-12`, `8`, `4,6,9`) or say SendGru / send add notes |
| Pipeline | **Never** part of Jobgru Phase 1/2/2b |
| Status filter | **applied** only (case-insensitive) |
| People per row | **2** — first two `/in/` URLs in column G; skip `Company:` line |
| Note source | Column H **before** send (LeadGru template text) |
| Note length | **1–300** characters (Premium desktop). Skip if empty or over 300 |
| After success | **Append** ` Sent add note` to the existing H text (same cell; do not replace) |
| Already sent | Skip if H already contains `Sent add note` |
| Sheet writes | **Sheets API only** — never browser-type into the sheet |
| LinkedIn tabs | **One** tab |
| Daily cap | **20** sends per run (use `--apply-daily-cap` on select script) |
| Stop | CAPTCHA, checkpoint, weekly invitation limit → unlock, report partial, **no retries this session** |

## Prerequisites

```bash
.venv/bin/python scripts/jobgru_check.py --json
```

- LinkedIn logged in (Premium: connection notes up to **300** characters)
- Rows must have Leads (G) filled (usually from LeadGru) and Add note Message (H) from templates
- User must have set Status to **applied** after applying to the job

## Coordinator workflow

### 1 — Parse rows and load sheet

```bash
.venv/bin/python scripts/sendgru_select.py --rows "4-12" --apply-daily-cap
```

Or read manually:

```bash
.venv/bin/python scripts/sheets_write.py read --range "A4:H12"
```

Use [`scripts/sendgru_select.py`](../../scripts/sendgru_select.py) JSON output: `actionable` vs `skipped`.

### 2 — Browser lock

1. `browser_tabs` list
2. If LinkedIn tab exists: `browser_lock` lock first
3. Else: `browser_navigate` to first profile URL, then lock

Read runbook: [`data/linkedin-runbooks/connect-add-note.json`](../../data/linkedin-runbooks/connect-add-note.json)

### 3 — Per person (max 2 per row)

**Before each profile navigate after the first:** blocking sleep **60–90 seconds** (randomize in range; do not batch).

Follow runbook steps in order:

1. Navigate to `/in/` URL
2. Snapshot — if page shows stop phrases (see runbook `stop_phrases`), **stop session**
3. If **Message** only (already connected) or **Pending** — skip person, continue
4. Click **Connect** (fallback: **More** → **Connect**)
5. Click **Add a note** (if missing, skip person — do not use “Send without a note”)
6. Paste **exact** column H text (`browser_fill` or type)
7. Click **Send** / **Send invitation**
8. Wait **5s**, snapshot to confirm dialog closed

**Between companies** (after finishing a row’s people): extra **30s** before next row’s first profile.

### 4 — Mark row done

After finishing a row (sent 1–2 people successfully on that row), **append** `Sent add note` to the existing H text. Never replace the note.

```bash
.venv/bin/python scripts/sendgru_select.py --rows "{ROW}" --mark-sent
```

- Mark row **only** if at least one invite sent successfully for that row
- If both people skipped (already connected), **do not** append `Sent add note` — report row
- If session stopped mid-row due to rate limit, **do not** mark partial rows unless user confirms
- Do **not** `sheets_write.py write --value "Sent add note"` — that wipes the template text

### 5 — Unlock and report

```bash
browser_lock action unlock
```

Save summary to `data/runs/sendgru-<YYYY-MM-DD-HHMM>.json`:

```json
{
  "mode": "sendgru",
  "rows_requested": [4, 5, 6],
  "rows_sent": [4, 5],
  "rows_skipped": [{"row": 6, "reason": "already Sent add note"}],
  "people_sent": 4,
  "stopped_reason": null
}
```

## Column reference

| Column | Header | SendGru |
| --- | --- | --- |
| A | Company Name | Read |
| B | Position | Read |
| D | Status | Must be **applied** |
| G | Leads | Read — first **2** `/in/` only |
| H | Add note Message | Read note to send → **append** ` Sent add note` after send |

## What not to do

- Do not run after every job search
- Do not send to 5 people per company (LeadGru bench stays on sheet; you send 2)
- Do not send if H is empty or over **300** chars (Premium limit)
- Do not replace H with only `Sent add note` — always append to the existing text
- Do not append `Sent add note` if zero invites sent on that row
- Do not use InMail
- Do not parallel LinkedIn tabs
- Do not retry after CAPTCHA / weekly limit in the same session
- Do not type into Google Sheet in the browser

## LinkedIn limits (Premium)

LinkedIn does not publish exact weekly invite counts. Observed safe band: **~100–200 invites / rolling 7 days**. This skill defaults to **20 sends/run** and **60–90s** between people to reduce restriction risk. **Cannot guarantee** zero rate limits.

Connection note on desktop Premium: up to **300** characters. SendGru skips only if H is empty or over 300. LeadGru still writes new H notes at **≤ 200** from sheet templates.

## Standalone prompt

Copy from [`prompts/sendgru-run.md`](../../prompts/sendgru-run.md).

## Test order

1. Unit tests: `python -m unittest tests.test_sendgru_select`
2. Dry run: `sendgru_select.py --rows "N"` — confirm actionable/skipped
3. Live: **one** applied row (2 sends max), then re-run → row skipped (H contains `Sent add note`)
4. Larger ranges only after a clean single-row test

## Related skills

| Skill | Relationship |
| --- | --- |
| [leadgru/SKILL.md](../leadgru/SKILL.md) | Finds 5 people + note template — **does not send** |
| [jobgru/SKILL.md](../jobgru/SKILL.md) | Pipeline — **does not send invites** |
