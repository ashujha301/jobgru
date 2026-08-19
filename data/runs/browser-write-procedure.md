# Browser sheet write procedure (Jobgru coordinator)

Use this when appending rows via Cursor Browser to the Job Applications sheet.

## Steps per row

1. Open sheet URL and confirm tab `Job Applications`.
2. Read existing rows (Drive MCP or browser) to find first empty row in column A.
3. For each cell A–E on that row:
   - Fill the **name box** with the cell reference (e.g. `E22`) and press **Enter**.
   - Fill the **formula bar** with the value and press **Enter**.
4. Leave F and G blank for Jobgru rows.
5. Re-read the sheet to verify the row and `Apply:` URL in Details.

## Smoke test row (row 22)

| Cell | Value |
| --- | --- |
| A22 | Jobgru Smoke Test Co |
| B22 | AI Engineer |
| C22 | to apply |
| D22 | 18/8/2026 |
| E22 | Pay: Not stated, Exp: 2 years, Visa: Not stated, Remote, India, Posted: smoke test, Apply: https://wellfound.com/jobs/smoke-test-jobgru |

Delete this row after verifying browser writes work.
