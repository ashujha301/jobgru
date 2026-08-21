# Google Sheets API setup

Jobgru and LeadGru write to your sheet through `scripts/sheets_write.py`. Browser cell editing in Cursor **does not persist** — use this API path only.

See also: [README.md](../README.md) for the full user guide.

---

## Option A — gcloud with Drive access (recommended)

Use the Google account that **owns** the sheet.

```bash
# From project root
python3 -m venv .venv
.venv/bin/pip install -r scripts/requirements.txt

gcloud auth login --enable-gdrive-access --update-adc
```

Sign in in the browser when prompted.

Verify:

```bash
.venv/bin/python scripts/sheets_write.py test --cleanup
```

Expected output: `OK: Sheets API write verified`

### Common mistakes

| Mistake | Result |
| --- | --- |
| `gcloud auth login` without `--enable-gdrive-access` | `403 insufficient scopes` |
| `gcloud auth application-default login --scopes=.../spreadsheets` | *"This app is blocked"* |
| Wrong Google account | Sheet not found or permission denied |
| Template URL in setup (viewer only) | Cannot write — use **your copy** URL after File → Make a copy |
| Viewer or Commenter on the sheet | Permission denied — need **Editor** or **Owner** for the gcloud account |
| Wrong Google account in gcloud | Re-auth with the account that has Editor/Owner on the sheet |
| Confusion: "anyone with link → Editor" | **Not required** for solo setup — Owner after Make a copy is enough |

Re-auth when token expires:

```bash
gcloud auth login --enable-gdrive-access --update-adc
```

---

## Option B — OAuth desktop client

Use if gcloud Drive login is unavailable.

1. [Google Cloud Console](https://console.cloud.google.com/) → create project → enable **Google Sheets API**
2. **OAuth consent screen** → External → add yourself as **Test user**
3. **Credentials → OAuth client ID → Desktop app** → download JSON
4. Save as `scripts/oauth-client.json` (gitignored)
5. Run:
   ```bash
   .venv/bin/python scripts/sheets_write.py auth login
   .venv/bin/python scripts/sheets_write.py test --cleanup
   ```

---

## Option C — Service account

1. Create service account + JSON key in Google Cloud Console
2. `export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json`
3. Share the sheet with the service account email as **Editor**
4. Run `test --cleanup`

---

## CLI reference

All commands from **project root**:

| Command | Purpose |
| --- | --- |
| `auth login` | One-time OAuth (Option B) |
| `auth status` | Check saved OAuth token |
| `test --cleanup` | Write/read/clear smoke test on A22 |
| `first-empty` | Print next safe append row (after last occupied A–C + last-run cursor) |
| `first-empty --json` | Include `last_occupied_row` and `data/runs/sheet-append-cursor.json` |
| `read --range "A2:H"` | Read all job rows (open-ended) |
| `append --file FILE` | Append after last occupied row; refuses mid-sheet overwrite |
| `append --file FILE --start-row N` | Write at N only when safe (`--force-overwrite` to bypass) |
| `write --range "G5:H5" --json '[["a","b"]]'` | Write Leads + note (LeadGru) |
| `format-layout` | Wrap text + column widths for F/G/H/O (prevents overflow) |

Defaults (override with flags or `config/sheet.json`):

- Spreadsheet ID: from `config/sheet.json` → `spreadsheet_id`
- Tab: `Job Applications`

---

## Row format (Jobgru)

`pending-rows.json` — array of 8-string rows `[A..H]`:

```json
[
  [
    "Company",
    "Position",
    "https://apply-url",
    "to apply",
    "19/8/2026",
    "Pay: ..., Exp: ..., Visa: ..., Onsite, City, Posted: ...",
    "",
    ""
  ]
]
```

Column C = bare URL (plain text, no dropdown validation).
