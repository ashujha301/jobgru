#!/usr/bin/env python3
"""Register and verify Playwright MCP for Claude Code and Codex."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

MCP_NAME = "playwright"
BROWSER_PROFILE = Path.home() / ".jobgru" / "browser-profile"
PLAYWRIGHT_NPX_ARGS = [
    "@playwright/mcp@latest",
    "--user-data-dir",
    str(BROWSER_PROFILE),
]


def _run(cmd: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def agent_present(agent: str) -> bool:
    return shutil.which(agent) is not None


def mcp_list_output(agent: str) -> str:
    result = _run([agent, "mcp", "list"])
    if result.returncode != 0:
        return result.stderr or result.stdout or ""
    return result.stdout or ""


def playwright_registered(agent: str) -> bool:
    if not agent_present(agent):
        return False
    output = mcp_list_output(agent)
    return MCP_NAME in output.lower()


def remove_playwright(agent: str) -> None:
    if playwright_registered(agent):
        _run([agent, "mcp", "remove", MCP_NAME])


def install_playwright(agent: str, *, force: bool = False) -> tuple[bool, str]:
    if not agent_present(agent):
        return False, f"{agent} CLI not found on PATH"
    if playwright_registered(agent) and not force:
        return True, f"{agent}: Playwright MCP already registered (run: jobgru mcp install --force to refresh profile)"
    if playwright_registered(agent):
        remove_playwright(agent)
    BROWSER_PROFILE.mkdir(parents=True, exist_ok=True)
    result = _run([agent, "mcp", "add", MCP_NAME, "--", "npx", *PLAYWRIGHT_NPX_ARGS])
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "unknown error").strip()
        return False, f"{agent}: failed to register Playwright MCP — {err}"
    return True, f"{agent}: Playwright MCP registered (profile: {BROWSER_PROFILE})"


def linkedin_login_instructions() -> str:
    return f"""LinkedIn login for LeadGru (Codex / Claude Code)
==============================================

LeadGru needs a **signed-in LinkedIn** session in Playwright — not public web search.

One-time setup:
  1. jobgru mcp install        (register BEFORE starting the Codex session)
  2. Start a NEW Codex session, then paste:

     Use the playwright MCP tool browser_navigate to open
     https://www.linkedin.com/login — do not use any built-in browser skill.
     Wait while I sign in manually. Do not continue until I say I'm logged in.

  3. A browser window opens — sign into LinkedIn (complete MFA if asked)
  4. Say: "I'm logged in to LinkedIn"
  5. Close the window or leave it — login is saved on disk in:
     {BROWSER_PROFILE}
     Future runs reuse it automatically. No re-login needed.

Backfill leads for existing rows:
  LeadGru backfill rows 42-43 — use Playwright MCP, signed-in LinkedIn only.

Cursor users: sign into LinkedIn in Cursor Browser instead — no MCP step.
"""


def status_payload() -> dict:
    agents = {
        "cursor": {
            "present": True,
            "browser": "Cursor Browser (built-in)",
            "mcp_required": False,
            "playwright_registered": None,
            "note": "Sign into LinkedIn in Cursor Browser before LeadGru.",
        },
        "claude": {
            "present": agent_present("claude"),
            "browser": "Playwright MCP (persistent profile)",
            "mcp_required": True,
            "playwright_registered": playwright_registered("claude") if agent_present("claude") else False,
            "browser_profile": str(BROWSER_PROFILE),
            "install_command": "jobgru mcp install",
        },
        "codex": {
            "present": agent_present("codex"),
            "browser": "Playwright MCP (persistent profile)",
            "mcp_required": True,
            "playwright_registered": playwright_registered("codex") if agent_present("codex") else False,
            "browser_profile": str(BROWSER_PROFILE),
            "install_command": "jobgru mcp install",
        },
    }
    return {
        "agents": agents,
        "browser_profile": str(BROWSER_PROFILE),
        "linkedin_login_required_for_leadgru": True,
    }


def print_status() -> int:
    data = status_payload()
    print("Jobgru browser / MCP status")
    print("=" * 40)
    for name, info in data["agents"].items():
        label = name.capitalize()
        if name == "cursor":
            print(f"{label}: {info['browser']}")
            continue
        if not info["present"]:
            print(f"{label}: CLI not installed (skip MCP)")
            continue
        reg = info["playwright_registered"]
        state = "registered" if reg else "NOT registered"
        print(f"{label}: Playwright MCP {state}")
        if not reg:
            print("  Fix: jobgru mcp install")
    print("")
    print(f"Browser profile (LinkedIn cookies): {BROWSER_PROFILE}")
    print("LeadGru needs signed-in LinkedIn in Playwright — run: jobgru mcp login")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    ok = True
    for agent in ("claude", "codex"):
        if not agent_present(agent):
            print(f"SKIP: {agent} CLI not on PATH")
            continue
        success, message = install_playwright(agent, force=args.force)
        print(message)
        ok = ok and success
    print("")
    print(linkedin_login_instructions())
    return 0 if ok else 1


def cmd_login(_args: argparse.Namespace) -> int:
    print(linkedin_login_instructions())
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    if args.json:
        print(json.dumps(status_payload(), indent=2))
        return 0
    return print_status()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Jobgru Playwright MCP setup for Claude Code and Codex")
    sub = parser.add_subparsers(dest="command", required=True)
    install_p = sub.add_parser("install", help="Register Playwright MCP with persistent LinkedIn profile")
    install_p.add_argument("--force", action="store_true", help="Re-register MCP with profile dir")
    install_p.set_defaults(func=cmd_install)
    login_p = sub.add_parser("login", help="Show LinkedIn sign-in steps for LeadGru")
    login_p.set_defaults(func=cmd_login)
    status_p = sub.add_parser("status", help="Show browser/MCP status per agent")
    status_p.add_argument("--json", action="store_true")
    status_p.set_defaults(func=cmd_status)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
