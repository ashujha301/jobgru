#!/usr/bin/env python3
"""Register and verify Playwright MCP for Claude Code and Codex."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys

PLAYWRIGHT_CMD = ["npx", "@playwright/mcp@latest"]
MCP_NAME = "playwright"


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


def install_playwright(agent: str) -> tuple[bool, str]:
    if not agent_present(agent):
        return False, f"{agent} CLI not found on PATH"
    if playwright_registered(agent):
        return True, f"{agent}: Playwright MCP already registered"
    result = _run([agent, "mcp", "add", MCP_NAME, "--", *PLAYWRIGHT_CMD])
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "unknown error").strip()
        return False, f"{agent}: failed to register Playwright MCP — {err}"
    return True, f"{agent}: Playwright MCP registered"


def status_payload() -> dict:
    agents = {
        "cursor": {
            "present": True,
            "browser": "Cursor Browser (built-in)",
            "mcp_required": False,
            "playwright_registered": None,
            "note": "No MCP setup needed in Cursor.",
        },
        "claude": {
            "present": agent_present("claude"),
            "browser": "Playwright MCP → Chrome",
            "mcp_required": True,
            "playwright_registered": playwright_registered("claude") if agent_present("claude") else False,
            "install_command": "jobgru mcp install",
        },
        "codex": {
            "present": agent_present("codex"),
            "browser": "Playwright MCP → Chrome",
            "mcp_required": True,
            "playwright_registered": playwright_registered("codex") if agent_present("codex") else False,
            "install_command": "jobgru mcp install",
        },
    }
    return {"agents": agents}


def print_status() -> int:
    data = status_payload()
    print("Jobgru browser / MCP status")
    print("=" * 40)
    for name, info in data["agents"].items():
        label = name.capitalize()
        if name == "cursor":
            print(f"{label}: {info['browser']} — {info['note']}")
            continue
        if not info["present"]:
            print(f"{label}: CLI not installed (skip MCP)")
            continue
        reg = info["playwright_registered"]
        state = "registered" if reg else "NOT registered"
        print(f"{label}: Playwright MCP {state}")
        if not reg:
            print(f"  Fix: jobgru mcp install   (or: {name} mcp add playwright -- npx @playwright/mcp@latest)")
    print("")
    print("Why: Job search can use web search; LeadGru needs a live browser for LinkedIn people search.")
    return 0


def cmd_install(_args: argparse.Namespace) -> int:
    ok = True
    for agent in ("claude", "codex"):
        if not agent_present(agent):
            print(f"SKIP: {agent} CLI not on PATH")
            continue
        success, message = install_playwright(agent)
        print(message)
        ok = ok and success
    print("")
    print("Cursor users: no MCP step — Cursor Browser is built in.")
    return 0 if ok else 1


def cmd_status(args: argparse.Namespace) -> int:
    if args.json:
        print(json.dumps(status_payload(), indent=2))
        return 0
    return print_status()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Jobgru Playwright MCP setup for Claude Code and Codex")
    sub = parser.add_subparsers(dest="command", required=True)
    install_p = sub.add_parser("install", help="Register Playwright MCP for Claude Code and Codex")
    install_p.set_defaults(func=cmd_install)
    status_p = sub.add_parser("status", help="Show browser/MCP status per agent")
    status_p.add_argument("--json", action="store_true")
    status_p.set_defaults(func=cmd_status)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
