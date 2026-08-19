# ATSScore standalone (backfill)

Use when jobs are already in the sheet but column **I (ATS score)** is empty for `to apply` rows.

Requires resumes in `data/resumes/` — see [data/resumes/README.md](../data/resumes/README.md).

Sheet headers: **I1** = `ATS score`, **J1** = `Suggestions on Resume`.

```text
Use the atsscore skill (standalone backfill).

Google Sheet:
Google Sheet (read URL from config/sheet.json → sheet_url):

Score all rows where Status is "to apply" and ATS score (column I) is empty.
Write Suggestions on Resume to column J for successfully scored rows only.

Resumes: all

Run:
  .venv/bin/python scripts/ats_score.py score --all

Optional dry-run first:
  .venv/bin/python scripts/ats_score.py score --all --dry-run

Then:
  .venv/bin/python scripts/sheets_write.py format-layout

Report: rows scored, rows skipped (no Skills in Details), resumes used.
Do not overwrite existing ATS scores. Do not use LLM or fetch job URLs.
```
