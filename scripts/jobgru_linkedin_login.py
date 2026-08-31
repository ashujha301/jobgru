#!/usr/bin/env python3
"""Open LinkedIn login in the Jobgru Playwright browser profile."""

from __future__ import annotations

import sys
from pathlib import Path

BROWSER_PROFILE = Path.home() / ".jobgru" / "browser-profile"
LOGIN_URL = "https://www.linkedin.com/login"
FEED_URL = "https://www.linkedin.com/feed/"


def _read_tty(prompt: str) -> None:
    """Read Enter from the real terminal (works when stdin is piped)."""
    try:
        with open("/dev/tty", "r") as tty:
            print(prompt, flush=True)
            tty.readline()
    except OSError:
        input(prompt)


def linkedin_logged_in(context) -> bool:
    """Return True when LinkedIn session cookie li_at is present."""
    try:
        cookies = context.cookies()
    except Exception:
        return False
    for cookie in cookies:
        if cookie.get("name") == "li_at" and cookie.get("value"):
            return True
    return False


def verify_linkedin_session(context) -> bool:
    """Confirm login via cookie and feed URL (not redirected to login)."""
    if not linkedin_logged_in(context):
        return False
    try:
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(FEED_URL, wait_until="domcontentloaded", timeout=30000)
        url = page.url.lower()
        if "/login" in url or "uas/login" in url:
            return False
        return True
    except Exception:
        return False


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

        if context is None:
            print("Could not launch browser.", file=sys.stderr)
            return 1

        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(LOGIN_URL, wait_until="domcontentloaded")

            _read_tty("\n>>> Press ENTER here after you have signed into LinkedIn... ")

            if not verify_linkedin_session(context):
                print("")
                print("LinkedIn login was NOT detected.", file=sys.stderr)
                print("Sign in fully (including MFA), then press ENTER — do not close the browser early.", file=sys.stderr)
                context.close()
                return 1

            context.close()
        except Exception as exc:
            print(f"Browser closed or login check failed: {exc}", file=sys.stderr)
            print("Keep the browser open, sign into LinkedIn, then press ENTER in the terminal.", file=sys.stderr)
            try:
                context.close()
            except Exception:
                pass
            return 1

    print("")
    print("OK: LinkedIn session saved and verified.")
    print("Future Codex/Claude Playwright runs will reuse this login.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
