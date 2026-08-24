# SendGru — on-demand LinkedIn connection notes

**Not part of the Jobgru pipeline.** Run only when you explicitly ask to send add notes.

LeadGru still finds **5 people + company people page** on `to apply` rows. SendGru sends to **2 people per row** only.

## Example chat prompt

```text
SendGru rows 4-12

Use sendgru skill. Sheets API for reads/writes only.

Step 1 — Select targets:
  .venv/bin/python scripts/sendgru_select.py --rows "4-12" --apply-daily-cap

Step 2 — For each actionable row (Status applied, H not "Sent add note"):
  - Send column H note to first 2 /in/ URLs in column G
  - Follow data/linkedin-runbooks/connect-add-note.json
  - 60-90s sleep before each profile navigate (after the first)
  - Stop on CAPTCHA / weekly invitation limit

Step 3 — After row completes (1-2 successful sends):
  .venv/bin/python scripts/sheets_write.py write --range "H{ROW}" --value "Sent add note"

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
- Add note Message (H) = template text, **1–300 chars** (Premium), not already `Sent add note`

## After send

Column H becomes exactly: **`Sent add note`**
