#!/usr/bin/env python3
"""Regression tests for LinkedIn job uncap, LeadGru 5-cap, and pacing skills."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
import sys

sys.path.insert(0, str(SCRIPT_DIR))

from jobgru_filters import RUN_LIMITS, catalog_text  # noqa: E402
from leadgru_leads import MAX_PEOPLE_PER_COMPANY, format_leads, validate_leads_cell  # noqa: E402


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class LimitsConstantsTests(unittest.TestCase):
    def test_linkedin_jobs_uncapped(self):
        self.assertIsNone(RUN_LIMITS["max_linkedin_per_run"])
        self.assertIsNone(RUN_LIMITS["max_jobs_per_run"])

    def test_leadgru_hard_cap(self):
        self.assertEqual(RUN_LIMITS["leadgru_max_people_per_company"], 5)
        self.assertTrue(RUN_LIMITS["leadgru_always_company_people_page"])
        self.assertEqual(MAX_PEOPLE_PER_COMPANY, 5)

    def test_filter_catalog_does_not_advertise_linkedin_25(self):
        text = catalog_text()
        self.assertNotIn("LinkedIn max 25", text)
        self.assertIn("no job-count cap", text)
        self.assertIn("5 people", text)


class LeadsCellTests(unittest.TestCase):
    def test_format_caps_at_five_and_adds_people_page(self):
        people = [(f"P{i}", "TA", f"https://www.linkedin.com/in/p{i}") for i in range(8)]
        text = format_leads(people, "https://www.linkedin.com/company/acme/")
        self.assertEqual(text.count("/in/"), 5)
        self.assertIn("/company/acme/people/", text)
        self.assertEqual(validate_leads_cell(text), [])

    def test_six_people_fail_validation(self):
        lines = [f"N — T — https://www.linkedin.com/in/u{i}/" for i in range(6)]
        lines.append("Company: https://www.linkedin.com/company/x/people/")
        errs = validate_leads_cell("\n".join(lines))
        self.assertTrue(any("too many" in e for e in errs))

    def test_missing_company_page_fails(self):
        text = "Ada — TA — https://www.linkedin.com/in/ada/"
        errs = validate_leads_cell(text)
        self.assertTrue(any("missing Company" in e for e in errs))

    def test_company_page_only_ok(self):
        text = "Company: https://www.linkedin.com/company/tiny/people/"
        self.assertEqual(validate_leads_cell(text), [])


class SkillContractTests(unittest.TestCase):
    def test_jobgru_skill_uncap_and_pacing(self):
        skill = _read(".cursor/skills/jobgru/SKILL.md")
        self.assertNotIn("max 25 accepted jobs", skill)
        self.assertNotIn("LinkedIn capped at **25", skill)
        self.assertIn("no per-run job-count cap", skill)
        self.assertIn("Sleep 40 seconds", skill)
        self.assertIn("5 people + company people page", skill)

    def test_leadgru_skill_five_cap(self):
        skill = _read(".cursor/skills/leadgru/SKILL.md")
        self.assertNotIn("4–10", skill)
        self.assertIn("At most 5", skill)
        self.assertIn("/people/", skill)
        self.assertIn("Sleep 40 seconds", skill)
        self.assertIn("Never write 6+", skill)
        self.assertIn("SendGru", skill)

    def test_sendgru_skill_contract(self):
        skill = _read(".cursor/skills/sendgru/SKILL.md")
        self.assertIn("Sent add note", skill)
        self.assertIn("2", skill)
        self.assertIn("applied", skill)
        self.assertIn("Never", skill)
        self.assertIn("300", skill)
        self.assertNotIn("hard-caps at **200**", skill)

    def test_docs_and_prompts_uncapped(self):
        for rel in (
            "README.md",
            "prompts/jobgru-run.md",
            "prompts/filter.md",
            "prompts/leadgru-run.md",
            ".cursor/skills/jobgru-setup/SKILL.md",
        ):
            text = _read(rel)
            self.assertNotIn("LinkedIn max 25", text, rel)
            self.assertNotIn("max 25/run", text, rel)


if __name__ == "__main__":
    unittest.main()
