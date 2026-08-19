#!/usr/bin/env python3
"""Shared Google Sheet configuration for Jobgru scripts and skills."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from jobgru_home import get_jobgru_home  # noqa: E402

_HOME = get_jobgru_home()
PROJECT_ROOT = _HOME
CONFIG_PATH = PROJECT_ROOT / "config" / "sheet.json"
EXAMPLE_PATH = PROJECT_ROOT / "config" / "sheet.json.example"

_BUILTIN_DEFAULT_SPREADSHEET_ID = "1xQ2M_XDxQvx7ZdpWqYLkWvMVpGehBJEFIkQqEcvFPEY"
_BUILTIN_DEFAULT_TAB = "Job Applications"
_PLACEHOLDER_IDS = {"PASTE_YOUR_SPREADSHEET_ID_HERE", ""}

SHEET_URL_RE = re.compile(
    r"(?:https?://)?(?:docs\.)?google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)"
)

GCLOUD_AUTH_COMMAND = "gcloud auth login --enable-gdrive-access --update-adc"
DEFAULT_JOBGRU_REPO = os.environ.get(
    "JOBGRU_REPO", "https://github.com/ashujha301/jobgru.git"
)


def load_sheet_config() -> dict:
    """Load user config; fall back to example file if sheet.json missing."""
    for path in (CONFIG_PATH, EXAMPLE_PATH):
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    return {}


def get_template_sheet_url() -> str:
    cfg = load_sheet_config()
    url = cfg.get("template_sheet_url")
    if url:
        return url
    if EXAMPLE_PATH.is_file():
        example = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
        return example.get(
            "template_sheet_url",
            "https://docs.google.com/spreadsheets/d/18TQRl1dh0Ivdk8YbxkdiWb6__XkpHM32T1ohPTuMJ_4/edit",
        )
    return "https://docs.google.com/spreadsheets/d/18TQRl1dh0Ivdk8YbxkdiWb6__XkpHM32T1ohPTuMJ_4/edit"


def parse_spreadsheet_id(value: str) -> str:
    """Extract spreadsheet ID from a URL or raw ID string."""
    value = value.strip()
    match = SHEET_URL_RE.search(value)
    if match:
        return match.group(1)
    if re.fullmatch(r"[a-zA-Z0-9-_]+", value):
        return value
    raise ValueError(f"Could not parse spreadsheet ID from: {value!r}")


def sheet_url_from_id(spreadsheet_id: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"


def get_spreadsheet_id() -> str:
    return (
        os.environ.get("JOBGRU_SPREADSHEET_ID")
        or os.environ.get("JOBGRU_SPREADSHEET_ID")  # legacy
        or load_sheet_config().get("spreadsheet_id")
        or _BUILTIN_DEFAULT_SPREADSHEET_ID
    )


def get_tab() -> str:
    return (
        os.environ.get("JOBGRU_SHEET_TAB")
        or os.environ.get("JOBGRU_SHEET_TAB")  # legacy
        or load_sheet_config().get("tab")
        or _BUILTIN_DEFAULT_TAB
    )


def get_sheet_url() -> str:
    cfg = load_sheet_config()
    url = cfg.get("sheet_url")
    if url and "PASTE_YOUR" not in url:
        return url
    sid = get_spreadsheet_id()
    if sid in _PLACEHOLDER_IDS:
        return sheet_url_from_id(_BUILTIN_DEFAULT_SPREADSHEET_ID)
    return sheet_url_from_id(sid)


def get_resume_link_default() -> str:
    return load_sheet_config().get("resume_link") or "https://example.com/your-resume"


def get_your_name() -> str:
    return load_sheet_config().get("your_name") or "Your Name"


def config_is_configured() -> bool:
    if not CONFIG_PATH.is_file():
        return False
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    sid = cfg.get("spreadsheet_id", "")
    return bool(sid) and sid not in _PLACEHOLDER_IDS


def write_sheet_config(
    spreadsheet_id: str,
    *,
    sheet_url: str | None = None,
    tab: str = _BUILTIN_DEFAULT_TAB,
    resume_link: str | None = None,
    your_name: str | None = None,
) -> Path:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = load_sheet_config() if CONFIG_PATH.is_file() else {}
    cfg = {
        "spreadsheet_id": spreadsheet_id,
        "tab": tab,
        "sheet_url": sheet_url or sheet_url_from_id(spreadsheet_id),
        "template_sheet_url": get_template_sheet_url(),
        "resume_link": resume_link or existing.get("resume_link") or "https://example.com/your-resume",
        "your_name": your_name or existing.get("your_name") or "Your Name",
    }
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    return CONFIG_PATH


def get_config_path_for_docs() -> str:
    if CONFIG_PATH.is_file():
        return "config/sheet.json"
    return "config/sheet.json.example (copy to config/sheet.json)"


def cmd_set(args: argparse.Namespace) -> int:
    sid = parse_spreadsheet_id(args.url or args.id or "")
    path = write_sheet_config(
        sid,
        sheet_url=args.url if args.url and "google.com" in args.url else None,
        tab=args.tab,
        resume_link=args.resume_link,
        your_name=args.name,
    )
    print(json.dumps({"config_path": str(path.relative_to(PROJECT_ROOT)), "spreadsheet_id": sid}, indent=2))
    return 0


def cmd_show(_args: argparse.Namespace) -> int:
    print(json.dumps(load_sheet_config(), indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Jobgru sheet configuration")
    sub = parser.add_subparsers(dest="command", required=True)

    set_p = sub.add_parser("set", help="Write config/sheet.json from sheet URL or ID")
    set_p.add_argument("--url", help="Full Google Sheet URL")
    set_p.add_argument("--id", help="Spreadsheet ID (alternative to --url)")
    set_p.add_argument("--tab", default=_BUILTIN_DEFAULT_TAB)
    set_p.add_argument("--name", help="Your name (for outreach templates)")
    set_p.add_argument("--resume-link", help="Public resume URL for column O2")
    set_p.set_defaults(func=cmd_set)

    show_p = sub.add_parser("show", help="Print current config")
    show_p.set_defaults(func=cmd_show)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
