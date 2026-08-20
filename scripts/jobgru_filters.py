#!/usr/bin/env python3
"""List Jobgru job-search filter types for use in prompts."""

from __future__ import annotations

import argparse
import json
import sys

RUN_LIMITS = {
    "max_jobs_per_run": 50,
    "max_linkedin_per_run": 25,
    "linkedin_researchers": 1,
}

FILTER_CATALOG: list[dict] = [
    {
        "id": "count",
        "name": "Target / count",
        "say": "Say how many jobs you want this run.",
        "examples": ["find 3 jobs", "find 10 jobs", "find up to 30 jobs"],
        "limits": "Max 50 jobs per run (hard cap).",
    },
    {
        "id": "sources",
        "name": "Job boards / sources",
        "say": "Say which board(s) to search — one, several, or a mix.",
        "examples": [
            "LinkedIn only",
            "LinkedIn and Wellfound",
            "mix: LinkedIn + Indeed + YC Jobs",
        ],
        "modes": [
            "Single — one board only (e.g. LinkedIn only)",
            "Multiple — same search across several boards in parallel",
            "Mix & match — pick any combination you name in the prompt",
        ],
        "limits": "LinkedIn max 25 jobs per run (rate-limit safety). Other boards share the remaining quota up to 50 total.",
    },
    {
        "id": "roles",
        "name": "Role / domain",
        "say": "Say the job titles or role families you want.",
        "examples": [
            "Software Engineer, SWE AI",
            "Backend Engineer, Full Stack Engineer",
        ],
    },
    {
        "id": "role_variants",
        "name": "Acceptable role variants",
        "say": "Say similar titles to include when the description still matches.",
        "examples": [
            "include LLM Engineer, Software Engineer AI/ML",
            "include SDE / Full Stack when stack matches",
        ],
    },
    {
        "id": "location",
        "name": "Location",
        "say": "Say city, country, or region.",
        "examples": ["Bangalore", "India", "US remote-eligible"],
    },
    {
        "id": "remote_restriction",
        "name": "Remote country / time zone",
        "say": "Say where remote work must be allowed from.",
        "examples": ["India only", "US time zones", "any worldwide remote"],
    },
    {
        "id": "work_arrangement",
        "name": "Work arrangement",
        "say": "Say remote, hybrid, onsite, or any.",
        "examples": ["remote only", "hybrid Bangalore", "onsite or hybrid"],
    },
    {
        "id": "experience",
        "name": "Experience",
        "say": "Say years of experience or seniority you want.",
        "examples": ["0–2 years", "2–5 years", "3+ years", "mid-level"],
    },
    {
        "id": "visa",
        "name": "Visa sponsorship",
        "say": "Say if visa sponsorship matters.",
        "examples": ["visa required", "visa irrelevant", "no visa needed"],
    },
    {
        "id": "required_skills",
        "name": "Required skills",
        "say": "Say must-have skills or keywords.",
        "examples": ["Python, FastAPI, PostgreSQL", "React, Node.js", "LLMs, agents"],
    },
    {
        "id": "excluded_roles",
        "name": "Excluded roles",
        "say": "Say titles or domains to skip.",
        "examples": [
            "exclude Data Scientist, Data Engineer",
            "exclude sales and internships",
            "exclude 5+ years senior roles",
        ],
    },
    {
        "id": "min_compensation",
        "name": "Minimum compensation",
        "say": "Say a pay floor, or skip if not needed.",
        "examples": ["minimum ₹20L", "minimum $120k", "not required"],
    },
    {
        "id": "employment_type",
        "name": "Employment type",
        "say": "Say full-time, contract, etc.",
        "examples": ["full-time only", "no internships", "contract ok"],
    },
    {
        "id": "max_posting_age",
        "name": "Maximum posting age",
        "say": "Say how recent listings must be.",
        "examples": ["posted in last 7 days", "last 2 weeks", "last 30 days"],
    },
    {
        "id": "exclude_staffing_agencies",
        "name": "Exclude staffing agencies",
        "say": "Say yes to skip recruiters/staffing firms.",
        "examples": ["exclude staffing agencies", "staffing agencies ok"],
    },
    {
        "id": "ats_scoring",
        "name": "ATS scoring",
        "say": "Say yes to score your resume after jobs are added.",
        "examples": ["run ATS scoring", "skip ATS scoring"],
    },
    {
        "id": "note",
        "name": "Note (extra instructions)",
        "say": "Say anything else in plain English — overrides default skip rules.",
        "examples": [
            "don't skip if experience matches for similar roles",
            "include if visa is not stated",
            "onsite ok in Bangalore only",
        ],
    },
]


def catalog_text() -> str:
    lines = [
        "Jobgru — filters you can use in a job-search prompt",
        "",
        "Write in plain English — pick any filters below and say what you want.",
        "You do not need every filter; only mention what matters to you.",
        "",
        "Run limits:",
        f"  • Max {RUN_LIMITS['max_jobs_per_run']} jobs per run (total across all boards)",
        f"  • Max {RUN_LIMITS['max_linkedin_per_run']} jobs from LinkedIn per run (rate-limit safety)",
        f"  • One LinkedIn researcher per run",
        "",
        "=" * 44,
        "",
    ]
    for idx, item in enumerate(FILTER_CATALOG, start=1):
        lines.append(f"{idx}. {item['name']}")
        lines.append(f"   {item['say']}")
        if item.get("modes"):
            lines.append("   Boards — pick one style:")
            for mode in item["modes"]:
                lines.append(f"     • {mode}")
        if item.get("limits"):
            lines.append(f"   Limit: {item['limits']}")
        if item.get("examples"):
            for ex in item["examples"][:3]:
                lines.append(f"   e.g. {ex}")
        lines.append("")
    lines.extend(
        [
            "Example prompt (copy and edit — run: jobgru prompts):",
            "",
            "  jobgru prompts",
            "",
            "  GitHub: https://github.com/ashujha301/jobgru/blob/main/prompts/jobgru-run.md",
        ]
    )
    return "\n".join(lines)


def catalog_json() -> dict:
    return {
        "run_limits": RUN_LIMITS,
        "filters": FILTER_CATALOG,
        "count": len(FILTER_CATALOG),
    }


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
