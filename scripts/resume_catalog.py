#!/usr/bin/env python3
"""Resume catalog: manifest + column O (Latest Resume) + ATS winner link resolution."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from jobgru_home import get_jobgru_home  # noqa: E402

PROJECT_ROOT = get_jobgru_home()
RESUMES_DIR = PROJECT_ROOT / "data" / "resumes"
MANIFEST_PATH = RESUMES_DIR / "manifest.json"

from sheet_config import (  # noqa: E402
    get_resume_link_default,
    get_spreadsheet_id,
    get_tab,
    load_sheet_config,
    write_sheet_config,
)
from sheets_write import DEFAULT_SPREADSHEET_ID, DEFAULT_TAB, read_range, sheets_service, write_range  # noqa: E402

CATALOG_SEP = " , "
BEST_MATCH_RE = re.compile(r"Best match:\s*([^|(]+?)\s*\(\s*(\d+)\s*\)", re.IGNORECASE)
ATS_SCORE_RE = re.compile(r"([^:]+):\s*(\d+)")
URL_RE = re.compile(r"^https?://", re.IGNORECASE)

ROLE_TOKEN_MAP: list[tuple[str, str]] = [
    ("fullstack", "Full Stack"),
    ("full stack", "Full Stack"),
    ("full-stack", "Full Stack"),
    ("backend", "backend"),
    ("back end", "backend"),
    ("back-end", "backend"),
    ("machine learning", "Machine learning"),
    ("machinelearning", "Machine learning"),
    ("software engineer", "SWE"),
    ("swe", "SWE"),
    ("ai/ml", "AI"),
    ("ai ml", "AI"),
    ("ai", "AI"),
    ("ml", "Machine learning"),
    ("be", "backend"),
    ("se", "SWE"),
    ("fs", "Full Stack"),
]


@dataclass
class CatalogEntry:
    left: str  # share_url or filename
    role: str
    share_url: str = ""
    display_name: str = ""

    def to_sheet_line(self) -> str:
        left = self.share_url or self.display_name or self.left
        return f"{left}{CATALOG_SEP}{self.role}"

    @property
    def note_link(self) -> str:
        if self.share_url:
            return self.share_url
        return self.display_name or self.left


def read_manifest_data() -> dict:
    if not MANIFEST_PATH.is_file():
        return {"resumes": []}
    return json.loads(MANIFEST_PATH.read_text())


def write_manifest_data(data: dict) -> None:
    RESUMES_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(data, indent=2) + "\n")


def filename_to_id(stem: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return slug or "resume"


def filename_to_label(stem: str) -> str:
    label = re.sub(r"[_-]+", " ", stem).strip()
    return label.title() if label else "Resume"


def infer_role_from_filename(stem: str) -> str:
    normalized = re.sub(r"[_-]+", " ", stem.lower())
    for token, role in ROLE_TOKEN_MAP:
        if token in normalized:
            return role
    return filename_to_label(stem)


def normalize_label(label: str) -> str:
    return re.sub(r"\s+", " ", label.strip().lower())


def parse_catalog_line(line: str) -> CatalogEntry | None:
    text = (line or "").strip()
    if not text:
        return None
    if CATALOG_SEP in text:
        left, role = text.split(CATALOG_SEP, 1)
    elif "," in text:
        left, role = text.split(",", 1)
    else:
        return None
    left = left.strip()
    role = role.strip()
    if not left or not role:
        return None
    share_url = left if URL_RE.match(left) else ""
    display_name = left if not share_url else Path(left).name if left.endswith(".pdf") else left
    return CatalogEntry(left=left, role=role, share_url=share_url, display_name=display_name)


def manifest_entry_to_catalog(item: dict) -> CatalogEntry:
    share_url = (item.get("share_url") or "").strip()
    filename = item.get("file", "")
    label = item.get("label") or filename_to_label(Path(filename).stem if filename else "Resume")
    if share_url:
        left = share_url
    elif filename:
        left = filename
    else:
        left = label
    return CatalogEntry(
        left=left,
        role=label,
        share_url=share_url,
        display_name=filename or label,
    )


def load_manifest_catalog() -> list[CatalogEntry]:
    data = read_manifest_data()
    return [manifest_entry_to_catalog(item) for item in data.get("resumes", [])]


def upsert_manifest_entry(
    *,
    file: str | None = None,
    label: str,
    share_url: str = "",
    resume_id: str | None = None,
) -> dict:
    data = read_manifest_data()
    resumes: list[dict] = list(data.get("resumes", []))
    rid = resume_id or filename_to_id(Path(file).stem if file else label)
    entry = {
        "id": rid,
        "file": file or "",
        "label": label,
    }
    if share_url:
        entry["share_url"] = share_url
    updated = False
    for idx, item in enumerate(resumes):
        if item.get("id") == rid or (file and item.get("file") == file):
            merged = dict(item)
            merged.update(entry)
            if not share_url and item.get("share_url"):
                merged["share_url"] = item["share_url"]
            if not file and item.get("file"):
                merged["file"] = item["file"]
            resumes[idx] = merged
            updated = True
            entry = merged
            break
    if not updated:
        resumes.append(entry)
    data["resumes"] = resumes
    write_manifest_data(data)
    return entry


def read_sheet_catalog(service, spreadsheet_id: str, tab: str) -> list[CatalogEntry]:
    values = read_range(service, spreadsheet_id, tab, "O2:O50")
    entries: list[CatalogEntry] = []
    for row in values:
        cell = row[0] if row else ""
        parsed = parse_catalog_line(cell)
        if parsed:
            entries.append(parsed)
    return entries


def catalog_to_sheet_values(entries: list[CatalogEntry]) -> list[list[str]]:
    if not entries:
        return [[""]]
    return [[e.to_sheet_line()] for e in entries]


def sync_sheet_catalog(
    service,
    spreadsheet_id: str,
    tab: str,
    entries: list[CatalogEntry] | None = None,
) -> dict:
    entries = entries if entries is not None else load_manifest_catalog()
    values = catalog_to_sheet_values(entries)
    end_row = 1 + len(values)
    write_range(service, spreadsheet_id, tab, f"O2:O{end_row}", values)
    if end_row < 50:
        clear_end = min(end_row + 10, 50)
        blanks = [[""] for _ in range(clear_end - end_row)]
        if blanks:
            write_range(service, spreadsheet_id, tab, f"O{end_row + 1}:O{clear_end}", blanks)

    first_url = next((e.share_url for e in entries if e.share_url), "")
    if first_url:
        cfg = load_sheet_config()
        write_sheet_config(
            get_spreadsheet_id(),
            resume_link=first_url,
            your_name=cfg.get("your_name"),
        )
    return {
        "rows_written": len(entries),
        "catalog": [e.to_sheet_line() for e in entries],
    }


def parse_best_match_from_j(suggestions: str) -> tuple[str, int] | None:
    match = BEST_MATCH_RE.search(suggestions or "")
    if not match:
        return None
    return match.group(1).strip(), int(match.group(2))


def parse_best_from_i(ats_cell: str) -> tuple[str, int] | None:
    scores: list[tuple[str, int]] = []
    for match in ATS_SCORE_RE.finditer(ats_cell or ""):
        label = match.group(1).strip()
        if label.lower().startswith("no skills"):
            continue
        scores.append((label, int(match.group(2))))
    if not scores:
        return None
    return max(scores, key=lambda x: x[1])


def find_catalog_entry(entries: list[CatalogEntry], label: str) -> CatalogEntry | None:
    target = normalize_label(label)
    for entry in entries:
        if normalize_label(entry.role) == target:
            return entry
    for entry in entries:
        if target in normalize_label(entry.role) or normalize_label(entry.role) in target:
            return entry
    return None


def resolve_link_for_row(
    *,
    row_num: int,
    ats_cell: str = "",
    suggestions_cell: str = "",
    catalog: list[CatalogEntry] | None = None,
    default_link: str | None = None,
) -> dict:
    catalog = catalog if catalog is not None else load_manifest_catalog()
    default_link = default_link if default_link is not None else get_resume_link_default()

    best = parse_best_match_from_j(suggestions_cell) or parse_best_from_i(ats_cell)
    winner_label = best[0] if best else ""

    matched = find_catalog_entry(catalog, winner_label) if winner_label else None
    if matched:
        link = matched.note_link
        source = "catalog_match"
    elif len(catalog) == 1:
        link = catalog[0].note_link
        source = "single_catalog"
    else:
        link = default_link
        source = "default"

    return {
        "row": row_num,
        "best_label": winner_label,
        "best_score": best[1] if best else None,
        "link": link,
        "source": source,
    }


def download_pdf_from_url(url: str, dest: Path) -> bool:
    req = urllib.request.Request(url, headers={"User-Agent": "Jobgru/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            content_type = (resp.headers.get("Content-Type") or "").lower()
            data = resp.read()
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False

    if not data.startswith(b"%PDF") and "pdf" not in content_type:
        return False

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return True


def google_drive_download_url(url: str) -> str | None:
    match = re.search(r"drive\.google\.com/file/d/([a-zA-Z0-9_-]+)", url)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    match = re.search(r"drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)", url)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return None


def resolve_download_url(url: str) -> str:
    drive = google_drive_download_url(url)
    return drive or url


def write_text_pdf(path: Path, text: str) -> None:
    """Write a minimal PDF with extractable text (for tests / smoke bootstrap)."""
    safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({safe}) Tj ET"
    body = (
        f"%PDF-1.4\n"
        f"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        f"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        f"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        f"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        f"4 0 obj << /Length {len(stream)} >> stream\n{stream}\nendstream endobj\n"
        f"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        f"xref\n0 6\n0000000000 65535 f \n"
        f"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n0\n%%EOF\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body.encode("latin-1"))


ROLE_PDF_KEYWORDS: dict[str, str] = {
    "AI": "Python LLM RAG agentic AI engineer FastAPI machine learning",
    "backend": "Python FastAPI PostgreSQL backend engineer REST API LLM",
    "SWE": "software engineer Python JavaScript full stack web development",
    "Machine learning": "machine learning PyTorch scikit-learn NLP deep learning Python",
    "Full Stack": "full stack React Node Python frontend backend engineer",
}


def cmd_import_sheet(args: argparse.Namespace) -> int:
    service = sheets_service()
    entries = read_sheet_catalog(service, args.spreadsheet_id, args.tab)
    imported: list[dict] = []
    for entry in entries:
        item = upsert_manifest_entry(
            file="",
            label=entry.role,
            share_url=entry.share_url,
        )
        imported.append(item)
    if not args.dry_run:
        sync_sheet_catalog(service, args.spreadsheet_id, args.tab, entries)
    print(json.dumps({"imported": imported, "count": len(imported)}, indent=2))
    return 0


def cmd_bootstrap_pdfs(args: argparse.Namespace) -> int:
    """Create keyword PDFs for manifest entries missing files (smoke / local test)."""
    data = read_manifest_data()
    created: list[str] = []
    for item in data.get("resumes", []):
        label = item.get("label", "Resume")
        filename = item.get("file") or f"{filename_to_id(label)}.pdf"
        path = RESUMES_DIR / filename
        if path.is_file() and not args.force:
            continue
        keywords = ROLE_PDF_KEYWORDS.get(label, f"{label} Python engineer software development")
        write_text_pdf(path, keywords)
        upsert_manifest_entry(file=filename, label=label, share_url=item.get("share_url", ""))
        created.append(filename)
    from ats_score import sync_manifest_from_pdfs  # noqa: WPS433

    sync_manifest_from_pdfs(write=True)
    print(json.dumps({"created": created}, indent=2))
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    label = args.label or infer_role_from_filename(Path(args.pdf).stem if args.pdf else args.url)
    share_url = (args.url or "").strip()
    saved_file = ""

    if args.pdf:
        src = Path(args.pdf)
        if not src.is_file():
            print(json.dumps({"error": f"PDF not found: {args.pdf}"}, indent=2))
            return 1
        RESUMES_DIR.mkdir(parents=True, exist_ok=True)
        dest = RESUMES_DIR / src.name
        shutil.copy2(src, dest)
        saved_file = dest.name
        entry = upsert_manifest_entry(file=saved_file, label=label, share_url=share_url)
    elif share_url:
        download_name = f"{filename_to_id(label)}.pdf"
        dest = RESUMES_DIR / download_name
        final_url = resolve_download_url(share_url)
        downloaded = download_pdf_from_url(final_url, dest)
        if downloaded:
            saved_file = download_name
            entry = upsert_manifest_entry(file=saved_file, label=label, share_url=share_url)
        else:
            entry = upsert_manifest_entry(file="", label=label, share_url=share_url)
    else:
        print(json.dumps({"error": "Provide --pdf and/or --url"}, indent=2))
        return 1

    catalog = load_manifest_catalog()
    if not args.dry_run:
        service = sheets_service()
        sync_result = sync_sheet_catalog(service, args.spreadsheet_id, args.tab, catalog)
    else:
        sync_result = {"rows_written": len(catalog), "catalog": [e.to_sheet_line() for e in catalog]}

    from ats_score import sync_manifest_from_pdfs  # noqa: WPS433

    sync_manifest_from_pdfs(write=True)

    result = {
        "status": "ok",
        "entry": entry,
        "saved_file": saved_file,
        "downloaded": bool(saved_file and not args.pdf),
        "sheet": sync_result,
        "dry_run": args.dry_run,
    }
    print(json.dumps(result, indent=2))
    return 0


def cmd_sync_sheet(args: argparse.Namespace) -> int:
    catalog = load_manifest_catalog()
    if args.dry_run:
        print(json.dumps({"catalog": [e.to_sheet_line() for e in catalog]}, indent=2))
        return 0
    service = sheets_service()
    result = sync_sheet_catalog(service, args.spreadsheet_id, args.tab, catalog)
    print(json.dumps(result, indent=2))
    return 0


def cmd_resolve(args: argparse.Namespace) -> int:
    service = sheets_service()
    row_num = args.row
    values = read_range(service, args.spreadsheet_id, args.tab, f"I{row_num}:J{row_num}")
    ats_cell = values[0][0] if values and values[0] else ""
    sug_cell = values[0][1] if values and len(values[0]) > 1 else ""
    sheet_catalog = read_sheet_catalog(service, args.spreadsheet_id, args.tab)
    manifest_catalog = load_manifest_catalog()
    catalog = sheet_catalog or manifest_catalog
    result = resolve_link_for_row(
        row_num=row_num,
        ats_cell=ats_cell,
        suggestions_cell=sug_cell,
        catalog=catalog,
    )
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["link"])
    return 0


def cmd_fill_notes(args: argparse.Namespace) -> int:
    from leadgru_notes import DEFAULT_TEMPLATES, fill_add_note  # noqa: WPS433

    service = sheets_service()
    if "-" in args.rows:
        start, end = args.rows.split("-", 1)
        row_numbers = list(range(int(start), int(end) + 1))
    else:
        row_numbers = [int(x.strip()) for x in args.rows.split(",") if x.strip()]

    templates = read_range(service, args.spreadsheet_id, args.tab, "Q2:Q7")
    template_texts = [row[0] if row else DEFAULT_TEMPLATES[i] for i, row in enumerate(templates)]
    while len(template_texts) < 6:
        template_texts.append(DEFAULT_TEMPLATES[len(template_texts)])

    sheet_catalog = read_sheet_catalog(service, args.spreadsheet_id, args.tab)
    manifest_catalog = load_manifest_catalog()
    catalog = sheet_catalog or manifest_catalog

    filled: list[dict] = []
    skipped: list[dict] = []

    for idx, row_num in enumerate(row_numbers):
        row = read_range(service, args.spreadsheet_id, args.tab, f"A{row_num}:J{row_num}")
        if not row:
            continue
        cells = row[0]
        while len(cells) < 10:
            cells.append("")
        company = cells[0]
        position = cells[1]
        existing_h = cells[7].strip()
        if existing_h and not args.force:
            skipped.append({"row": row_num, "reason": "H already filled"})
            continue

        resolved = resolve_link_for_row(
            row_num=row_num,
            ats_cell=cells[8],
            suggestions_cell=cells[9],
            catalog=catalog,
        )
        template = template_texts[idx % len(template_texts)]
        note = fill_add_note(
            template,
            position=position,
            company=company,
            link=resolved["link"],
        )
        if not args.dry_run:
            write_range(
                service,
                args.spreadsheet_id,
                args.tab,
                f"H{row_num}",
                [[note]],
            )
        filled.append({"row": row_num, "link": resolved["link"], "best_label": resolved["best_label"], "note": note})

    summary = {"filled": filled, "skipped": skipped, "dry_run": args.dry_run}
    print(json.dumps(summary, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resume catalog for column O and add-note link resolution")
    parser.add_argument("--spreadsheet-id", default=DEFAULT_SPREADSHEET_ID)
    parser.add_argument("--tab", default=DEFAULT_TAB)
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser("add", help="Add PDF and/or share URL to manifest + sync column O")
    add_p.add_argument("--pdf", help="Path to resume PDF")
    add_p.add_argument("--url", help="Public short link (Bitly, etc.)")
    add_p.add_argument("--label", help="Role label for catalog matching")
    add_p.add_argument("--dry-run", action="store_true")
    add_p.set_defaults(func=cmd_add)

    sync_p = sub.add_parser("sync-sheet", help="Rewrite column O from manifest catalog")
    sync_p.add_argument("--dry-run", action="store_true")
    sync_p.set_defaults(func=cmd_sync_sheet)

    import_p = sub.add_parser("import-sheet", help="Import column O catalog into manifest.json")
    import_p.add_argument("--dry-run", action="store_true")
    import_p.set_defaults(func=cmd_import_sheet)

    bootstrap_p = sub.add_parser("bootstrap-pdfs", help="Create keyword PDFs for manifest entries (local test)")
    bootstrap_p.add_argument("--force", action="store_true")
    bootstrap_p.set_defaults(func=cmd_bootstrap_pdfs)

    resolve_p = sub.add_parser("resolve", help="Resolve add-note link for a sheet row")
    resolve_p.add_argument("--row", type=int, required=True)
    resolve_p.add_argument("--json", action="store_true")
    resolve_p.set_defaults(func=cmd_resolve)

    fill_p = sub.add_parser("fill-notes", help="Fill column H using ATS winner link")
    fill_p.add_argument("--rows", required=True, help="Row numbers: 42 or 42-44 or 42,43")
    fill_p.add_argument("--force", action="store_true", help="Overwrite existing H")
    fill_p.add_argument("--dry-run", action="store_true")
    fill_p.set_defaults(func=cmd_fill_notes)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
