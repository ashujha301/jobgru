"""Validate Job Applications sheet layout (headers, formulas, dropdown)."""

from __future__ import annotations

import re

from sheets_write import read_range

DEFAULT_TAB = "Job Applications"

EXPECTED_HEADERS_A_J = [
    "Company Name",
    "Position",
    "Apply link",
    "Status",
    "Date Applied",
    "Details if any",
    "Leads",
    "Add note Message",
    "ATS score",
    "Suggestions on Resume",
]

SUMMARY_FORMULAS = [
    "=COUNTA(D2:D)",
    '=COUNTIF(D2:D, "Interview")',
    '=COUNTIF(D2:D, "Rejected")',
    '=COUNTIF(D2:D, "Selected")',
    '=COUNTIF(D3:D, "Assesment")',
    '=COUNTIF(D4:D, "Contacted")',
]

# Accept unbounded D2:D and legacy D2:D989 (deletes used to shrink the end row).
SUMMARY_FORMULA_PATTERNS = [
    re.compile(r"^=COUNTA\(D2:D\d*\)$"),
    re.compile(r'^=COUNTIF\(D2:D\d*,\s*"Interview"\)$'),
    re.compile(r'^=COUNTIF\(D2:D\d*,\s*"Rejected"\)$'),
    re.compile(r'^=COUNTIF\(D2:D\d*,\s*"Selected"\)$'),
    re.compile(r'^=COUNTIF\(D3:D\d*,\s*"Assesment"\)$'),
    re.compile(r'^=COUNTIF\(D4:D\d*,\s*"Contacted"\)$'),
]

STATUS_DROPDOWN_VALUES = [
    "Applied",
    "Rejected",
    "Interview",
    "Selected",
    "Assesment",
    "Contacted",
    "To Apply",
]


def sheet_has_tab(service, spreadsheet_id: str, tab: str) -> bool:
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    return any(s["properties"]["title"] == tab for s in meta.get("sheets", []))


def validate_headers(service, spreadsheet_id: str, tab: str) -> tuple[bool, list[str]]:
    issues: list[str] = []
    row = read_range(service, spreadsheet_id, tab, "A1:J1")
    if not row:
        return False, ["Row 1 headers missing"]
    got = [str(c) for c in row[0]]
    while len(got) < len(EXPECTED_HEADERS_A_J):
        got.append("")
    for i, (expected, actual) in enumerate(zip(EXPECTED_HEADERS_A_J, got, strict=True)):
        if actual != expected:
            col = chr(65 + i)
            issues.append(f"{col}1: expected {expected!r}, got {actual!r}")
    return not issues, issues


def validate_summary_formulas(service, spreadsheet_id: str, tab: str) -> tuple[bool, list[str]]:
    quoted_tab = f"'{tab}'" if " " in tab else tab
    issues: list[str] = []
    resp = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=f"{quoted_tab}!M2:M7",
            valueRenderOption="FORMULA",
        )
        .execute()
    )
    got = [row[0] if row else "" for row in resp.get("values", [])]
    while len(got) < len(SUMMARY_FORMULA_PATTERNS):
        got.append("")
    for i, (pattern, actual) in enumerate(zip(SUMMARY_FORMULA_PATTERNS, got, strict=False)):
        if not pattern.match(str(actual)):
            issues.append(
                f"M{i + 2}: expected {SUMMARY_FORMULAS[i]!r} (or legacy D2:D989), got {actual!r}"
            )
    return not issues, issues


def restore_summary_formulas(service, spreadsheet_id: str, tab: str) -> None:
    """Rewrite M2:M7 with canonical formulas (row deletes shrink the ranges)."""
    from sheets_write import write_range

    write_range(
        service,
        spreadsheet_id,
        tab,
        "M2:M7",
        [[f] for f in SUMMARY_FORMULAS],
        sanitize=False,
    )


def validate_status_dropdown(service, spreadsheet_id: str, tab: str) -> tuple[bool, list[str]]:
    quoted_tab = f"'{tab}'" if " " in tab else tab
    meta = (
        service.spreadsheets()
        .get(
            spreadsheetId=spreadsheet_id,
            ranges=[f"{quoted_tab}!D2"],
            includeGridData=True,
        )
        .execute()
    )
    try:
        cell = meta["sheets"][0]["data"][0]["rowData"][0]["values"][0]
    except (IndexError, KeyError):
        return False, ["Could not read D2 for status dropdown"]

    dv = cell.get("dataValidation", {})
    values = [
        v.get("userEnteredValue", "")
        for v in dv.get("condition", {}).get("values", [])
    ]
    if values != STATUS_DROPDOWN_VALUES:
        return False, [f"D2 dropdown mismatch: got {values!r}"]
    return True, []


def verify_template(service, spreadsheet_id: str, tab: str, *, require_empty_jobs: bool = False) -> dict:
    """Full template validation (used by init_template_sheet and jobgru_check)."""
    checks: dict = {"ok": True, "issues": []}

    if not sheet_has_tab(service, spreadsheet_id, tab):
        checks["ok"] = False
        checks["issues"].append(f'Tab not found: {tab!r}')
        return checks

    ok, issues = validate_headers(service, spreadsheet_id, tab)
    if not ok:
        checks["ok"] = False
        checks["issues"].extend(issues)

    ok, issues = validate_summary_formulas(service, spreadsheet_id, tab)
    if not ok:
        checks["ok"] = False
        checks["issues"].extend(issues)

    ok, issues = validate_status_dropdown(service, spreadsheet_id, tab)
    if not ok:
        checks["ok"] = False
        checks["issues"].extend(issues)
    else:
        checks["status_dropdown"] = STATUS_DROPDOWN_VALUES

    if require_empty_jobs:
        sample = read_range(service, spreadsheet_id, tab, "A2:J20")
        for ri, row in enumerate(sample, start=2):
            if any(str(c).strip() for c in row):
                checks["ok"] = False
                checks["issues"].append(f"Row {ri} still has job data in A:J")
                break

    return checks
