#!/usr/bin/env python3
"""Save and show Jobgru job-search filters."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from jobgru_home import get_jobgru_home  # noqa: E402

PROJECT_ROOT = get_jobgru_home()
FILTERS_PATH = PROJECT_ROOT / "config" / "filters.json"
EXAMPLE_PATH = PROJECT_ROOT / "config" / "filters.json.example"

DEFAULT_FILTERS = {
    "count": 5,
    "sources": ["LinkedIn Jobs", "Wellfound", "Indeed"],
    "roles": [],
    "location": "",
    "remote_restriction": "",
    "work_arrangement": "any",
    "experience": "",
    "visa": "irrelevant",
    "required_skills": [],
    "excluded_roles": [],
    "min_compensation": "",
    "employment_type": "",
    "max_posting_age": "",
    "exclude_staffing_agencies": "yes",
    "ats_scoring": "yes",
    "note": "",
}


def load_filters() -> dict:
    if FILTERS_PATH.is_file():
        data = json.loads(FILTERS_PATH.read_text())
        merged = {**DEFAULT_FILTERS, **data}
        return merged
    return dict(DEFAULT_FILTERS)


def save_filters(data: dict) -> None:
    FILTERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    FILTERS_PATH.write_text(json.dumps(data, indent=2) + "\n")


def _split_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def build_search_prompt(filters: dict) -> str:
    roles = ", ".join(filters.get("roles") or []) or "(fill in)"
    excluded = ", ".join(filters.get("excluded_roles") or []) or "(none)"
    sources = ", ".join(filters.get("sources") or []) or "LinkedIn Jobs"
    skills = ", ".join(filters.get("required_skills") or []) or "(none)"
    note_line = f"\nNote: {filters['note']}" if filters.get("note") else ""

    return f"""Jobgru — find {filters.get('count', 5)} verified jobs (full pipeline: Jobgru + LeadGru + ATSScore).

Sources: {sources}
Roles: {roles}
Location: {filters.get('location') or '(fill in)'}
Remote / time zone: {filters.get('remote_restriction') or 'any'}
Work arrangement: {filters.get('work_arrangement') or 'any'}
Experience: {filters.get('experience') or '(fill in)'}
Visa sponsorship: {filters.get('visa') or 'irrelevant'}
Required skills: {skills}
Excluded roles: {excluded}
Minimum compensation: {filters.get('min_compensation') or '(none)'}
Employment type: {filters.get('employment_type') or 'any'}
Max posting age: {filters.get('max_posting_age') or '(none)'}
Exclude staffing agencies: {filters.get('exclude_staffing_agencies') or 'yes'}
ATS scoring: {filters.get('ats_scoring') or 'yes'}{note_line}"""


def print_filters(filters: dict) -> None:
    print("Saved Jobgru filters")
    print("=" * 40)
    for key, value in filters.items():
        if isinstance(value, list):
            display = ", ".join(value) if value else "(empty)"
        else:
            display = value if value not in ("", None) else "(empty)"
        print(f"  {key}: {display}")
    print(f"\nFile: {FILTERS_PATH}")


def cmd_show(_args: argparse.Namespace) -> int:
    if not FILTERS_PATH.is_file():
        print(f"No saved filters at {FILTERS_PATH}")
        if EXAMPLE_PATH.is_file():
            print(f"Copy and edit: {EXAMPLE_PATH}")
        return 1
    print_filters(load_filters())
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    filters = load_filters()
    if args.count is not None:
        filters["count"] = args.count
    if args.sources is not None:
        filters["sources"] = _split_list(args.sources)
    if args.roles is not None:
        filters["roles"] = _split_list(args.roles)
    if args.location is not None:
        filters["location"] = args.location
    if args.remote is not None:
        filters["remote_restriction"] = args.remote
    if args.work is not None:
        filters["work_arrangement"] = args.work
    if args.experience is not None:
        filters["experience"] = args.experience
    if args.visa is not None:
        filters["visa"] = args.visa
    if args.skills is not None:
        filters["required_skills"] = _split_list(args.skills)
    if args.exclude_roles is not None:
        filters["excluded_roles"] = _split_list(args.exclude_roles)
    if args.min_comp is not None:
        filters["min_compensation"] = args.min_comp
    if args.employment is not None:
        filters["employment_type"] = args.employment
    if args.max_age is not None:
        filters["max_posting_age"] = args.max_age
    if args.exclude_agencies is not None:
        filters["exclude_staffing_agencies"] = args.exclude_agencies
    if args.ats is not None:
        filters["ats_scoring"] = args.ats
    if args.note is not None:
        filters["note"] = args.note
    save_filters(filters)
    print_filters(filters)
    return 0


def cmd_prompt(args: argparse.Namespace) -> int:
    filters = load_filters() if FILTERS_PATH.is_file() else dict(DEFAULT_FILTERS)
    print(build_search_prompt(filters))
    return 0


def cmd_init(_args: argparse.Namespace) -> int:
    if FILTERS_PATH.is_file():
        print(f"Filters already exist: {FILTERS_PATH}")
        return 0
    save_filters(dict(DEFAULT_FILTERS))
    print(f"Created {FILTERS_PATH}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Jobgru saved job-search filters")
    sub = parser.add_subparsers(dest="command", required=True)

    show_p = sub.add_parser("show", help="Show saved filters")
    show_p.set_defaults(func=cmd_show)

    init_p = sub.add_parser("init", help="Create default filters.json")
    init_p.set_defaults(func=cmd_init)

    set_p = sub.add_parser("set", help="Update saved filters")
    set_p.add_argument("--count", type=int)
    set_p.add_argument("--sources")
    set_p.add_argument("--roles")
    set_p.add_argument("--location")
    set_p.add_argument("--remote")
    set_p.add_argument("--work")
    set_p.add_argument("--experience")
    set_p.add_argument("--visa")
    set_p.add_argument("--skills")
    set_p.add_argument("--exclude-roles")
    set_p.add_argument("--min-comp")
    set_p.add_argument("--employment")
    set_p.add_argument("--max-age")
    set_p.add_argument("--exclude-agencies")
    set_p.add_argument("--ats")
    set_p.add_argument("--note")
    set_p.set_defaults(func=cmd_set)

    prompt_p = sub.add_parser("prompt", help="Print a ready-to-paste job search prompt")
    prompt_p.set_defaults(func=cmd_prompt)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
