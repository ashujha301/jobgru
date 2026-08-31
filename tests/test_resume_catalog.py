#!/usr/bin/env python3
"""Unit tests for resume catalog parsing and ATS winner link resolution."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from resume_catalog import (  # noqa: E402
    CatalogEntry,
    find_catalog_entry,
    infer_role_from_filename,
    load_manifest_catalog,
    manifest_entry_to_catalog,
    parse_best_from_i,
    parse_best_match_from_j,
    parse_catalog_line,
    resolve_link_for_row,
    upsert_manifest_entry,
)


class ParseCatalogTests(unittest.TestCase):
    def test_parse_bitly_line(self):
        entry = parse_catalog_line("https://bit.ly/aj_be , backend")
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.share_url, "https://bit.ly/aj_be")
        self.assertEqual(entry.role, "backend")
        self.assertEqual(entry.note_link, "https://bit.ly/aj_be")

    def test_parse_pdf_only_line(self):
        entry = parse_catalog_line("Ayush_SWE.pdf , SWE")
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.share_url, "")
        self.assertEqual(entry.note_link, "Ayush_SWE.pdf")

    def test_infer_role_backend(self):
        self.assertEqual(infer_role_from_filename("Ayush_BE_Resume"), "backend")

    def test_parse_best_from_j(self):
        best = parse_best_match_from_j("Best match: backend (86) | Add keywords: K8s")
        self.assertEqual(best, ("backend", 86))

    def test_parse_best_from_i(self):
        best = parse_best_from_i("backend: 86, SWE: 71, AI: 54")
        self.assertEqual(best, ("backend", 86))


class ResolveLinkTests(unittest.TestCase):
    def setUp(self):
        self.catalog = [
            CatalogEntry(left="https://bit.ly/aj_be", role="backend", share_url="https://bit.ly/aj_be"),
            CatalogEntry(left="https://bit.ly/aj_ai", role="AI", share_url="https://bit.ly/aj_ai"),
        ]

    def test_resolve_by_best_match_label(self):
        result = resolve_link_for_row(
            row_num=22,
            ats_cell="backend: 86, AI: 54",
            suggestions_cell="Best match: backend (86) | Title fit: strong",
            catalog=self.catalog,
            default_link="https://bit.ly/default",
        )
        self.assertEqual(result["link"], "https://bit.ly/aj_be")
        self.assertEqual(result["source"], "catalog_match")

    def test_single_catalog_fallback(self):
        single = [CatalogEntry(left="https://bit.ly/aj_se", role="SWE", share_url="https://bit.ly/aj_se")]
        result = resolve_link_for_row(
            row_num=22,
            ats_cell="",
            suggestions_cell="",
            catalog=single,
            default_link="https://bit.ly/default",
        )
        self.assertEqual(result["link"], "https://bit.ly/aj_se")
        self.assertEqual(result["source"], "single_catalog")

    def test_default_when_no_match(self):
        result = resolve_link_for_row(
            row_num=22,
            ats_cell="Unknown: 50",
            suggestions_cell="Best match: Unknown (50)",
            catalog=self.catalog,
            default_link="https://bit.ly/default",
        )
        self.assertEqual(result["link"], "https://bit.ly/default")
        self.assertEqual(result["source"], "default")

    def test_find_catalog_case_insensitive(self):
        entry = find_catalog_entry(self.catalog, "Backend")
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.share_url, "https://bit.ly/aj_be")


class ManifestTests(unittest.TestCase):
    def test_manifest_entry_to_catalog(self):
        item = {
            "id": "backend",
            "file": "Ayush_BE.pdf",
            "label": "backend",
            "share_url": "https://bit.ly/aj_be",
        }
        entry = manifest_entry_to_catalog(item)
        self.assertEqual(entry.to_sheet_line(), "https://bit.ly/aj_be , backend")

    def test_upsert_preserves_share_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            resumes_dir = Path(tmp) / "data" / "resumes"
            resumes_dir.mkdir(parents=True)
            manifest = resumes_dir / "manifest.json"
            with patch("resume_catalog.RESUMES_DIR", resumes_dir), patch(
                "resume_catalog.MANIFEST_PATH", manifest
            ):
                upsert_manifest_entry(
                    file="Ayush_BE.pdf",
                    label="backend",
                    share_url="https://bit.ly/aj_be",
                )
                upsert_manifest_entry(file="Ayush_BE.pdf", label="backend")
                data = json.loads(manifest.read_text())
                self.assertEqual(data["resumes"][0]["share_url"], "https://bit.ly/aj_be")
                catalog = load_manifest_catalog()
                self.assertEqual(catalog[0].share_url, "https://bit.ly/aj_be")


if __name__ == "__main__":
    unittest.main()
