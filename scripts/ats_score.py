#!/usr/bin/env python3
"""ATS scoring for Job Applications sheet — deterministic, no LLM.

Reads job title + Skills from Details (column F), compares against local resume PDFs,
writes ATS score (I) and Suggestions on Resume (J).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

# Import shared Sheets helpers from sibling module
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from jobgru_home import get_jobgru_home  # noqa: E402

PROJECT_ROOT = get_jobgru_home()
RESUMES_DIR = PROJECT_ROOT / "data" / "resumes"
MANIFEST_PATH = RESUMES_DIR / "manifest.json"

from sheets_write import (  # noqa: E402
    DEFAULT_SPREADSHEET_ID,
    DEFAULT_TAB,
    parse_row_spec,
    read_range,
    sheets_service,
    write_range,
)
NO_SKILLS_MSG = "No skills data — add Skills to Details and rescore"

# Column indices (0-based) for A:J rows
COL_COMPANY = 0
COL_POSITION = 1
COL_STATUS = 3
COL_DETAILS = 5
COL_ATS = 8
COL_SUGGESTIONS = 9


@dataclass
class ResumeEntry:
    id: str
    label: str
    path: Path
    text: str = ""


@dataclass
class JobRow:
    row_num: int
    company: str
    position: str
    status: str
    details: str
    ats_existing: str
    skills: list[str] = field(default_factory=list)
    exp_text: str = ""
    arrangement: str = ""


@dataclass
class ScoreResult:
    label: str
    score: int
    matched_skills: list[str]
    missing_skills: list[str]
    title_fit: str
    exp_match: str


def filename_to_id(stem: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return slug or "resume"


def filename_to_label(stem: str) -> str:
    label = re.sub(r"[_-]+", " ", stem).strip()
    return label.title() if label else "Resume"


def read_manifest_data() -> dict:
    if not MANIFEST_PATH.is_file():
        return {"resumes": []}
    return json.loads(MANIFEST_PATH.read_text())


def sync_manifest_from_pdfs(*, write: bool = True) -> tuple[list[dict], bool]:
    """Discover PDFs in data/resumes/ and merge into manifest (auto id/label from filename).

    Existing manifest entries are kept when the PDF still exists (preserves custom labels).
    Returns (manifest resume dicts, changed).
    """
    data = read_manifest_data()
    by_file: dict[str, dict] = {
        item["file"]: item
        for item in data.get("resumes", [])
        if item.get("file")
    }

    pdfs = sorted(RESUMES_DIR.glob("*.pdf"))
    merged: list[dict] = []
    changed = False

    for pdf_path in pdfs:
        filename = pdf_path.name
        if filename in by_file:
            entry = dict(by_file[filename])
            entry.setdefault("id", filename_to_id(pdf_path.stem))
            entry.setdefault("label", filename_to_label(pdf_path.stem))
        else:
            entry = {
                "id": filename_to_id(pdf_path.stem),
                "file": filename,
                "label": filename_to_label(pdf_path.stem),
            }
            changed = True
        merged.append(entry)

    if set(by_file) - {e["file"] for e in merged}:
        changed = True

    if merged != data.get("resumes", []):
        changed = True

    if write and changed:
        MANIFEST_PATH.write_text(json.dumps({"resumes": merged}, indent=2) + "\n")

    return merged, changed


def load_resumes(resume_ids: list[str] | None = None, *, sync_manifest: bool = True) -> list[ResumeEntry]:
    """Load resumes: auto-sync manifest from any PDFs in data/resumes/, then read entries."""
    if sync_manifest:
        manifest_items, _ = sync_manifest_from_pdfs(write=True)
    else:
        manifest_items, _ = sync_manifest_from_pdfs(write=False)

    if not manifest_items:
        return []

    entries: list[ResumeEntry] = []
    for item in manifest_items:
        rid = item.get("id", "")
        if resume_ids and rid not in resume_ids:
            continue
        pdf_path = RESUMES_DIR / item.get("file", "")
        if not pdf_path.is_file():
            continue
        entries.append(
            ResumeEntry(
                id=rid,
                label=item.get("label", rid),
                path=pdf_path,
            )
        )
    return entries


def extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n".join(parts)


def load_resume_texts(entries: list[ResumeEntry]) -> list[ResumeEntry]:
    for entry in entries:
        entry.text = extract_pdf_text(entry.path).lower()
    return entries


def parse_skills(details: str) -> list[str]:
    if not details:
        return []
    match = re.search(r"\|\s*Skills:\s*(.+?)(?:\s*\|\s*|$)", details, re.IGNORECASE)
    if not match:
        match = re.search(r"Skills:\s*(.+?)$", details, re.IGNORECASE)
    if not match:
        return []
    raw = match.group(1).strip()
    skills = [s.strip() for s in re.split(r",|;", raw) if s.strip()]
    return skills[:20]


def parse_exp(details: str) -> str:
    match = re.search(r"Exp:\s*([^,|]+)", details, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def parse_arrangement(details: str) -> str:
    for word in ("Remote", "Hybrid", "Onsite"):
        if re.search(rf"\b{word}\b", details, re.IGNORECASE):
            return word
    return ""


def normalize_tokens(text: str) -> set[str]:
    text = text.lower()
    tokens = re.findall(r"[a-z0-9+#.]+", text)
    return {t for t in tokens if len(t) > 1}


def skill_in_resume(skill: str, resume_text: str) -> bool:
    skill_lower = skill.lower().strip()
    if not skill_lower:
        return False
    if skill_lower in resume_text:
        return True
    # Multi-word: all significant words present
    words = [w for w in re.findall(r"[a-z0-9+#.]+", skill_lower) if len(w) > 2]
    if len(words) >= 2:
        return all(w in resume_text for w in words)
    return False


def title_overlap_score(title: str, resume_text: str) -> tuple[int, str]:
    title_tokens = normalize_tokens(title)
    title_tokens -= {"engineer", "developer", "software", "the", "and", "for", "at", "a", "an"}
    if not title_tokens:
        return 50, "moderate"
    head = resume_text[:1500]
    head_tokens = normalize_tokens(head)
    overlap = title_tokens & head_tokens
    ratio = len(overlap) / len(title_tokens)
    if ratio >= 0.6:
        return 100, "strong"
    if ratio >= 0.3:
        return 65, "moderate"
    return 30, "weak"


def exp_match_score(exp_text: str, resume_text: str) -> tuple[int, str]:
    if not exp_text or exp_text.lower() == "not stated":
        return 50, "unknown"
    # Look for year patterns in resume
    years = re.findall(r"(\d+)\+?\s*(?:years?|yrs?)", resume_text)
    resume_years = max((int(y) for y in years), default=0)
    # Parse job exp band
    range_match = re.search(r"(\d+)\s*[-–]\s*(\d+)", exp_text)
    plus_match = re.search(r"(\d+)\+", exp_text)
    if range_match:
        lo, hi = int(range_match.group(1)), int(range_match.group(2))
        if lo <= resume_years <= hi + 1:
            return 100, "matches"
        if abs(resume_years - lo) <= 1 or abs(resume_years - hi) <= 1:
            return 70, "close"
        return 30, "mismatch"
    if plus_match:
        min_y = int(plus_match.group(1))
        if resume_years >= min_y:
            return 100, "matches"
        if resume_years >= min_y - 1:
            return 70, "close"
        return 30, "mismatch"
    single = re.search(r"(\d+)", exp_text)
    if single:
        target = int(single.group(1))
        if abs(resume_years - target) <= 1:
            return 100, "matches"
        return 50, "unknown"
    return 50, "unknown"


def score_resume(job: JobRow, resume: ResumeEntry) -> ScoreResult:
    skills = job.skills
    matched = [s for s in skills if skill_in_resume(s, resume.text)]
    missing = [s for s in skills if s not in matched]

    skill_pct = (len(matched) / len(skills) * 100) if skills else 0
    title_pts, title_fit = title_overlap_score(job.position, resume.text)
    exp_pts, exp_match = exp_match_score(job.exp_text, resume.text)

    # Weighted total
    total = int(skill_pct * 0.60 + title_pts * 0.20 + exp_pts * 0.20)
    total = max(0, min(100, total))

    return ScoreResult(
        label=resume.label,
        score=total,
        matched_skills=matched,
        missing_skills=missing[:5],
        title_fit=title_fit,
        exp_match=exp_match,
    )


def format_ats_cell(results: list[ScoreResult]) -> str:
    sorted_results = sorted(results, key=lambda r: r.score, reverse=True)
    return ", ".join(f"{r.label}: {r.score}" for r in sorted_results)


def format_suggestions(best: ScoreResult) -> str:
    parts = [f"Best match: {best.label} ({best.score})"]
    if best.missing_skills:
        parts.append(f"Add keywords: {', '.join(best.missing_skills)}")
    parts.append(f"Title fit: {best.title_fit}")
    parts.append(f"Exp: {best.exp_match}")
    return " | ".join(parts)


def pad_row(row: list[str], length: int = 10) -> list[str]:
    while len(row) < length:
        row.append("")
    return row


def read_job_rows(service, spreadsheet_id: str, tab: str) -> list[JobRow]:
    values = read_range(service, spreadsheet_id, tab, "A2:J500")
    jobs: list[JobRow] = []
    for idx, raw in enumerate(values):
        row = pad_row(list(raw))
        row_num = idx + 2
        jobs.append(
            JobRow(
                row_num=row_num,
                company=row[COL_COMPANY].strip(),
                position=row[COL_POSITION].strip(),
                status=row[COL_STATUS].strip().lower(),
                details=row[COL_DETAILS].strip(),
                ats_existing=row[COL_ATS].strip(),
                skills=parse_skills(row[COL_DETAILS]),
                exp_text=parse_exp(row[COL_DETAILS]),
                arrangement=parse_arrangement(row[COL_DETAILS]),
            )
        )
    return jobs


def eligible_rows(
    jobs: list[JobRow],
    *,
    row_numbers: set[int] | None = None,
    row_range: tuple[int, int] | None = None,
    all_to_apply: bool = False,
    force: bool = False,
    rescore: bool = False,
) -> list[JobRow]:
    eligible: list[JobRow] = []
    for job in jobs:
        if not job.company and not job.position:
            continue
        if row_numbers is not None:
            if job.row_num not in row_numbers:
                continue
        elif job.status != "to apply":
            continue
        if job.ats_existing and not force:
            continue
        if rescore or row_numbers is not None:
            eligible.append(job)
        elif all_to_apply or row_range is None:
            eligible.append(job)
        elif row_range[0] <= job.row_num <= row_range[1]:
            eligible.append(job)
    return eligible


def parse_row_range(spec: str) -> tuple[int, int]:
    if "-" in spec:
        start, end = spec.split("-", 1)
        return int(start.strip()), int(end.strip())
    row = int(spec.strip())
    return row, row


def cmd_sync(args: argparse.Namespace) -> int:
    items, changed = sync_manifest_from_pdfs(write=not args.dry_run)
    summary = {
        "sync_status": "updated" if changed else "unchanged",
        "resume_count": len(items),
        "resumes": items,
        "dry_run": args.dry_run,
    }
    print(json.dumps(summary, indent=2))
    return 0


def cmd_rescore(args: argparse.Namespace) -> int:
    args.force = True
    args.all = False
    args.row_numbers = set(parse_row_spec(args.rows))
    return cmd_score(args)


def cmd_score(args: argparse.Namespace) -> int:
    resumes = load_resumes(args.resumes.split(",") if args.resumes else None)
    if not resumes:
        summary = {
            "atsscore_status": "skipped",
            "reason": "no PDF resumes in data/resumes/",
            "atsscore_rows_scored": [],
            "atsscore_skipped_no_data": [],
            "resumes_used": [],
        }
        print(json.dumps(summary, indent=2))
        return 0

    resumes = load_resume_texts(resumes)
    service = sheets_service()
    jobs = read_job_rows(service, args.spreadsheet_id, args.tab)

    row_numbers = getattr(args, "row_numbers", None)
    row_range = parse_row_range(args.rows) if args.rows and row_numbers is None else None
    rescore = getattr(args, "command", "") == "rescore"
    targets = eligible_rows(
        jobs,
        row_numbers=row_numbers,
        row_range=row_range,
        all_to_apply=args.all,
        force=args.force,
        rescore=rescore,
    )

    scored_rows: list[int] = []
    no_data_rows: list[int] = []
    writes: list[tuple[int, str, str]] = []

    for job in targets:
        if not job.skills:
            no_data_rows.append(job.row_num)
            writes.append((job.row_num, NO_SKILLS_MSG, ""))
            continue

        results = [score_resume(job, r) for r in resumes]
        best = max(results, key=lambda r: r.score)
        ats_cell = format_ats_cell(results)
        sug_cell = format_suggestions(best)
        scored_rows.append(job.row_num)
        writes.append((job.row_num, ats_cell, sug_cell))

    if not args.dry_run:
        for row_num, ats_val, sug_val in writes:
            write_range(
                service,
                args.spreadsheet_id,
                args.tab,
                f"I{row_num}:J{row_num}",
                [[ats_val, sug_val]],
            )

    summary = {
        "atsscore_status": "complete" if writes else "skipped",
        "atsscore_rows_scored": scored_rows,
        "atsscore_skipped_no_data": no_data_rows,
        "resumes_used": [r.label for r in resumes],
        "dry_run": args.dry_run,
    }
    print(json.dumps(summary, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ATS scoring for Job Applications sheet")
    parser.add_argument("--spreadsheet-id", default=DEFAULT_SPREADSHEET_ID)
    parser.add_argument("--tab", default=DEFAULT_TAB)

    sub = parser.add_subparsers(dest="command", required=True)

    score_p = sub.add_parser("score", help="Score eligible to-apply rows")
    score_p.add_argument("--rows", help="Row range e.g. 27-31 (also backfills other empty to-apply rows when used with --all)")
    score_p.add_argument(
        "--all",
        action="store_true",
        help="Include all to-apply rows with empty ATS score (backfill)",
    )
    score_p.add_argument(
        "--force",
        action="store_true",
        help="Re-score even when column I already has a value",
    )
    score_p.add_argument("--resumes", help="Comma-separated resume ids from manifest (default: all)")
    score_p.add_argument("--dry-run", action="store_true", help="Print summary without writing sheet")
    score_p.set_defaults(func=cmd_score)

    sync_p = sub.add_parser("sync", help="Refresh manifest.json from PDFs in data/resumes/")
    sync_p.add_argument("--dry-run", action="store_true", help="Show changes without writing manifest")
    sync_p.set_defaults(func=cmd_sync)

    rescore_p = sub.add_parser(
        "rescore",
        help="Re-score specific rows only (overwrites column I/J)",
    )
    rescore_p.add_argument(
        "--rows",
        required=True,
        help="Row numbers: 42 | 42,43 | 42-44 | 42,44-46",
    )
    rescore_p.add_argument("--resumes", help="Comma-separated resume ids from manifest (default: all)")
    rescore_p.add_argument("--dry-run", action="store_true", help="Print summary without writing sheet")
    rescore_p.set_defaults(func=cmd_rescore)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
