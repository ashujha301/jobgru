#!/usr/bin/env python3
"""Unit tests for sheet uncap, formula sanitization, and LinkedIn verify."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from jobgru_linkedin_login import linkedin_logged_in, verify_linkedin_session  # noqa: E402
from sheet_cells import sanitize_sheet_rows, sanitize_sheet_value  # noqa: E402
from sheet_validate import SUMMARY_FORMULA_PATTERNS, SUMMARY_FORMULAS  # noqa: E402


class SanitizeTests(unittest.TestCase):
    def test_formula_prefixed_values_are_forced_text(self):
        self.assertEqual(sanitize_sheet_value('=HYPERLINK("http://x")'), "'=HYPERLINK(\"http://x\")")
        self.assertEqual(sanitize_sheet_value("+1-555"), "'+1-555")
        self.assertEqual(sanitize_sheet_value("-1"), "'-1")
        self.assertEqual(sanitize_sheet_value("@SUM(1)"), "'@SUM(1)")
        self.assertEqual(sanitize_sheet_value("\t=1"), "'\t=1")

    def test_normal_job_fields_unchanged(self):
        self.assertEqual(sanitize_sheet_value("Acme Inc"), "Acme Inc")
        self.assertEqual(sanitize_sheet_value("https://jobs.example/1"), "https://jobs.example/1")
        self.assertEqual(sanitize_sheet_value(""), "")

    def test_sanitize_rows(self):
        rows = [["Acme", "=1+1"]]
        out = sanitize_sheet_rows(rows)
        self.assertEqual(out[0][0], "Acme")
        self.assertEqual(out[0][1], "'=1+1")


class FormulaPatternTests(unittest.TestCase):
    def test_unbounded_canonical_formulas_match(self):
        for formula, pattern in zip(SUMMARY_FORMULAS, SUMMARY_FORMULA_PATTERNS, strict=True):
            self.assertTrue(pattern.match(formula), formula)

    def test_legacy_d989_still_valid(self):
        self.assertTrue(SUMMARY_FORMULA_PATTERNS[0].match("=COUNTA(D2:D989)"))
        self.assertTrue(SUMMARY_FORMULA_PATTERNS[1].match('=COUNTIF(D2:D989, "Interview")'))

    def test_rows_past_500_are_in_unbounded_formula(self):
        self.assertIn("D2:D)", SUMMARY_FORMULAS[0])
        self.assertNotIn("500", SUMMARY_FORMULAS[0])
        self.assertNotIn("989", SUMMARY_FORMULAS[0])


class LinkedInVerifyTests(unittest.TestCase):
    def test_missing_cookie_is_logged_out(self):
        class Ctx:
            def cookies(self):
                return []

        self.assertFalse(linkedin_logged_in(Ctx()))

    def test_navigation_error_does_not_count_as_logged_in(self):
        class Ctx:
            pages = []

            def cookies(self):
                return [{"name": "li_at", "value": "stale"}]

            def new_page(self):
                raise RuntimeError("browser closed")

        self.assertTrue(linkedin_logged_in(Ctx()))
        self.assertFalse(verify_linkedin_session(Ctx()))


class FilterLimitsTests(unittest.TestCase):
    def test_no_per_run_job_cap(self):
        from jobgru_filters import RUN_LIMITS

        self.assertIsNone(RUN_LIMITS["max_jobs_per_run"])
        self.assertIsNone(RUN_LIMITS["sheet_row_cap"])
        self.assertIsNone(RUN_LIMITS["max_linkedin_per_run"])
        self.assertEqual(RUN_LIMITS["leadgru_max_people_per_company"], 5)


class LastDataRowTests(unittest.TestCase):
    def test_open_ended_column_a_includes_row_555(self):
        from sheets_write import last_data_row, layout_end_row

        class Fake:
            def __init__(self, n):
                self.n = n

            def spreadsheets(self):
                return self

            def values(self):
                return self

            def get(self, **_kwargs):
                return self

            def execute(self):
                if "ranges" in getattr(self, "_last", {}):
                    pass
                return {"values": [["Co"]] * self.n}

        # 554 data rows starting at A2 → last row 555
        svc = Fake(554)
        self.assertEqual(last_data_row(svc, "id", "Job Applications"), 555)

        class FakeMeta(Fake):
            def get(self, **kwargs):
                self._kwargs = kwargs
                return self

            def execute(self):
                if "spreadsheetId" in self._kwargs and "range" not in self._kwargs:
                    return {
                        "sheets": [
                            {
                                "properties": {
                                    "title": "Job Applications",
                                    "sheetId": 0,
                                    "gridProperties": {"rowCount": 1000},
                                }
                            }
                        ]
                    }
                return {"values": [["Co"]] * self.n}

        self.assertEqual(layout_end_row(FakeMeta(554), "id", "Job Applications"), 1000)


class AppendSafetyTests(unittest.TestCase):
    def test_blank_company_mid_sheet_does_not_become_append_point(self):
        from sheets_write import last_occupied_row_from_values

        # Rows 2-21 filled, row 22 blank company + title, rows 23-27 filled.
        values = [["Co", "Role", "https://x"]] * 20
        values.append(["", "AI Engineer", "https://gap.example"])
        values.extend([["LaterCo", "SWE", "https://y"]] * 5)
        last = last_occupied_row_from_values(values, start_row=2, columns=3)
        self.assertEqual(last, 27)  # last LaterCo
        self.assertEqual(last + 1, 28)

        # Old first-blank-in-A behavior would have returned row 22:
        first_blank_a = None
        for idx, row in enumerate(values):
            if not row or not str(row[0]).strip():
                first_blank_a = 2 + idx
                break
        self.assertEqual(first_blank_a, 22)
        self.assertGreater(last + 1, first_blank_a)

    def test_cursor_roundtrip(self):
        import tempfile
        from pathlib import Path
        import sheets_write as sw

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sheet-append-cursor.json"
            original = sw.append_cursor_path
            sw.append_cursor_path = lambda: path
            try:
                sw.save_append_cursor(
                    spreadsheet_id="sheet123",
                    tab="Job Applications",
                    start_row=79,
                    end_row=134,
                    rows_written=56,
                )
                loaded = sw.load_append_cursor("sheet123")
                self.assertEqual(loaded["next_row"], 135)
                self.assertIsNone(sw.load_append_cursor("other"))
            finally:
                sw.append_cursor_path = original


if __name__ == "__main__":
    unittest.main()
