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

# Column L labels + column M formulas (Summary / Count). Unbounded ranges.
SUMMARY_LABELS = [
    "Total jobs",
    "Total Applied",
    "Total to Apply",
    "Interviews",
    "Rejections",
    "Total Selected",
    "Total Assesments",
    "Total Contacted",
]

SUMMARY_FORMULAS = [
    "=COUNTA(A2:A)",
    '=COUNTIFS(A2:A,"<>",D2:D,"Applied")',
    '=COUNTIFS(A2:A,"<>",D2:D,"to apply")',
    '=COUNTIFS(A2:A,"<>",D2:D,"Interview")',
    '=COUNTIFS(A2:A,"<>",D2:D,"Rejected")',
    '=COUNTIFS(A2:A,"<>",D2:D,"Selected")',
    '=COUNTIFS(A2:A,"<>",D2:D,"Assesment")',
    '=COUNTIFS(A2:A,"<>",D2:D,"Contacted")',
]

# Accept COUNTIFS (canonical), legacy COUNTIF, and capped ranges (e.g. D2:D989).
_COUNTIFS = r'=COUNTIFS\(A2:A\d*,"<>",D2:D\d*,\s*"{status}"\)'
_COUNTIF = r'=COUNTIF\(D2:D\d*,\s*"{status}"\)'

SUMMARY_FORMULA_PATTERNS = [
    re.compile(r"^=COUNTA\(A2:A\d*\)$"),
    re.compile("^" + _COUNTIFS.format(status="Applied") + "$|" + "^" + _COUNTIF.format(status="Applied") + "$"),
    re.compile(
        "^" + _COUNTIFS.format(status="to apply") + "$|^" + _COUNTIF.format(status="to apply") + "$",
        re.IGNORECASE,
    ),
    re.compile("^" + _COUNTIFS.format(status="Interview") + "$|" + "^" + _COUNTIF.format(status="Interview") + "$"),
    re.compile("^" + _COUNTIFS.format(status="Rejected") + "$|" + "^" + _COUNTIF.format(status="Rejected") + "$"),
    re.compile("^" + _COUNTIFS.format(status="Selected") + "$|" + "^" + _COUNTIF.format(status="Selected") + "$"),
    re.compile("^" + _COUNTIFS.format(status="Assesment") + "$|" + "^" + _COUNTIF.format(status="Assesment") + "$"),
    re.compile("^" + _COUNTIFS.format(status="Contacted") + "$|" + "^" + _COUNTIF.format(status="Contacted") + "$"),
]

SUMMARY_RANGE_END = 1 + len(SUMMARY_FORMULAS)  # M2:M9 when 8 formulas

STATUS_DROPDOWN_VALUES = [
    "Applied",
    "Rejected",
    "Interview",
    "Selected",
    "Assesment",
    "Contacted",
    "to apply",
]

# Column D (0-based index 3). Template CF only covered rows 2–40 and four statuses.
STATUS_COLUMN_INDEX = 3
STATUS_CF_START_ROW = 1  # 0-based → sheet row 2
STATUS_CF_END_ROW = 5000  # exclusive → through row 4999

STATUS_CONDITIONAL_COLORS: dict[str, dict[str, float]] = {
    "Applied": {"red": 0.6784314, "green": 0.84705883, "blue": 0.9019608},
    "Rejected": {"red": 0.95686275, "green": 0.8, "blue": 0.8},
    "Interview": {"red": 1.0, "green": 1.0, "blue": 0.0},
    "Selected": {"red": 0.7176471, "green": 0.8980392, "blue": 0.6},
    "Assesment": {"red": 0.85, "green": 0.82, "blue": 0.93},
    "Contacted": {"red": 0.85, "green": 0.92, "blue": 0.95},
    "to apply": {"red": 1.0, "green": 0.9490196, "blue": 0.8},
}


