#!/usr/bin/env python3
"""Write to the Job Applications Google Sheet via Sheets API.

Google blocks gcloud's default OAuth client for the spreadsheets scope.
Use one of these auth paths (first match wins):

  1. GOOGLE_ACCESS_TOKEN env var
  2. GOOGLE_APPLICATION_CREDENTIALS (service account JSON; share sheet with SA email)
  3. scripts/.sheets-token.json (from: sheets_write.py auth login)
  4. Application Default Credentials (often blocked for spreadsheets — avoid)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_TOKEN_PATH = SCRIPT_DIR / ".sheets-token.json"
DEFAULT_CLIENT_SECRETS = SCRIPT_DIR / "oauth-client.json"

from sheet_cells import sanitize_sheet_rows, sanitize_sheet_value  # noqa: E402
from sheet_config import get_spreadsheet_id, get_tab  # noqa: E402

DEFAULT_SPREADSHEET_ID = get_spreadsheet_id()
DEFAULT_TAB = get_tab()
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _resolve_client_secrets(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit).expanduser()
    else:
        env = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRETS")
        path = Path(env).expanduser() if env else DEFAULT_CLIENT_SECRETS
    if not path.is_file():
        raise SystemExit(
            f"OAuth client secrets not found at {path}.\n"
            "Create a Desktop OAuth client in Google Cloud Console, enable Sheets API,\n"
            "download JSON, and save it as scripts/oauth-client.json\n"
            "See scripts/SHEETS-API-SETUP.md for step-by-step instructions."
        )
    return path


def _load_user_token(token_path: Path) -> Credentials | None:
    if not token_path.is_file():
        return None
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
    return creds


def get_credentials() -> Credentials:
    token = os.environ.get("GOOGLE_ACCESS_TOKEN")
    if token:
        return Credentials(token=token, scopes=SCOPES)

    sa_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if sa_path and Path(sa_path).is_file():
        return ServiceAccountCredentials.from_service_account_file(sa_path, scopes=SCOPES)

    token_path = Path(os.environ.get("SHEETS_TOKEN_PATH", DEFAULT_TOKEN_PATH))
    creds = _load_user_token(token_path)
    if creds and creds.valid:
        return creds

    try:
        from google.auth import default

        adc, _ = default(scopes=SCOPES)
        if hasattr(adc, "refresh") and not adc.valid:
            adc.refresh(Request())
        return adc
    except Exception as exc:
        raise SystemExit(
            "Google Sheets auth failed.\n\n"
            "gcloud's default OAuth client is blocked for spreadsheets scope.\n"
            "Fix (pick one):\n"
            "  A) OAuth desktop client (recommended):\n"
            "     1. Follow scripts/SHEETS-API-SETUP.md\n"
            "     2. Save client JSON as scripts/oauth-client.json\n"
            "     3. Run: .venv/bin/python scripts/sheets_write.py auth login\n"
            "  B) Service account:\n"
            "     1. Create SA key JSON, set GOOGLE_APPLICATION_CREDENTIALS\n"
            "     2. Share the sheet with the SA email as Editor\n\n"
            f"Original error: {exc}"
        ) from exc


def sheets_service():
    return build("sheets", "v4", credentials=get_credentials(), cache_discovery=False)


def read_range(service, spreadsheet_id: str, tab: str, cell_range: str) -> list[list[str]]:
    quoted_tab = f"'{tab}'" if " " in tab else tab
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"{quoted_tab}!{cell_range}")
        .execute()
    )
    return result.get("values", [])


def write_range(
    service,
    spreadsheet_id: str,
    tab: str,
    cell_range: str,
    values: list[list[str]],
    *,
    value_input_option: str = "USER_ENTERED",
    sanitize: bool = True,
) -> dict:
    quoted_tab = f"'{tab}'" if " " in tab else tab
    if sanitize:
        values = sanitize_sheet_rows(values)
    body = {"values": values}
    return (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=f"{quoted_tab}!{cell_range}",
            valueInputOption=value_input_option,
            body=body,
        )
        .execute()
    )


def append_rows(
    service,
    spreadsheet_id: str,
    tab: str,
    rows: list[list[str]],
    *,
    value_input_option: str = "USER_ENTERED",
) -> dict:
    quoted_tab = f"'{tab}'" if " " in tab else tab
    body = {"values": sanitize_sheet_rows(rows)}
    return (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=spreadsheet_id,
            range=f"{quoted_tab}!A:H",
            valueInputOption=value_input_option,
            insertDataOption="INSERT_ROWS",
            body=body,
        )
        .execute()
    )


def get_sheet_properties(service, spreadsheet_id: str, tab: str) -> dict:
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sheet in meta.get("sheets", []):
        if sheet["properties"]["title"] == tab:
            return sheet["properties"]
    raise SystemExit(f"Tab not found: {tab!r}")


def get_sheet_id(service, spreadsheet_id: str, tab: str) -> int:
    return int(get_sheet_properties(service, spreadsheet_id, tab)["sheetId"])


def last_data_row(service, spreadsheet_id: str, tab: str, *, start_row: int = 2) -> int:
    """Last row with a value in column A (1-based). Header-only sheet returns start_row - 1."""
    values = read_range(service, spreadsheet_id, tab, f"A{start_row}:A")
    return last_occupied_row_from_values(values, start_row=start_row, columns=1)


def last_occupied_row_from_values(
    values: list[list],
    *,
    start_row: int = 2,
    columns: int = 3,
) -> int:
    """Last 1-based row that has any non-empty cell in the first `columns` fields.

    Used for append positioning so a blank Company (A) mid-sheet cannot pull
    writes into the middle of existing Position/Apply data.
    Header-only / empty sheet → start_row - 1.
    """
    last = start_row - 1
    for idx, row in enumerate(values):
        cells = list(row or [])
        # Pad so short rows still check available cells
        chunk = cells[:columns]
        if any(str(c).strip() for c in chunk):
            last = start_row + idx
    return last


def last_occupied_row(
    service,
    spreadsheet_id: str,
    tab: str,
    *,
    start_row: int = 2,
) -> int:
    """Last row with any value in A–C (Company / Position / Apply link)."""
    values = read_range(service, spreadsheet_id, tab, f"A{start_row}:C")
    return last_occupied_row_from_values(values, start_row=start_row, columns=3)


def append_cursor_path() -> Path:
    from jobgru_home import get_jobgru_home

    return get_jobgru_home() / "data" / "runs" / "sheet-append-cursor.json"


def load_append_cursor(spreadsheet_id: str) -> dict | None:
    path = append_cursor_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if data.get("spreadsheet_id") != spreadsheet_id:
        return None
    return data


def save_append_cursor(
    *,
    spreadsheet_id: str,
    tab: str,
    start_row: int,
    end_row: int,
    rows_written: int,
) -> Path:
    path = append_cursor_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "spreadsheet_id": spreadsheet_id,
        "tab": tab,
        "last_start_row": start_row,
        "last_end_row": end_row,
        "next_row": end_row + 1,
        "rows_written": rows_written,
        "updated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def next_append_row(
    service,
    spreadsheet_id: str,
    tab: str,
    *,
    start_row: int = 2,
) -> int:
    """Row where the next Jobgru batch must begin (never inside existing data).

    Primary signal: last occupied A–C row + 1 (a blank Company mid-sheet cannot
    pull writes into existing Position/Apply rows).

    Persisted cursor ``next_row`` is a floor from the last successful append so
    the watermark cannot silently reset to a low row. If the cursor is ahead of
    the sheet but the gap is empty (trailing rows deleted outside Jobgru), the
    cursor is realigned to the sheet.
    """
    sheet_last = last_occupied_row(service, spreadsheet_id, tab, start_row=start_row)
    sheet_next = max(sheet_last + 1, start_row)
    cursor = load_append_cursor(spreadsheet_id)
    cursor_next = int(cursor["next_row"]) if cursor and cursor.get("next_row") else None
    if cursor_next is None or cursor_next <= sheet_next:
        return sheet_next

    # Cursor ahead of sheet occupancy — check whether the gap is empty.
    if cursor_next > sheet_next:
        gap = read_range(
            service, spreadsheet_id, tab, f"A{sheet_next}:C{cursor_next - 1}"
        )
        gap_occupied = any(
            any(str(c).strip() for c in (row or [])[:3]) for row in gap
        )
        if not gap_occupied:
            save_append_cursor(
                spreadsheet_id=spreadsheet_id,
                tab=tab,
                start_row=sheet_last if sheet_last >= 2 else 2,
                end_row=sheet_last if sheet_last >= 2 else 1,
                rows_written=0,
            )
            return sheet_next
    return cursor_next


def assert_append_range_clear(
    service,
    spreadsheet_id: str,
    tab: str,
    start_row: int,
    num_rows: int,
) -> None:
    """Refuse to write over any occupied Company/Position/Apply cells."""
    if num_rows <= 0:
        return
    end_row = start_row + num_rows - 1
    values = read_range(service, spreadsheet_id, tab, f"A{start_row}:C{end_row}")
    conflicts: list[int] = []
    for idx, row in enumerate(values):
        if any(str(c).strip() for c in (row or [])[:3]):
            conflicts.append(start_row + idx)
    if conflicts:
        preview = ", ".join(str(r) for r in conflicts[:8])
        more = f" (+{len(conflicts) - 8} more)" if len(conflicts) > 8 else ""
        raise SystemExit(
            f"Refusing to overwrite existing sheet data at row(s) {preview}{more}.\n"
            f"Requested write: A{start_row}:H{end_row}.\n"
            "Use `sheets_write.py first-empty` (next append row after last occupied A–C),\n"
            "or omit --start-row so append picks the safe row automatically.\n"
            "Pass --force-overwrite only if you intentionally mean to replace those cells."
        )


def layout_end_row(service, spreadsheet_id: str, tab: str) -> int:
    """Format through the sheet's current grid (grows as jobs are appended). No 500 cap."""
    props = get_sheet_properties(service, spreadsheet_id, tab)
    grid_rows = int(props.get("gridProperties", {}).get("rowCount") or 0)
    used = last_occupied_row(service, spreadsheet_id, tab)
    return max(grid_rows, used + 1, 2)


