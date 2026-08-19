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

YOU do (2 manual steps):
  1. Copy template → File → Make a copy → tab must stay "Job Applications"
  2. Terminal auth (sheet owner Google account):
     gcloud auth login --enable-gdrive-access --update-adc

CHAT commands (Cursor / Claude Code / Codex — any folder):
  Jobgru setup     First-time config (sheet URL, name, resume PDF)
  Jobgru help      Show this guide
  Jobgru check     Verify setup is READY
  Jobgru mcp       Install/check Playwright MCP (Claude + Codex browser)
  Jobgru filter    Show or save job-search filters; print ready prompt
  Jobgru delete    Delete sheet rows (e.g. rows 42-44 or 42,43,44)
  /jobgru + search Run full pipeline (jobs → leads → ATS)

TERMINAL commands:
  jobgru check
  jobgru setup --url SHEET_URL --name YOUR_NAME [--resume-link URL]
  jobgru mcp install          Register Playwright MCP (Claude + Codex)
  jobgru mcp status           Browser/MCP status per agent
  jobgru filter show          Show saved filters
  jobgru filter set --location Bangalore --roles "SWE,SWE AI" ...
  jobgru filter prompt        Copy-paste job search prompt from saved filters
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
        "manual_steps": [
            "Copy Google Sheet template (tab: Job Applications)",
            "gcloud auth login --enable-gdrive-access --update-adc",
        ],
        "chat_commands": {
            "Jobgru setup": "Configure sheet URL, name, resume PDF",
            "Jobgru help": "Show full command guide",
            "Jobgru check": "Health check — must show READY before pipeline",
            "Jobgru mcp": "Install or verify Playwright MCP (Claude/Codex)",
            "Jobgru filter": "Show/save filters or print job-search prompt",
            "Jobgru delete": "Delete rows from sheet (single, list, or range)",
            "/jobgru + search": "Full pipeline: Jobgru + LeadGru + ATSScore",
        },
        "terminal_commands": {
            "jobgru check": "Health check",
            "jobgru setup": "Configure sheet (--url, --name, --resume-link)",
            "jobgru mcp install": "Register Playwright MCP for Claude + Codex",
            "jobgru mcp status": "Browser/MCP status",
            "jobgru filter show|set|prompt": "Saved job-search filters",
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
