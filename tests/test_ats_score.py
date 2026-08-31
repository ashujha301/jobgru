#!/usr/bin/env python3
"""Unit tests for ATS manifest sync and best-match selection."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from ats_score import (  # noqa: E402
    ResumeEntry,
    format_ats_cell,
    format_suggestions,
    score_resume,
    sync_manifest_from_pdfs,
    JobRow,
)


class SyncManifestTests(unittest.TestCase):
    def test_preserves_share_url_on_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            resumes_dir = Path(tmp)
            manifest = resumes_dir / "manifest.json"
            pdf_path = resumes_dir / "backend.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 minimal\n")

            manifest.write_text(
                json.dumps(
                    {
                        "resumes": [
                            {
                                "id": "backend",
                                "file": "backend.pdf",
                                "label": "backend",
                                "share_url": "https://bit.ly/aj_be",
                            }
                        ]
                    }
                )
            )

            with patch("ats_score.RESUMES_DIR", resumes_dir), patch(
                "ats_score.MANIFEST_PATH", manifest
            ):
                items, _ = sync_manifest_from_pdfs(write=True)
                self.assertEqual(len(items), 1)
                self.assertEqual(items[0]["share_url"], "https://bit.ly/aj_be")
                self.assertEqual(items[0]["label"], "backend")


class BestMatchTests(unittest.TestCase):
    def test_format_ats_cell_sorted(self):
        from dataclasses import dataclass

        @dataclass
        class R:
            label: str
            score: int

        cell = format_ats_cell([R("SWE", 71), R("backend", 86)])
        self.assertTrue(cell.index("backend: 86") < cell.index("SWE: 71"))

    def test_best_is_max_score(self):
        job = JobRow(
            row_num=2,
            company="Acme",
            position="Backend AI Engineer",
            status="to apply",
            details="Pay: x, Exp: 2 years, Visa: n, Remote, India, Posted: 1d | Skills: Python, FastAPI, LLM",
            ats_existing="",
            skills=["Python", "FastAPI", "LLM"],
            exp_text="2 years",
        )
        backend = ResumeEntry(
            id="backend",
            label="backend",
            path=Path("x.pdf"),
            text="python fastapi backend engineer llm 3 years experience",
        )
        ai = ResumeEntry(
            id="ai",
            label="AI",
            path=Path("y.pdf"),
            text="machine learning research",
        )
        results = [score_resume(job, backend), score_resume(job, ai)]
        best = max(results, key=lambda r: r.score)
        self.assertEqual(best.label, "backend")
        sug = format_suggestions(best)
        self.assertIn("Best match: backend", sug)


if __name__ == "__main__":
    unittest.main()