def parse_row_spec(spec: str) -> list[int]:
    """Parse row numbers: 42 | 42,43 | 42-44 | 42,44-46"""
    rows: set[int] = set()
    for chunk in spec.replace(" ", "").split(","):
        if not chunk:
            continue
        if "-" in chunk:
            start_s, end_s = chunk.split("-", 1)
            start, end = int(start_s), int(end_s)
            if start > end:
                start, end = end, start
            rows.update(range(start, end + 1))
        else:
            rows.add(int(chunk))
    return sorted(rows)


def group_contiguous_rows(rows: list[int]) -> list[tuple[int, int]]:
    """Group 1-based row numbers into contiguous (start, end) inclusive ranges."""
    if not rows:
        return []
    groups: list[tuple[int, int]] = []
    start = prev = rows[0]
    for row in rows[1:]:
        if row == prev + 1:
            prev = row
            continue
        groups.append((start, prev))
        start = prev = row
    groups.append((start, prev))
    return groups


def delete_sheet_rows(
    service,
    spreadsheet_id: str,
    tab: str,
    row_numbers: list[int],
) -> dict:
    if not row_numbers:
        raise SystemExit("No rows to delete")
    if any(row < 2 for row in row_numbers):
        raise SystemExit("Cannot delete row 1 (header row)")
    sheet_id = get_sheet_id(service, spreadsheet_id, tab)
    requests: list[dict] = []
    for start_row, end_row in reversed(group_contiguous_rows(row_numbers)):
        requests.append(
            {
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": start_row - 1,
                        "endIndex": end_row,
                    }
                }
            }
        )
    return (
        service.spreadsheets()
        .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
        .execute()
    )


