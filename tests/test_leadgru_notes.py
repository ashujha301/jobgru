#!/usr/bin/env python3
"""Unit tests for LeadGru add-note fill (≤ 200 chars)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from leadgru_notes import (  # noqa: E402
    DEFAULT_TEMPLATES,
    MAX_FILLED_NOTE_CHARS,
    clamp_note,
    fill_add_note,
)


class FillNoteTests(unittest.TestCase):
    def test_hi_no_name_or_bang(self):
        note = fill_add_note(
            DEFAULT_TEMPLATES[0],
            position="AI Engineer",
            company="Acme",
            link="https://bit.ly/ajha",
        )
        self.assertTrue(note.startswith("Hi,"))
        self.assertNotIn("{Name}", note)
        self.assertNotIn("{Position}", note)
        self.assertNotIn("Ayush", note)
        self.assertNotIn("!", note)
        self.assertTrue(note.endswith("Thanks"))
        self.assertIn("https://bit.ly/ajha", note)
        self.assertLessEqual(len(note), MAX_FILLED_NOTE_CHARS)

    def test_long_title_stays_under_cap(self):
        note = fill_add_note(
            DEFAULT_TEMPLATES[2],
            position="Founding Agentic AI Engineer - Boock.ai (Remote India)",
            company="Businessonbot (Y Combinator W21)",
            link="https://bit.ly/ajha",
        )
        self.assertLessEqual(len(note), MAX_FILLED_NOTE_CHARS)
        self.assertIn("https://bit.ly/ajha", note)
        self.assertTrue(note.endswith("Thanks"))
        self.assertNotIn("Ayush", note)

    def test_extreme_titles_are_clamped(self):
        note = fill_add_note(
            DEFAULT_TEMPLATES[3],
            position="Senior Staff Founding Principal AI Engineer " * 4,
            company="Very Long Company Name With Many Words Incorporated " * 3,
            link="https://bit.ly/ajha",
        )
        self.assertLessEqual(len(note), MAX_FILLED_NOTE_CHARS)
        self.assertIn("https://bit.ly/ajha", note)
        self.assertTrue(note.endswith("Thanks"))

    def test_all_default_templates_short_job(self):
        for tpl in DEFAULT_TEMPLATES:
            with self.subTest(tpl=tpl[:40]):
                note = fill_add_note(
                    tpl,
                    position="SWE",
                    company="Cisco",
                    link="https://bit.ly/ajha",
                )
                self.assertLessEqual(len(note), MAX_FILLED_NOTE_CHARS)
                self.assertGreater(len(note), 40)
                self.assertNotIn("!", note)
                self.assertTrue(note.endswith("Thanks"))


class ClampTests(unittest.TestCase):
    def test_passthrough(self):
        self.assertEqual(clamp_note("Hi, short"), "Hi, short")

    def test_keeps_link_and_thanks(self):
        long = (
            "Hi, " + ("please refer me for this long role " * 8)
            + "https://bit.ly/ajha Thanks"
        )
        out = clamp_note(long, 200)
        self.assertLessEqual(len(out), 200)
        self.assertIn("https://bit.ly/ajha", out)
        self.assertTrue(out.endswith("Thanks"))


if __name__ == "__main__":
    unittest.main()
