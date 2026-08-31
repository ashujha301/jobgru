#!/usr/bin/env python3
"""Create an exact Job Applications tracker template by copying the source sheet.

Copies the full spreadsheet via Drive API (preserves dropdowns, colors, column widths,
summary COUNT formulas, conditional/status formatting). Clears job data in A2:J only,
then replaces personal placeholders in O2 and Q2:Q7.

Usage (from project root, after gcloud auth):
  .venv/bin/python scripts/init_template_sheet.py
  .venv/bin/python scripts/init_template_sheet.py --write-config
  .venv/bin/python scripts/init_template_sheet.py --trash-old OLD_TEMPLATE_ID
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from googleapiclient.discovery import build

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from sheet_config import CONFIG_PATH, get_spreadsheet_id, get_tab, write_sheet_config  # noqa: E402
from jobgru_home import get_jobgru_home  # noqa: E402

PROJECT_ROOT = get_jobgru_home()
from sheet_validate import verify_template  # noqa: E402
from sheets_write import get_credentials, read_range, sheets_service, write_range  # noqa: E402

DEFAULT_TITLE = "Job Applications Tracker (Jobgru Template)"
DEFAULT_TAB = "Job Applications"
JOB_DATA_CLEAR_RANGE = "A2:J"
RESUME_PLACEHOLDER = "https://example.com/your-resume"
NAME_PLACEHOLDER = "Your Name"


def drive_service():
    return build("drive", "v3", credentials=get_credentials(), cache_discovery=False)


def copy_spreadsheet(source_id: str, *, title: str) -> tuple[str, str]:
    drive = drive_service()
    copied = drive.files().copy(fileId=source_id, body={"name": title}).execute()
    spreadsheet_id = copied["id"]
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
    return spreadsheet_id, url


def trash_spreadsheet(spreadsheet_id: str) -> None:
    drive = drive_service()
    drive.files().update(fileId=spreadsheet_id, body={"trashed": True}).execute()


def clear_job_data(service, spreadsheet_id: str, tab: str) -> None:
    quoted_tab = f"'{tab}'" if " " in tab else tab
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id,
        range=f"{quoted_tab}!{JOB_DATA_CLEAR_RANGE}",
        body={},
    ).execute()


def sanitize_personal_fields(service, spreadsheet_id: str, tab: str) -> None:
    """Replace resume link and signature name with generic placeholders."""
    write_range(service, spreadsheet_id, tab, "O2", [[RESUME_PLACEHOLDER]])

    templates = read_range(service, spreadsheet_id, tab, "Q2:Q7")
    if not templates:
        return

    cleaned: list[list[str]] = []
    for row in templates:
        text = row[0] if row else ""
        text = text.replace("Ayush Jha", NAME_PLACEHOLDER)
        text = re.sub(r"https://bit\.ly/\S+", RESUME_PLACEHOLDER, text)
        cleaned.append([text])

    write_range(service, spreadsheet_id, tab, "Q2:Q7", cleaned)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Copy production sheet into a shareable blank Jobgru template"
    )
    parser.add_argument(
        "--source-id",
        default=get_spreadsheet_id(),
        help="Source spreadsheet to clone (default: config/sheet.json)",
    )
    parser.add_argument("--title", default=DEFAULT_TITLE, help="Title for the new template file")
    parser.add_argument("--tab", default=get_tab(), help="Worksheet tab name")
    parser.add_argument(
        "--write-config",
        action="store_true",
        help="Write config/sheet.json with the new template spreadsheet ID",
    )
    parser.add_argument(
        "--trash-old",
        action="append",
        metavar="SPREADSHEET_ID",
        default=[],
        help="Move previous template spreadsheet(s) to Drive trash after creating the new one",
    )
    args = parser.parse_args()

    service = sheets_service()
    spreadsheet_id, url = copy_spreadsheet(args.source_id, title=args.title)
    clear_job_data(service, spreadsheet_id, args.tab)
    sanitize_personal_fields(service, spreadsheet_id, args.tab)
    # Ensure Summary L/M labels, formulas, colors, and borders match the canonical layout
    from sheet_validate import restore_summary_formulas

    restore_summary_formulas(service, spreadsheet_id, args.tab)
    verification = verify_template(
        service, spreadsheet_id, args.tab, require_empty_jobs=True
    )

    for old_id in args.trash_old:
        if old_id and old_id != spreadsheet_id:
            trash_spreadsheet(old_id)

    result = {
        "source_spreadsheet_id": args.source_id,
        "spreadsheet_id": spreadsheet_id,
        "sheet_url": url,
        "tab": args.tab,
        "verification": verification,
        "config_written": False,
        "trashed_old": args.trash_old or None,
    }

    if args.write_config:
        write_sheet_config(
            spreadsheet_id,
            sheet_url=url,
            tab=args.tab,
            resume_link=RESUME_PLACEHOLDER,
            your_name=NAME_PLACEHOLDER,
        )
        result["config_written"] = True
        result["config_path"] = str(CONFIG_PATH.relative_to(PROJECT_ROOT))

    print(json.dumps(result, indent=2))
    print()
    if verification.get("ok"):
        print("OK: Exact template created (dropdowns, colors, summary formulas preserved).")
    else:
        print("WARN: Template created but verification found issues — see JSON above.")
    print()
    print("Share with others:")
    print("  1. Open the sheet URL → Share → General access → Viewer")
    print("  2. Others open the link → File → Make a copy (copies ALL formatting + formulas)")
    print("  3. They chat: Jobgru setup with their copy's sheet URL")
    if not verification.get("ok"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
