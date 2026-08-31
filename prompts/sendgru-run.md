# SendGru — on-demand LinkedIn connection notes

**Not part of the Jobgru pipeline.** Run only when you explicitly ask to send add notes.

LeadGru still finds **5 people + company people page** on `to apply` rows. SendGru sends to **2 people per row** only.

## Example chat prompt

```text
SendGru rows 4-12

Use sendgru skill. Sheets API for reads/writes only.

Step 1 — Select targets:
  .venv/bin/python scripts/sendgru_select.py --rows "4-12" --apply-daily-cap

Step 2 — Send (pick first working browser path):

**A. Cursor Browser MCP** — follow `data/linkedin-runbooks/connect-add-note.json`

**Profile Connect (fixed — do not guess):**

1. If **Pending** — skip this person.
2. If **Message** only (already connected) — click **Message**, paste exact column H text, click **Send**.
3. **Path A:** Blue **Connect** button in the profile header → click it.
4. **Path B:** No Connect, but **Follow** is shown → click **More** → **Connect** in the dropdown list.
5. Modal opens with **Add a note** and **Send without a note** — always use **Add a note** (never send without a note).
6. Paste exact column H text → **Send invitation**.

**B. If MCP disconnected** — Playwright CLI (no reload required):

```bash
.venv/bin/python scripts/sendgru_playwright.py --rows "4-12" --apply-daily-cap
```

**C. Manual mark after MCP sends** (if you sent via browser MCP, not CLI):

```bash
.venv/bin/python scripts/sendgru_select.py --rows "{ROW}" --mark-sent
```

Playwright CLI marks rows automatically after successful sends.

Do not send if H is empty or over 300 characters (Premium).
Do not auto-run after Jobgru.
```

## Row spec examples

| You say | `--rows` value |
| --- | --- |
| rows 4-12 | `4-12` |
| row 8 | `8` |
| 4, 6, 9 | `4,6,9` |

## Eligibility

- Status (D) = **applied** (case-insensitive)
- Leads (G) has at least one `/in/` URL
- Add note Message (H) = template text, **1–300 chars** (Premium), does not already contain `Sent add note`

## After send

Column H keeps the original note and **appends** ` Sent add note` in the same cell.
