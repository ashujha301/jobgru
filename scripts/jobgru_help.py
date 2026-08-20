#!/usr/bin/env python3
"""Centralized Jobgru help text for CLI and chat agents."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from jobgru_home import get_install_mode, get_jobgru_home  # noqa: E402
from sheet_config import get_template_sheet_url  # noqa: E402

TEMPLATE_URL = get_template_sheet_url()
HOME = get_jobgru_home()


def help_text() -> str:
    mode = get_install_mode()
    return f"""Jobgru — commands and quick start
══════════════════════════════════

Install: ~/.jobgru ({mode} mode) · Template: {TEMPLATE_URL}

FIRST TIME — one command (interactive wizard):
  curl -fsSL https://raw.githubusercontent.com/ashujha301/jobgru/main/install.sh | bash

  The installer walks you through:
    • gcloud install + Google sign-in
    • Open sheet template → Make a copy → paste YOUR copy URL
    • Verify sheet (tab, headers, write test)
    • LinkedIn login for LeadGru (Codex/Claude)
    • jobgru check → READY

  Resume (optional): cp resume.pdf to {HOME}/data/resumes/
  Skip wizard: ./install.sh --local . --skip-setup

MANUAL fallback (if you skipped steps):
  1. Copy template → File → Make a copy → tab "Job Applications"
  2. gcloud auth login --enable-gdrive-access --update-adc
  3. jobgru setup --url YOUR_COPY_URL
  4. jobgru mcp login   (Codex/Claude)
  5. jobgru check

CHAT commands (Cursor / Claude Code / Codex — any folder):
  Jobgru setup     First-time config (sheet URL, name, resume PDF)
  Jobgru help      Show this guide
  Jobgru check     Verify setup is READY
  Jobgru mcp       Install/check Playwright MCP (Claude + Codex browser)
  Jobgru filter    List every filter type you can use in a job-search prompt
  Jobgru delete    Delete sheet rows (e.g. rows 42-44 or 42,43,44)
  /jobgru + search Run full pipeline (jobs → leads → ATS)

TERMINAL commands:
  jobgru check
  jobgru setup --url SHEET_URL --name YOUR_NAME [--resume-link URL]
  jobgru mcp install          Register Playwright MCP (Claude + Codex)
  jobgru mcp login            Open LinkedIn login in the Jobgru browser (one time)
  jobgru mcp status           Browser/MCP status
  jobgru filter               List all filter types for job-search prompts
  jobgru filter --json        Same catalog as JSON
  jobgru delete --rows 42-44    Delete rows and compact the sheet
  jobgru update               Pull latest engine + refresh router skills
  jobgru uninstall            Remove global install

Browser by agent:
  Cursor       Built-in Cursor Browser (no MCP setup)
  Claude Code  Playwright MCP → run: jobgru mcp install
  Codex        Playwright MCP → run: jobgru mcp install

Resume for ATS (global install):
  Copy PDF to {HOME}/data/resumes/
  Or attach in chat: Jobgru setup — add my resume

Pipeline phases (one job-search prompt):
  Phase 1  Jobgru   Find jobs → write sheet (A–H)
  Phase 2  LeadGru  LinkedIn contacts → columns G/H (needs browser)
  Phase 2b ATSScore Resume fit → columns I/J (needs PDF in data/resumes/)

Docs: README.md · Troubleshooting: docs/SETUP.md
"""


def help_json() -> dict:
    return {
        "template_sheet_url": TEMPLATE_URL,
        "jobgru_home": str(HOME),
        "install_mode": get_install_mode(),
        "install_wizard": "curl -fsSL https://raw.githubusercontent.com/ashujha301/jobgru/main/install.sh | bash",
        "manual_steps": [
            "Copy Google Sheet template (tab: Job Applications)",
            "gcloud auth login --enable-gdrive-access --update-adc",
            "jobgru setup --url YOUR_COPY_URL",
            "jobgru mcp login (Codex/Claude)",
            "jobgru check",
        ],
        "chat_commands": {
            "Jobgru setup": "Configure sheet URL, name, resume PDF",
            "Jobgru help": "Show full command guide",
            "Jobgru check": "Health check — must show READY before pipeline",
            "Jobgru mcp": "Install or verify Playwright MCP (Claude/Codex)",
            "Jobgru filter": "List all filter types for job-search prompts",
            "Jobgru delete": "Delete rows from sheet (single, list, or range)",
            "/jobgru + search": "Full pipeline: Jobgru + LeadGru + ATSScore",
        },
        "terminal_commands": {
            "jobgru check": "Health check",
            "jobgru setup": "Configure sheet (--url, --name, --resume-link)",
            "jobgru mcp install": "Register Playwright MCP for Claude + Codex",
            "jobgru mcp status": "Browser/MCP status",
            "jobgru filter": "Catalog of filter types for prompts",
            "jobgru delete --rows SPEC": "Delete rows (42, 42-44, 42,44-46)",
            "jobgru update": "Pull latest from GitHub",
            "jobgru uninstall": "Remove global install",
        },
        "browser": {
            "cursor": "Cursor Browser built-in",
            "claude_code": "Playwright MCP (jobgru mcp install)",
            "codex": "Playwright MCP (jobgru mcp install)",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Jobgru help")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.json:
        print(json.dumps(help_json(), indent=2))
    else:
        print(help_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
