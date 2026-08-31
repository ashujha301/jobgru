#!/usr/bin/env python3
"""Verify configured Google Sheet is ready for Jobgru (installer wizard + setup)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from jobgru_home import get_jobgru_home, venv_python  # noqa: E402
from sheet_config import (  # noqa: E402
    GCLOUD_AUTH_COMMAND,
    config_is_configured,
    get_spreadsheet_id,
    get_tab,
    get_template_sheet_url,
    parse_spreadsheet_id,
)
from sheet_validate import (  # noqa: E402
    sheet_has_tab,
    validate_headers,
    validate_summary_formulas,
)

PROJECT_ROOT = get_jobgru_home()
VENV_PYTHON = venv_python(PROJECT_ROOT)


def _classify_error(exc: Exception) -> str:
    msg = str(exc).lower()
    if any(x in msg for x in ("403", "permission", "forbidden", "insufficient")):
        return "permission_denied"
    if any(x in msg for x in ("401", "unauthorized", "invalid_grant", "credentials")):
        return "auth_missing"
    if any(x in msg for x in ("404", "not found", "unable to parse range")):
        return "not_found"
    return "unknown"


def verify_sheet() -> tuple[bool, str, str]:
    """Return (ok, message, fix_hint)."""
    if not config_is_configured():
        return False, "Sheet config not saved", "Paste your copy URL during install or: jobgru setup --url YOUR_URL"

    template_id = parse_spreadsheet_id(get_template_sheet_url())
    sid = get_spreadsheet_id()
    if sid == template_id:
        return (
            False,
            "That URL is the read-only template — paste YOUR copy instead",
            "File → Make a copy in Google Sheets, then paste your copy URL",
        )

    tab = get_tab()

    try:
        from sheets_write import sheets_service

        service = sheets_service()
    except SystemExit:
        return False, "Google auth not configured", GCLOUD_AUTH_COMMAND
    except Exception as exc:
        kind = _classify_error(exc)
        if kind == "auth_missing":
            return False, "Google auth failed — sign in first", GCLOUD_AUTH_COMMAND
        if kind == "permission_denied":
            return (
                False,
                "Permission denied — your Google account needs Editor access on this sheet",
                f"Run {GCLOUD_AUTH_COMMAND} with the account that owns the sheet",
            )
        return False, str(exc), GCLOUD_AUTH_COMMAND

    try:
        if not sheet_has_tab(service, sid, tab):
            return (
                False,
                f'Tab "{tab}" not found in your sheet',
                f'Rename the tab to "{tab}" or recopy the Jobgru template',
            )

        ok, issues = validate_headers(service, sid, tab)
        if not ok:
            return (
                False,
                "Sheet headers do not match the Jobgru template: " + "; ".join(issues[:3]),
                "File → Make a copy from the Jobgru template (do not use the template URL directly)",
            )

        ok, issues = validate_summary_formulas(service, sid, tab)
        if not ok:
            return (
                False,
                "Summary formulas (L2:M9) do not match: " + "; ".join(issues[:3]),
                "Recopy the Jobgru template",
            )
    except Exception as exc:
        kind = _classify_error(exc)
        if kind == "permission_denied":
            return (
                False,
                "Cannot read sheet — permission denied (need Editor, not Viewer)",
                f"Run {GCLOUD_AUTH_COMMAND} with the Google account that owns the sheet",
            )
        if kind == "auth_missing":
            return False, "Google auth failed during sheet read", GCLOUD_AUTH_COMMAND
        return False, str(exc), GCLOUD_AUTH_COMMAND

    python = str(VENV_PYTHON if VENV_PYTHON.is_file() else sys.executable)
    try:
        subprocess.run(
            [python, str(SCRIPT_DIR / "sheets_write.py"), "test", "--cleanup"],
            check=True,
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or exc.stdout or "").strip()
        lower = err.lower()
        if any(x in lower for x in ("403", "permission", "forbidden")):
            return (
                False,
                "Sheets API write failed — permission denied",
                f"Your gcloud account must be Editor/Owner on the sheet. Run: {GCLOUD_AUTH_COMMAND}",
            )
        if any(x in lower for x in ("auth", "credential", "login", "token")):
            return False, "Sheets API write failed — auth required", GCLOUD_AUTH_COMMAND
        snippet = err[:300] if err else "Sheets API write test failed"
        return False, snippet, GCLOUD_AUTH_COMMAND

    return True, f'Sheet OK — tab "{tab}", headers, formulas, and write test passed', ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Jobgru sheet configuration")
    parser.add_argument("--json", action="store_true", help="Output JSON result")
    args = parser.parse_args()

    ok, message, fix = verify_sheet()
    if args.json:
        print(json.dumps({"ok": ok, "message": message, "fix": fix}, indent=2))
    else:
        if ok:
            print(f"OK: {message}")
        else:
            print(f"FAIL: {message}", file=sys.stderr)
            if fix:
                print(f"Fix: {fix}", file=sys.stderr)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
