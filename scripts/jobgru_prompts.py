#!/usr/bin/env python3
"""Print Jobgru example prompts for copy-edit-paste into chat."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from jobgru_filters import (  # noqa: E402
    RUN_LIMITS,
    SHORT_NATURAL_PROMPT,
    prompt_example,
    prompt_template,
)

GITHUB_PROMPTS_URL = "https://github.com/ashujha301/jobgru/blob/main/prompts/jobgru-run.md"

PROMPT_LABELS = (
    "template",
    "example_linkedin_swe_bangalore",
    "short_natural",
)


def load_prompt_blocks() -> dict[str, str]:
    return {
        "template": prompt_template(),
        "example_linkedin_swe_bangalore": prompt_example(),
        "short_natural": SHORT_NATURAL_PROMPT,
    }


def prompts_text(blocks: dict[str, str]) -> str:
    lines = [
        "Jobgru — copy-edit-paste prompts",
        "=" * 34,
        "",
        "One prompt runs the full pipeline: jobs → leads → ATS.",
        f"Limits: max {RUN_LIMITS['max_jobs_per_run']} jobs/run, LinkedIn max {RUN_LIMITS['max_linkedin_per_run']}/run.",
        "",
        "1) TEMPLATE — all filters (edit values, paste into chat)",
        "-" * 34,
        blocks["template"],
        "",
        "2) EXAMPLE — LinkedIn SWE in Bangalore (all filters filled)",
        "-" * 34,
        blocks["example_linkedin_swe_bangalore"],
        "",
        "3) SHORT — natural language (also works)",
        "-" * 34,
        blocks["short_natural"],
        "",
        "Filter catalog: jobgru filter",
        f"GitHub: {GITHUB_PROMPTS_URL}",
    ]
    return "\n".join(lines)


def prompts_json(blocks: dict[str, str]) -> dict:
    return {
        "prompts": blocks,
        "run_limits": RUN_LIMITS,
        "github_url": GITHUB_PROMPTS_URL,
        "filter_command": "jobgru filter",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Show Jobgru example prompts to copy into chat")
    parser.add_argument("--json", action="store_true", help="Output prompts as JSON")
    parser.add_argument(
        "--which",
        choices=["all", *PROMPT_LABELS],
        default="all",
        help="Print one prompt block only (default: all)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    blocks = load_prompt_blocks()

    if args.json:
        payload = prompts_json(blocks)
        if args.which != "all":
            payload = {"prompt": blocks[args.which], "github_url": GITHUB_PROMPTS_URL}
        print(json.dumps(payload, indent=2))
        return 0

    if args.which == "all":
        print(prompts_text(blocks))
    else:
        print(blocks[args.which])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
