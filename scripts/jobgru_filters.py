#!/usr/bin/env python3
"""List Jobgru job-search filter types for use in prompts."""

from __future__ import annotations

import argparse
import json
import sys

FILTER_CATALOG: list[dict] = [
    {
        "id": "count",
        "prompt_label": "Target / count",
        "description": "How many verified jobs to find this run.",
        "examples": ["3", "5", "5–10"],
        "default": "5–10",
    },
    {
        "id": "sources",
        "prompt_label": "Sources / boards",
        "description": "Job boards to search. Can limit to one or use several in parallel.",
        "examples": [
            "LinkedIn Jobs only",
            "LinkedIn Jobs, Wellfound, Indeed",
            "YC Jobs, company career pages",
        ],
        "default": "LinkedIn Jobs, Wellfound, Indeed, YC Jobs, remote boards",
    },
    {
        "id": "roles",
        "prompt_label": "Role / domain",
        "description": "Primary job titles or role families you want.",
        "examples": [
            "Software Engineer, SWE AI",
            "Backend Engineer, Full Stack Engineer",
            "AI Engineer, ML Engineer, Applied AI",
        ],
    },
    {
        "id": "role_variants",
        "prompt_label": "Acceptable role variants",
        "description": "Close title variants to include when the job description matches your domain.",
        "examples": [
            "LLM Engineer, Software Engineer AI/ML",
            "SDE, Full Stack, Backend when stack matches",
        ],
    },
    {
        "id": "location",
        "prompt_label": "Location",
        "description": "City, country, or region filter for the search.",
        "examples": ["Bangalore", "India", "US remote-eligible"],
    },
    {
        "id": "remote_restriction",
        "prompt_label": "Remote country / time-zone restriction",
        "description": "Where remote work must be allowed from.",
        "examples": ["India only", "US time zones", "any worldwide remote"],
    },
    {
        "id": "work_arrangement",
        "prompt_label": "Work arrangement",
        "description": "Onsite, hybrid, remote, or any combination.",
        "examples": ["remote", "hybrid Bangalore", "onsite Bangalore", "remote / hybrid / any"],
        "default": "any",
    },
    {
        "id": "experience",
        "prompt_label": "Experience",
        "description": "Years of experience or seniority band you want.",
        "examples": ["0–2 years", "2–5 years", "3+ years", "mid-level"],
    },
    {
        "id": "visa",
        "prompt_label": "Visa sponsorship",
        "description": "Whether visa sponsorship matters for the role.",
        "examples": ["required", "preferred", "irrelevant", "exclude"],
        "default": "irrelevant",
    },
    {
        "id": "required_skills",
        "prompt_label": "Required skills",
        "description": "Must-have skills or keywords from listings.",
        "examples": ["Python, FastAPI, PostgreSQL", "React, Node.js", "LLMs, agents, backend"],
    },
    {
        "id": "excluded_roles",
        "prompt_label": "Excluded roles / skills",
        "description": "Titles or domains to skip even if keyword overlap exists.",
        "examples": [
            "Data Scientist, Data Engineer",
            "sales, internships, data annotation",
            "5+ years senior, staff engineer",
        ],
    },
    {
        "id": "min_compensation",
        "prompt_label": "Minimum compensation",
        "description": "Pay floor if you want to filter by salary.",
        "examples": ["₹20L", "$120k", "not required"],
    },
    {
        "id": "employment_type",
        "prompt_label": "Employment type",
        "description": "Full-time, contract, internship, etc.",
        "examples": ["full-time", "contract", "internship exclude"],
    },
    {
        "id": "max_posting_age",
        "prompt_label": "Maximum posting age",
        "description": "How recent listings must be.",
        "examples": ["7 days", "2 weeks", "30 days"],
    },
    {
        "id": "exclude_staffing_agencies",
        "prompt_label": "Exclude staffing agencies",
        "description": "Skip third-party recruiters / staffing firms.",
        "examples": ["yes", "no"],
        "default": "yes",
    },
    {
        "id": "ats_scoring",
        "prompt_label": "ATS scoring",
        "description": "Run resume fit scoring after jobs are added.",
        "examples": ["yes", "no"],
        "default": "yes",
    },
    {
        "id": "note",
        "prompt_label": "Note (override)",
        "description": "Extra instructions that override default skip rules.",
        "examples": [
            "don't skip if experience matches for similar roles",
            "include if visa is not stated",
            "onsite ok in Bangalore only",
        ],
    },
]


def catalog_text() -> str:
    lines = [
        "Jobgru — available job-search filters",
        "Use these in a natural prompt or fill prompts/jobgru-run.md",
        "=" * 44,
        "",
    ]
    for idx, item in enumerate(FILTER_CATALOG, start=1):
        lines.append(f"{idx}. {item['prompt_label']}")
        lines.append(f"   {item['description']}")
        if item.get("default"):
            lines.append(f"   Default: {item['default']}")
        if item.get("examples"):
            lines.append(f"   Examples: {' | '.join(item['examples'][:3])}")
        lines.append("")
    lines.extend(
        [
            "Example prompt:",
            '  Jobgru — find 3 SWE jobs on LinkedIn in Bangalore. Include SWE AI.',
            "  Exclude Data Scientist and Data Engineer. Don't skip if exp matches.",
            "",
            "Full template: prompts/jobgru-run.md",
        ]
    )
    return "\n".join(lines)


def catalog_json() -> dict:
    return {"filters": FILTER_CATALOG, "count": len(FILTER_CATALOG)}


def cmd_list(args: argparse.Namespace) -> int:
    if args.json:
        print(json.dumps(catalog_json(), indent=2))
    else:
        print(catalog_text())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="List Jobgru filter types you can use in job-search prompts"
    )
    parser.add_argument("--json", action="store_true", help="Output JSON catalog")
    parser.set_defaults(func=cmd_list)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
