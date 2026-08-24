#!/usr/bin/env python3
"""Unit tests for SendGru row selection."""

from __future__ import annotations

import unittest

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from sendgru_select import (  # noqa: E402
    MAX_NOTE_CHARS,
    SENT_MARKER,
    append_sent_marker,
    apply_daily_cap,
    evaluate_row,
    is_sent_marker,
    note_length_ok,
    parse_leads_people,
    parse_row_spec,
    select_from_sheet_rows,
    total_send_count,
)


class ParseRowSpecTests(unittest.TestCase):
    def test_range(self):
        self.assertEqual(parse_row_spec("4-12"), list(range(4, 13)))

    def test_list(self):
        self.assertEqual(parse_row_spec("4,6,9"), [4, 6, 9])

    def test_single(self):
        self.assertEqual(parse_row_spec("8"), [8])

    def test_row_prefix(self):
        self.assertEqual(parse_row_spec("row 8"), [8])


class ParseLeadsTests(unittest.TestCase):
    def test_first_two_in_urls(self):
        g = (
            "Alice — TA — https://www.linkedin.com/in/alice/\n"
            "Bob — HR — https://www.linkedin.com/in/bob/\n"
            "Carol — Eng — https://www.linkedin.com/in/carol/\n"
            "Company: https://www.linkedin.com/company/acme/people/"
        )
        people = parse_leads_people(g)
        self.assertEqual(len(people), 2)
        self.assertIn("alice", people[0].url)
        self.assertIn("bob", people[1].url)

    def test_empty(self):
        self.assertEqual(parse_leads_people(""), [])


class NoteLengthTests(unittest.TestCase):
    def test_ok(self):
        self.assertTrue(note_length_ok("Hi, short note")[0])

    def test_empty(self):
        ok, reason = note_length_ok("")
        self.assertFalse(ok)
        self.assertIn("empty", reason)

    def test_premium_300_ok(self):
        self.assertTrue(note_length_ok("x" * 300)[0])

    def test_too_long(self):
        ok, reason = note_length_ok("x" * (MAX_NOTE_CHARS + 1))
        self.assertFalse(ok)
        self.assertIn("too long", reason)


class EvaluateRowTests(unittest.TestCase):
    def _cells(self, **kw):
        base = ["Acme", "Engineer", "https://jobs/1", "applied", "1/1/2026", "", "", ""]
        idx = {"company": 0, "position": 1, "apply": 2, "status": 3, "date": 4, "details": 5, "leads": 6, "note": 7}
        for k, v in kw.items():
            base[idx[k]] = v
        return base

    def test_applied_row_ok(self):
        g = "A — T — https://www.linkedin.com/in/a/\nB — T — https://www.linkedin.com/in/b/"
        note = "Hi, please refer me. Thanks!"
        t = evaluate_row(5, self._cells(leads=g, note=note))
        self.assertEqual(t.skip_reason, "")
        self.assertEqual(len(t.people), 2)

    def test_to_apply_skipped(self):
        t = evaluate_row(5, self._cells(status="to apply", leads="X — https://www.linkedin.com/in/x/", note="Hi"))
        self.assertIn("applied", t.skip_reason)

    def test_sent_marker_skipped(self):
        t = evaluate_row(
            5,
            self._cells(status="applied", leads="X — https://www.linkedin.com/in/x/", note=SENT_MARKER),
        )
        self.assertIn("Sent add note", t.skip_reason)

    def test_appended_marker_skipped(self):
        note = f"Hi, please refer me. Thanks {SENT_MARKER}"
        t = evaluate_row(
            5,
            self._cells(status="applied", leads="X — https://www.linkedin.com/in/x/", note=note),
        )
        self.assertIn("Sent add note", t.skip_reason)

    def test_over_200_still_ok_premium(self):
        t = evaluate_row(
            5,
            self._cells(status="applied", leads="X — https://www.linkedin.com/in/x/", note="x" * 201),
        )
        self.assertEqual(t.skip_reason, "")

    def test_long_note_skipped(self):
        t = evaluate_row(
            5,
            self._cells(status="applied", leads="X — https://www.linkedin.com/in/x/", note="x" * 301),
        )
        self.assertIn("too long", t.skip_reason)


class AppendMarkerTests(unittest.TestCase):
    def test_appends_without_replacing(self):
        note = "Hi, please refer me. Thanks"
        self.assertEqual(append_sent_marker(note), f"{note} {SENT_MARKER}")

    def test_does_not_double_append(self):
        note = f"Hi, please refer me. Thanks {SENT_MARKER}"
        self.assertEqual(append_sent_marker(note), note)

    def test_legacy_exact_marker_is_sent(self):
        self.assertTrue(is_sent_marker(SENT_MARKER))
        self.assertTrue(is_sent_marker(f"Hi Thanks {SENT_MARKER}"))
        self.assertFalse(is_sent_marker("Hi, please refer me. Thanks"))


class DailyCapTests(unittest.TestCase):
    def test_caps_total_sends(self):
        rows = [
            evaluate_row(
                i,
                [
                    "Co",
                    "Role",
                    "",
                    "applied",
                    "",
                    "",
                    f"P — T — https://www.linkedin.com/in/p{i}a/\nQ — T — https://www.linkedin.com/in/p{i}b/",
                    "Hi",
                ],
            )
            for i in range(1, 6)
        ]
        kept, capped = apply_daily_cap(rows, max_sends=4)
        self.assertEqual(total_send_count(kept), 4)
        self.assertTrue(len(capped) >= 1)


class SelectIntegrationTests(unittest.TestCase):
    def test_mixed_sheet(self):
        sheet = {
            4: ["Co", "Role", "", "applied", "", "", "A — https://www.linkedin.com/in/a/", "Hi"],
            5: ["Co", "Role", "", "to apply", "", "", "A — https://www.linkedin.com/in/a/", "Hi"],
            6: ["Co", "Role", "", "applied", "", "", "A — https://www.linkedin.com/in/a/", SENT_MARKER],
        }
        actionable, skipped = select_from_sheet_rows([4, 5, 6], sheet)
        self.assertEqual(len(actionable), 1)
        self.assertEqual(actionable[0].row, 4)
        self.assertEqual(len(skipped), 2)


if __name__ == "__main__":
    unittest.main()