def find_first_empty_row(service, spreadsheet_id: str, tab: str, *, start_row: int = 2) -> int:
    """Deprecated name — returns the next safe append row (after last occupied A–C).

    Historically scanned for the first blank in column A, which could land inside
    existing jobs when Company was empty but Position/Apply were filled. Jobgru
    append must never use mid-sheet gaps.
    """
    return next_append_row(service, spreadsheet_id, tab, start_row=start_row)


# Column widths (px) for Job Applications tab — keeps long text inside cells with wrap.
DEFAULT_COLUMN_WIDTHS: dict[int, int] = {
    0: 160,  # A Company Name
    1: 140,  # B Position
    2: 200,  # C Apply link
    3: 95,  # D Status
    4: 95,  # E Date Applied
    5: 240,  # F Details if any
    6: 280,  # G Leads
    7: 300,  # H Add note Message
    8: 140,  # I ATS score
    9: 300,  # J Suggestions on Resume
    11: 120,  # L Summary (was J before I/J insert)
    12: 70,  # M Count (was K)
    14: 140,  # O Latest Resume (was M)
    16: 300,  # Q Add Note Template (was O)
}


def apply_sheet_layout(
    service,
    spreadsheet_id: str,
    tab: str,
    *,
    wrap_columns: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 14, 16),
    max_row: int | None = None,
) -> dict:
    """Wrap text, top-align, and set column widths so cells do not overflow visually."""
    if max_row is None or max_row <= 0:
        max_row = layout_end_row(service, spreadsheet_id, tab)
    sheet_id = get_sheet_id(service, spreadsheet_id, tab)
    requests: list[dict] = []

    for col_index, pixel_size in DEFAULT_COLUMN_WIDTHS.items():
        requests.append(
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": col_index,
                        "endIndex": col_index + 1,
                    },
                    "properties": {"pixelSize": pixel_size},
                    "fields": "pixelSize",
                }
            }
        )

    for col_index in wrap_columns:
        requests.append(
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": max_row,
                        "startColumnIndex": col_index,
                        "endColumnIndex": col_index + 1,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "wrapStrategy": "WRAP",
                            "verticalAlignment": "TOP",
                        }
                    },
                    "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)",
                }
            }
        )

    requests.append(
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        }
    )

    requests.append(
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": 1,
                    "endIndex": max_row,
                }
            }
        }
    )

    return (
        service.spreadsheets()
        .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
        .execute()
    )