def status_cf_grid_range(sheet_id: int, *, end_row: int = STATUS_CF_END_ROW) -> dict:
    return {
        "sheetId": sheet_id,
        "startRowIndex": STATUS_CF_START_ROW,
        "endRowIndex": max(end_row, STATUS_CF_START_ROW + 1),
        "startColumnIndex": STATUS_COLUMN_INDEX,
        "endColumnIndex": STATUS_COLUMN_INDEX + 1,
    }


def build_status_conditional_format_requests(sheet_id: int, *, end_row: int = STATUS_CF_END_ROW) -> list[dict]:
    """Build addConditionalFormatRule requests for every Status dropdown value."""
    grid = status_cf_grid_range(sheet_id, end_row=end_row)
    requests: list[dict] = []
    for status in STATUS_DROPDOWN_VALUES:
        requests.append(
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [grid],
                        "booleanRule": {
                            "condition": {
                                "type": "TEXT_EQ",
                                "values": [{"userEnteredValue": status}],
                            },
                            "format": {
                                "backgroundColor": STATUS_CONDITIONAL_COLORS[status],
                            },
                        },
                    },
                }
            }
        )
    return requests


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
    end = SUMMARY_RANGE_END
    resp = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=f"{quoted_tab}!L2:M{end}",
            valueRenderOption="FORMULA",
        )
        .execute()
    )
    rows = resp.get("values", [])
    while len(rows) < len(SUMMARY_FORMULA_PATTERNS):
        rows.append([])
    for i, pattern in enumerate(SUMMARY_FORMULA_PATTERNS):
        row = rows[i] if i < len(rows) else []
        label = row[0] if row else ""
        formula = row[1] if len(row) > 1 else ""
        expected_label = SUMMARY_LABELS[i]
        if str(label).strip() != expected_label:
            issues.append(f"L{i + 2}: expected {expected_label!r}, got {label!r}")
        if not pattern.match(str(formula)):
            issues.append(
                f"M{i + 2}: expected {SUMMARY_FORMULAS[i]!r} (or legacy capped range), got {formula!r}"
            )
    return not issues, issues


def restore_summary_formulas(service, spreadsheet_id: str, tab: str) -> None:
    """Rewrite L2:M{n} labels + formulas and apply Summary block colors/borders."""
    from sheets_write import write_range

    end = SUMMARY_RANGE_END
    values = [[label, formula] for label, formula in zip(SUMMARY_LABELS, SUMMARY_FORMULAS, strict=True)]
    write_range(
        service,
        spreadsheet_id,
        tab,
        f"L2:M{end}",
        values,
        sanitize=False,
    )
    # Ensure header labels exist (do not wipe custom header text if already Summary/Count)
    write_range(
        service,
        spreadsheet_id,
        tab,
        "L1:M1",
        [["Summary", "Count"]],
        sanitize=False,
    )
    apply_summary_formatting(service, spreadsheet_id, tab)
    ensure_status_formatting(service, spreadsheet_id, tab)


def ensure_status_formatting(service, spreadsheet_id: str, tab: str) -> None:
    """Status dropdown + conditional colors for all job rows (D2:D4999)."""
    restore_status_dropdown(service, spreadsheet_id, tab)
    restore_status_conditional_formatting(service, spreadsheet_id, tab)


def _delete_sheet_conditional_format_rules(service, spreadsheet_id: str, sheet_id: int) -> None:
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sheet in meta.get("sheets", []):
        if sheet["properties"]["sheetId"] != sheet_id:
            continue
        count = len(sheet.get("conditionalFormats", []))
        if not count:
            return
        requests = [
            {"deleteConditionalFormatRule": {"sheetId": sheet_id, "index": index}}
            for index in range(count - 1, -1, -1)
        ]
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests},
        ).execute()
        return


