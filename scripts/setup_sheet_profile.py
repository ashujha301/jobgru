#!/usr/bin/env python3
"""Apply user profile (resume catalog + name) to sheet cells O2:O{n} and Q2:Q7."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from resume_catalog import load_manifest_catalog, sync_sheet_catalog  # noqa: E402
from sheets_write import read_range, sheets_service, write_range  # noqa: E402


def apply_user_profile(
    service,
    spreadsheet_id: str,
    tab: str,
    *,
    resume_link: str,
    your_name: str,
) -> None:
    catalog = load_manifest_catalog()
    if catalog:
        sync_sheet_catalog(service, spreadsheet_id, tab, catalog)
    else:
        write_range(service, spreadsheet_id, tab, "O2", [[resume_link]])

    templates = read_range(service, spreadsheet_id, tab, "Q2:Q7")
    if not templates:
        return

    updated: list[list[str]] = []
    for row in templates:
        text = row[0] if row else ""
        if "Your Name" in text:
            text = text.replace("Your Name", your_name)
        updated.append([text])

    write_range(service, spreadsheet_id, tab, "Q2:Q7", updated)