def cmd_auth_login(args: argparse.Namespace) -> int:
    from google_auth_oauthlib.flow import InstalledAppFlow

    client_secrets = _resolve_client_secrets(args.client_secrets)
    token_path = Path(args.token_path)

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)
    token_path.write_text(creds.to_json())
    print(f"Saved token to {token_path}")
    print("Run: .venv/bin/python scripts/sheets_write.py test --cleanup")
    return 0


def cmd_auth_status(args: argparse.Namespace) -> int:
    token_path = Path(args.token_path)
    if not token_path.is_file():
        print(f"No token at {token_path}")
        return 1
    creds = _load_user_token(token_path)
    if creds and creds.valid:
        print(f"Token valid at {token_path}")
        return 0
    print(f"Token expired or invalid at {token_path}; run auth login")
    return 1


def cmd_read(args: argparse.Namespace) -> int:
    service = sheets_service()
    values = read_range(service, args.spreadsheet_id, args.tab, args.range)
    print(json.dumps(values, indent=2))
    return 0


def cmd_write(args: argparse.Namespace) -> int:
    service = sheets_service()
    if args.json:
        values = json.loads(args.json)
    elif args.value is not None:
        values = [[args.value]]
    else:
        raise SystemExit("Provide --value or --json")

    result = write_range(service, args.spreadsheet_id, args.tab, args.range, values)
    print(json.dumps(result, indent=2))
    return 0


def cmd_append(args: argparse.Namespace) -> int:
    service = sheets_service()
    rows = json.loads(Path(args.file).read_text())
    if not isinstance(rows, list):
        raise SystemExit("--file must contain a JSON array of row arrays")
    if not rows:
        raise SystemExit("--file contains no rows to append")

    safe_start = next_append_row(service, args.spreadsheet_id, args.tab)
    if args.start_row is not None:
        start_row = int(args.start_row)
        if start_row < safe_start and not args.force_overwrite:
            raise SystemExit(
                f"--start-row {start_row} would overwrite or insert before existing data "
                f"(next safe append row is {safe_start}).\n"
                f"Omit --start-row, pass --start-row {safe_start}, or use "
                f"--force-overwrite only if you intentionally mean to replace cells."
            )
    else:
        start_row = safe_start

    end_row = start_row + len(rows) - 1
    if not args.force_overwrite:
        assert_append_range_clear(
            service, args.spreadsheet_id, args.tab, start_row, len(rows)
        )

    result = write_range(
        service,
        args.spreadsheet_id,
        args.tab,
        f"A{start_row}:H{end_row}",
        rows,
    )
    cursor_path = save_append_cursor(
        spreadsheet_id=args.spreadsheet_id,
        tab=args.tab,
        start_row=start_row,
        end_row=end_row,
        rows_written=len(rows),
    )
    out = dict(result)
    out["startRow"] = start_row
    out["endRow"] = end_row
    out["nextRow"] = end_row + 1
    out["appendCursor"] = str(cursor_path)
    print(json.dumps(out, indent=2))
    return 0


