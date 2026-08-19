#!/usr/bin/env python3
"""Open LinkedIn login in the Jobgru Playwright browser profile."""

from __future__ import annotations

import sys
from pathlib import Path

BROWSER_PROFILE = Path.home() / ".jobgru" / "browser-profile"
LOGIN_URL = "https://www.linkedin.com/login"


def _read_tty(prompt: str) -> None:
    """Read Enter from the real terminal (works when stdin is piped)."""
    try:
        with open("/dev/tty", "r") as tty:
            print(prompt, flush=True)
            tty.readline()
    except OSError:
        input(prompt)


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "playwright Python package missing.\n"
            "Run: ~/.jobgru/.venv/bin/pip install playwright\n"
            "Then retry: jobgru mcp login",
            file=sys.stderr,
        )
        return 1

    BROWSER_PROFILE.mkdir(parents=True, exist_ok=True)
    print("Opening LinkedIn in the Jobgru browser profile...")
    print(f"Profile: {BROWSER_PROFILE}")
    print("")
    print("  1. Sign into LinkedIn in the browser window (complete MFA if asked)")
    print("  2. Come back here and press ENTER — the browser will close and save your session")
    print("     (Do NOT close the browser yourself — press ENTER here instead)")
    print("")

    launch_kwargs: dict = {
        "user_data_dir": str(BROWSER_PROFILE),
        "headless": False,
        "args": ["--start-maximized"],
    }

    with sync_playwright() as p:
        context = None
        for channel in ("chrome", None):
            try:
                if channel:
                    context = p.chromium.launch_persistent_context(channel=channel, **launch_kwargs)
                else:
                    context = p.chromium.launch_persistent_context(**launch_kwargs)
                break
            except Exception as exc:
                if channel is None:
                    print(f"Could not launch browser: {exc}", file=sys.stderr)
                    print("Install Chrome or run: ~/.jobgru/.venv/bin/playwright install chromium")
                    return 1
                continue

        page = context.pages[0] if context.pages else context.new_page()
        page.goto(LOGIN_URL, wait_until="domcontentloaded")

        _read_tty("\n>>> Press ENTER here after you have signed into LinkedIn... ")

        context.close()

    print("")
    print("OK: LinkedIn session saved.")
    print("Future Codex/Claude Playwright runs will reuse this login.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
