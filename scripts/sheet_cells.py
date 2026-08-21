"""Sanitize values written into job-data cells (not summary formulas)."""

from __future__ import annotations

# Prefix that make Google Sheets treat the cell as a formula under USER_ENTERED.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_sheet_value(value: object) -> str:
    """Force scraped text to stay text. Does not touch real formulas (callers skip those)."""
    text = "" if value is None else str(value)
    if text.startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text


def sanitize_sheet_rows(rows: list[list[object]]) -> list[list[str]]:
    return [[sanitize_sheet_value(cell) for cell in row] for row in rows]