def restore_status_conditional_formatting(service, spreadsheet_id: str, tab: str) -> None:
    """Replace legacy Status CF (rows 2–40, partial statuses) with full-column rules."""
    from sheets_write import get_sheet_id, layout_end_row

    sheet_id = get_sheet_id(service, spreadsheet_id, tab)
    end_row = layout_end_row(service, spreadsheet_id, tab)
    _delete_sheet_conditional_format_rules(service, spreadsheet_id, sheet_id)
    requests = build_status_conditional_format_requests(sheet_id, end_row=end_row)
    if requests:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests},
        ).execute()


def ensure_summary_and_status(service, spreadsheet_id: str, tab: str) -> bool:
    """Restore summary formulas only when invalid; always refresh Status dropdown + colors."""
    ok, _ = validate_summary_formulas(service, spreadsheet_id, tab)
    if ok:
        ensure_status_formatting(service, spreadsheet_id, tab)
    else:
        restore_summary_formulas(service, spreadsheet_id, tab)
    return ok


def restore_status_dropdown(service, spreadsheet_id: str, tab: str) -> None:
    """Apply Status dropdown (column D) for all job rows."""
    from sheets_write import get_sheet_id

    sheet_id = get_sheet_id(service, spreadsheet_id, tab)
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "requests": [
                {
                    "setDataValidation": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": 5000,
                            "startColumnIndex": 3,
                            "endColumnIndex": 4,
                        },
                        "rule": {
                            "condition": {
                                "type": "ONE_OF_LIST",
                                "values": [
                                    {"userEnteredValue": v} for v in STATUS_DROPDOWN_VALUES
                                ],
                            },
                            "showCustomUi": True,
                            "strict": True,
                        },
                    }
                }
            ]
        },
    ).execute()


def apply_summary_formatting(service, spreadsheet_id: str, tab: str) -> None:
    """Match Summary block styling: gray header, light body, medium borders, centered."""
    from sheets_write import get_sheet_id

    sheet_id = get_sheet_id(service, spreadsheet_id, tab)
    end = SUMMARY_RANGE_END  # 1-based inclusive row (e.g. 9)

    header_bg = {"red": 0.8509804, "green": 0.8509804, "blue": 0.8509804}
    body_bg = {"red": 0.9372549, "green": 0.9372549, "blue": 0.9372549}
    header_fg = {"red": 0.2627451, "green": 0.2627451, "blue": 0.2627451}
    medium = {
        "style": "SOLID_MEDIUM",
        "width": 2,
        "color": {"red": 0, "green": 0, "blue": 0},
    }
    borders = {"top": medium, "bottom": medium, "left": medium, "right": medium}

    def grid_range(start_row: int, end_row_exclusive: int) -> dict:
        # Sheets API uses 0-based startRowIndex, exclusive endRowIndex
        return {
            "sheetId": sheet_id,
            "startRowIndex": start_row - 1,
            "endRowIndex": end_row_exclusive,
            "startColumnIndex": 11,  # L
            "endColumnIndex": 13,  # M exclusive → through M
        }

    requests = [
        {
            "repeatCell": {
                "range": grid_range(1, 1),
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": header_bg,
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                        "textFormat": {"bold": True, "foregroundColor": header_fg},
                        "borders": borders,
                    }
                },
                "fields": (
                    "userEnteredFormat.backgroundColor,"
                    "userEnteredFormat.horizontalAlignment,"
                    "userEnteredFormat.verticalAlignment,"
                    "userEnteredFormat.textFormat,"
                    "userEnteredFormat.borders"
                ),
            }
        },
        {
            "repeatCell": {
                "range": grid_range(2, end),
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": body_bg,
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                        "textFormat": {"bold": False},
                        "borders": borders,
                    }
                },
                "fields": (
                    "userEnteredFormat.backgroundColor,"
                    "userEnteredFormat.horizontalAlignment,"
                    "userEnteredFormat.verticalAlignment,"
                    "userEnteredFormat.textFormat,"
                    "userEnteredFormat.borders"
                ),
            }
        },
    ]
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests},
    ).execute()


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