def cmd_test(args: argparse.Namespace) -> int:
    service = sheets_service()
    test_value = args.value
    cell = args.range

    print(f"Writing {test_value!r} to {args.tab}!{cell} ...")
    write_range(service, args.spreadsheet_id, args.tab, cell, [[test_value]])

    read_back = read_range(service, args.spreadsheet_id, args.tab, cell)
    print("Read back:", json.dumps(read_back, indent=2))

    if not read_back or read_back[0][0] != test_value:
        print("FAIL: value did not persist", file=sys.stderr)
        return 1

    print("OK: Sheets API write verified")
    if args.cleanup:
        write_range(service, args.spreadsheet_id, args.tab, cell, [[""]])
        print("Cleaned up test cell")
    return 0


def cmd_first_empty(args: argparse.Namespace) -> int:
    """Print the next safe append row (after last occupied A–C + cursor floor)."""
    service = sheets_service()
    sheet_last = last_occupied_row(
        service, args.spreadsheet_id, args.tab, start_row=args.start_row
    )
    row = next_append_row(
        service, args.spreadsheet_id, args.tab, start_row=args.start_row
    )
    cursor = load_append_cursor(args.spreadsheet_id)
    if args.json:
        print(
            json.dumps(
                {
                    "next_append_row": row,
                    "last_occupied_row": sheet_last,
                    "cursor": cursor,
                },
                indent=2,
            )
        )
    else:
        print(row)
    return 0


def cmd_restore_summary(args: argparse.Namespace) -> int:
    service = sheets_service()
    from sheet_validate import restore_summary_formulas, validate_summary_formulas

    restore_summary_formulas(service, args.spreadsheet_id, args.tab)
    ok, issues = validate_summary_formulas(service, args.spreadsheet_id, args.tab)
    result = {"summary_formulas": "restored" if ok else "restored_with_issues", "ok": ok, "issues": issues}
    print(json.dumps(result, indent=2))
    return 0 if ok else 1


def cmd_format_layout(args: argparse.Namespace) -> int:
    service = sheets_service()
    from sheet_validate import restore_summary_formulas

    restore_summary_formulas(service, args.spreadsheet_id, args.tab)
    result = apply_sheet_layout(
        service,
        args.spreadsheet_id,
        args.tab,
        max_row=args.max_row if args.max_row > 0 else None,
    )
    print(json.dumps(result, indent=2))
    print("OK: wrap text, column widths, frozen header, row auto-resize applied")
    return 0


def cmd_delete_rows(args: argparse.Namespace) -> int:
    service = sheets_service()
    rows = parse_row_spec(args.rows)
    if args.dry_run:
        preview = read_range(
            service,
            args.spreadsheet_id,
            args.tab,
            f"A{min(rows)}:B{max(rows)}",
        )
        print(json.dumps({"rows_to_delete": rows, "preview": preview}, indent=2))
        return 0

    delete_sheet_rows(service, args.spreadsheet_id, args.tab, rows)
    # Row deletion shrinks L2:M9 formula ranges — restore them.
    from sheet_validate import restore_summary_formulas

    restore_summary_formulas(service, args.spreadsheet_id, args.tab)
    apply_sheet_layout(
        service,
        args.spreadsheet_id,
        args.tab,
        max_row=args.max_row if args.max_row > 0 else None,
    )
    last = last_occupied_row(service, args.spreadsheet_id, args.tab)
    next_row = max(last + 1, 2)
    # Reset cursor watermark after compaction so max(sheet, cursor) cannot leave a gap.
    save_append_cursor(
        spreadsheet_id=args.spreadsheet_id,
        tab=args.tab,
        start_row=last if last >= 2 else 2,
        end_row=last if last >= 2 else 1,
        rows_written=0,
    )
    print(
        json.dumps(
            {
                "deleted_rows": rows,
                "deleted_count": len(rows),
                "next_append_row": next_row,
                "next_empty_row": next_row,
                "summary_formulas": "restored",
                "format_layout": "applied",
            },
            indent=2,
        )
    )
    print(f"OK: deleted {len(rows)} row(s); sheet compacted; next append row is {next_row}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Jobgru Google Sheets API writer")
    parser.add_argument("--spreadsheet-id", default=DEFAULT_SPREADSHEET_ID)
    parser.add_argument("--tab", default=DEFAULT_TAB)

    sub = parser.add_subparsers(dest="command", required=True)

    auth = sub.add_parser("auth", help="OAuth login (own client, not gcloud default)")
    auth_sub = auth.add_subparsers(dest="auth_command", required=True)

    login_p = auth_sub.add_parser("login", help="Browser login; saves scripts/.sheets-token.json")
    login_p.add_argument("--client-secrets", help="Path to OAuth desktop client JSON")
    login_p.add_argument("--token-path", default=str(DEFAULT_TOKEN_PATH))
    login_p.set_defaults(func=cmd_auth_login)

    status_p = auth_sub.add_parser("status", help="Check saved OAuth token")
    status_p.add_argument("--token-path", default=str(DEFAULT_TOKEN_PATH))
    status_p.set_defaults(func=cmd_auth_status)

    read_p = sub.add_parser("read", help="Read a range")
    read_p.add_argument("--range", required=True, help="e.g. A21:E22")
    read_p.set_defaults(func=cmd_read)

    write_p = sub.add_parser("write", help="Write to a range")
    write_p.add_argument("--range", required=True, help="e.g. A22 or A22:G22")
    write_p.add_argument("--value", help="Single cell value")
    write_p.add_argument("--json", help='2D JSON array, e.g. \'[["a","b"]]\'')
    write_p.set_defaults(func=cmd_write)

    append_p = sub.add_parser(
        "append",
        help="Append job rows after the last occupied A–C row (never mid-sheet gaps)",
    )
    append_p.add_argument("--file", required=True, help="JSON file: array of [A..H] rows")
    append_p.add_argument(
        "--start-row",
        type=int,
        help="Optional fixed start row (must be >= next safe append row unless --force-overwrite)",
    )
    append_p.add_argument(
        "--force-overwrite",
        action="store_true",
        help="Allow writing over non-empty Company/Position/Apply cells (dangerous)",
    )
    append_p.set_defaults(func=cmd_append)

    test_p = sub.add_parser("test", help="Smoke test: write, read back, optional cleanup")
    test_p.add_argument("--range", default="A22")
    test_p.add_argument("--value", default="SHEETS_API_TEST")
    test_p.add_argument("--cleanup", action="store_true", help="Clear cell after verify")
    test_p.set_defaults(func=cmd_test)

    empty_p = sub.add_parser(
        "first-empty",
        help="Print next safe append row (after last occupied A–C + last-run cursor floor)",
    )
    empty_p.add_argument("--start-row", type=int, default=2)
    empty_p.add_argument(
        "--json",
        action="store_true",
        help="Print next_append_row, last_occupied_row, and cursor as JSON",
    )
    empty_p.set_defaults(func=cmd_first_empty)

    fmt_p = sub.add_parser(
        "format-layout",
        help="Wrap text + column widths so Details/Leads/Add note/Template cells do not overflow",
    )
    fmt_p.add_argument(
        "--max-row",
        type=int,
        default=0,
        help="Apply wrap through this row (0 = full current sheet grid, no cap)",
    )
    fmt_p.set_defaults(func=cmd_format_layout)

    sum_p = sub.add_parser(
        "restore-summary",
        help="Fix Summary labels + COUNT formulas in L2:M9 (colors/borders)",
    )
    sum_p.set_defaults(func=cmd_restore_summary)

    del_p = sub.add_parser("delete-rows", help="Delete data rows and compact the sheet")
    del_p.add_argument("--rows", required=True, help="Row spec: 42 | 42,43 | 42-44 | 42,44-46")
    del_p.add_argument("--dry-run", action="store_true", help="Preview rows without deleting")
    del_p.add_argument(
        "--max-row",
        type=int,
        default=0,
        help="Apply layout through this row after delete (0 = full current sheet grid)",
    )
    del_p.set_defaults(func=cmd_delete_rows)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
