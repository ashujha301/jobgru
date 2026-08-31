#!/usr/bin/env python3
"""SendGru Playwright fallback — send LinkedIn connection notes without browser MCP.

Uses the Jobgru persistent browser profile (~/.jobgru/browser-profile).
Run when cursor-ide-browser MCP is disconnected or unavailable in Cursor.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from jobgru_linkedin_login import BROWSER_PROFILE, linkedin_logged_in  # noqa: E402
from sendgru_select import (  # noqa: E402
    MAX_SENDS_PER_DAY,
    RowTarget,
    apply_daily_cap as cap_daily_sends,
    cmd_mark_sent,
    parse_row_spec,
    row_to_json,
    select_from_sheet_rows,
    total_send_count,
)

STOP_PHRASES = [
    "unusual activity",
    "verify your identity",
    "security verification",
    "captcha",
    "weekly invitation limit",
    "you've reached the weekly",
    "invitation limit",
    "temporarily restricted",
]

PACING_MIN = 60
PACING_MAX = 90
BETWEEN_COMPANIES_EXTRA = 30


@dataclass
class SendResult:
    row: int
    company: str
    url: str
    status: str  # sent | skipped | failed | stopped
    detail: str = ""


@dataclass
class RunSummary:
    mode: str = "sendgru_playwright"
    rows_requested: list[int] = field(default_factory=list)
    rows_sent: list[int] = field(default_factory=list)
    rows_skipped: list[dict] = field(default_factory=list)
    people_results: list[dict] = field(default_factory=list)
    people_sent: int = 0
    stopped_reason: str | None = None
    dry_run: bool = False


def page_text_lower(page) -> str:
    try:
        return page.inner_text("body").lower()
    except Exception:
        return ""


def check_stop(page) -> str | None:
    text = page_text_lower(page)
    for phrase in STOP_PHRASES:
        if phrase in text:
            return phrase
    return None


def _visible_locator(page, getter, *, timeout_ms: int = 2000):
    """Return first visible locator from getter(), or None."""
    try:
        loc = getter()
        if loc.count() > 0 and loc.first.is_visible(timeout=timeout_ms):
            return loc.first
    except Exception:
        pass
    return None


def _safe_click(loc, *, timeout_ms: int = 5000) -> bool:
    try:
        loc.click(timeout=timeout_ms)
        return True
    except Exception:
        try:
            loc.click(force=True, timeout=timeout_ms)
            return True
        except Exception:
            return False


def header_connect_locator(page):
    """Blue Connect in the profile header (primary path)."""
    getters = [
        lambda: page.get_by_role("button", name=re.compile(r"^Connect$", re.I)),
        lambda: page.get_by_role("link", name=re.compile(r"^Connect$", re.I)),
        lambda: page.locator('[aria-label*="Invite"][aria-label*="connect" i]'),
        lambda: page.locator("main button, main a").filter(
            has_text=re.compile(r"^Connect$", re.I)
        ),
    ]
    for getter in getters:
        loc = _visible_locator(page, getter)
        if loc is not None:
            return loc
    return None


def header_follow_visible(page) -> bool:
    return _visible_locator(
        page,
        lambda: page.get_by_role("button", name=re.compile(r"^Follow$", re.I)),
    ) is not None


def header_more_locator(page):
    return _visible_locator(
        page,
        lambda: page.get_by_role("button", name=re.compile(r"^More\b", re.I)),
    )


def dropdown_connect_locator(page):
    """Connect inside the More dropdown list."""
    getters = [
        lambda: page.get_by_role("menuitem", name=re.compile(r"^Connect$", re.I)),
        lambda: page.get_by_role("button", name=re.compile(r"^Connect$", re.I)),
        lambda: page.locator('[role="menu"] button, [role="menu"] a, .artdeco-dropdown__content-inner button, .artdeco-dropdown__content-inner a').filter(
            has_text=re.compile(r"^Connect$", re.I)
        ),
        lambda: page.locator('[aria-label*="Invite"][aria-label*="connect" i]'),
    ]
    for getter in getters:
        loc = _visible_locator(page, getter, timeout_ms=1500)
        if loc is not None:
            return loc
    return None


def already_connected_or_pending(page) -> bool:
    """Skip when Connect is unavailable and profile is already connected/pending."""
    if header_connect_locator(page) is not None:
        return False
    if header_follow_visible(page) and header_more_locator(page) is not None:
        return False
    text = page_text_lower(page)
    if "pending" in text:
        return True
    try:
        if page.get_by_role("button", name=re.compile(r"^Pending$", re.I)).count() > 0:
            return True
        msg = page.get_by_role("button", name=re.compile(r"^Message$", re.I)).first
        if msg.count() > 0 and msg.is_visible(timeout=1500):
            return True
    except Exception:
        pass
    return False


def click_connect(page) -> bool:
    """Profile header flow: blue Connect, or Follow + More → Connect."""
    connect = header_connect_locator(page)
    if connect is not None:
        return _safe_click(connect)

    if not header_follow_visible(page):
        return False

    more = header_more_locator(page)
    if more is None:
        return False
    if not _safe_click(more):
        return False

    time.sleep(1)
    connect = dropdown_connect_locator(page)
    if connect is None:
        return False
    return _safe_click(connect)


def wait_for_invite_modal(page, *, timeout_sec: float = 8) -> bool:
    """After Connect, LinkedIn shows Add a note / Send without a note."""
    deadline = time.time() + timeout_sec
    patterns = [
        re.compile(r"Add a note", re.I),
        re.compile(r"Send without a note", re.I),
        re.compile(r"Send invitation", re.I),
    ]
    while time.time() < deadline:
        for pat in patterns:
            try:
                if page.get_by_text(pat).count() > 0:
                    return True
            except Exception:
                pass
        time.sleep(0.5)
    return False


def click_add_note(page) -> bool:
    patterns = [
        re.compile(r"Add a note", re.I),
        re.compile(r"Add note", re.I),
    ]
    for pat in patterns:
        try:
            btn = page.get_by_role("button", name=pat).first
            if btn.count() > 0 and btn.is_visible(timeout=3000):
                btn.click(timeout=5000)
                return True
        except Exception:
            continue
    return False


def fill_note(page, note: str) -> bool:
    selectors = [
        'textarea[name="message"]',
        "textarea#custom-message",
        'div[role="textbox"]',
        "textarea",
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=3000):
                loc.click(timeout=3000)
                loc.fill(note, timeout=5000)
                return True
        except Exception:
            continue
    return False


def click_send(page) -> bool:
    patterns = [
        re.compile(r"^Send invitation$", re.I),
        re.compile(r"^Send$", re.I),
        re.compile(r"Send now", re.I),
    ]
    for pat in patterns:
        try:
            btn = page.get_by_role("button", name=pat).first
            if btn.count() > 0 and btn.is_visible(timeout=3000):
                btn.click(timeout=5000)
                return True
        except Exception:
            continue
    return False


def send_to_person(page, *, url: str, note: str, first_navigate: bool) -> tuple[str, str]:
    if not first_navigate:
        delay = random.randint(PACING_MIN, PACING_MAX)
        time.sleep(delay)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
    except Exception as exc:
        return "failed", f"navigate: {exc}"

    time.sleep(3)
    stop = check_stop(page)
    if stop:
        return "stopped", stop

    if already_connected_or_pending(page):
        return "skipped", "already connected or pending"

    if not click_connect(page):
        if header_follow_visible(page):
            return "skipped", "Connect not found in More menu"
        return "skipped", "Connect button not found"

    if not wait_for_invite_modal(page):
        return "skipped", "Invite modal did not open"

    time.sleep(1)
    if not click_add_note(page):
        return "skipped", "Add a note not available"

    time.sleep(1)
    if not fill_note(page, note):
        return "failed", "could not fill note"

    time.sleep(1)
    if not click_send(page):
        return "failed", "Send button not found"

    time.sleep(5)
    stop = check_stop(page)
    if stop:
        return "stopped", stop

    return "sent", "ok"


def load_actionable_rows(row_spec: str, *, apply_daily_cap: bool) -> tuple[list[RowTarget], list[RowTarget], list[int]]:
    from sheets_write import read_range, sheets_service
    from sheet_config import get_spreadsheet_id, get_tab

    row_nums = parse_row_spec(row_spec)
    if not row_nums:
        return [], [], []

    service = sheets_service()
    sid = get_spreadsheet_id()
    tab = get_tab()
    lo, hi = min(row_nums), max(row_nums)
    values = read_range(service, sid, tab, f"A{lo}:H{hi}")
    sheet_rows = {lo + i: cells for i, cells in enumerate(values)}
    actionable, skipped = select_from_sheet_rows(row_nums, sheet_rows)
    if apply_daily_cap:
        actionable, extra = cap_daily_sends(actionable, MAX_SENDS_PER_DAY)
        skipped.extend(extra)
    return actionable, skipped, row_nums


def mark_rows_sent(rows: list[int]) -> None:
    if not rows:
        return
    spec = ",".join(str(r) for r in rows)
    args = argparse.Namespace(rows=spec)
    cmd_mark_sent(args)


def run_sendgru(
    row_spec: str,
    *,
    apply_daily_cap: bool = True,
    dry_run: bool = False,
    headless: bool = False,
) -> RunSummary:
    summary = RunSummary(dry_run=dry_run)
    actionable, skipped, row_nums = load_actionable_rows(row_spec, apply_daily_cap=apply_daily_cap)
    summary.rows_requested = row_nums
    summary.rows_skipped = [row_to_json(r) for r in skipped]

    if dry_run:
        summary.people_results = [
            {"row": r.row, "company": r.company, "url": p.url, "status": "dry_run"}
            for r in actionable
            for p in r.people
        ]
        return summary

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        summary.stopped_reason = "playwright not installed — run: pip install playwright"
        return summary

    BROWSER_PROFILE.mkdir(parents=True, exist_ok=True)
    rows_with_sends: list[int] = []
    first_navigate = True
    last_row: int | None = None

    with sync_playwright() as p:
        launch_kwargs = {
            "user_data_dir": str(BROWSER_PROFILE),
            "headless": headless,
            "args": ["--start-maximized"],
        }
        context = None
        for channel in ("chrome", None):
            try:
                if channel:
                    context = p.chromium.launch_persistent_context(channel=channel, **launch_kwargs)
                else:
                    context = p.chromium.launch_persistent_context(**launch_kwargs)
                break
            except Exception:
                if channel is None:
                    summary.stopped_reason = "could not launch browser — run: playwright install chromium"
                    return summary
                continue

        if context is None:
            summary.stopped_reason = "could not launch browser"
            return summary

        if not linkedin_logged_in(context):
            summary.stopped_reason = (
                "LinkedIn not logged in — run: jobgru mcp login (uses ~/.jobgru/browser-profile)"
            )
            context.close()
            return summary

        page = context.pages[0] if context.pages else context.new_page()
        row_sent_count: dict[int, int] = {}

        try:
            for row_target in actionable:
                if last_row is not None and row_target.row != last_row:
                    time.sleep(BETWEEN_COMPANIES_EXTRA)
                last_row = row_target.row

                for person in row_target.people:
                    status, detail = send_to_person(
                        page,
                        url=person.url,
                        note=row_target.note,
                        first_navigate=first_navigate,
                    )
                    first_navigate = False
                    result = SendResult(
                        row=row_target.row,
                        company=row_target.company,
                        url=person.url,
                        status=status,
                        detail=detail,
                    )
                    summary.people_results.append(asdict(result))

                    if status == "sent":
                        summary.people_sent += 1
                        row_sent_count[row_target.row] = row_sent_count.get(row_target.row, 0) + 1
                    elif status == "stopped":
                        summary.stopped_reason = detail
                        break

                if summary.stopped_reason:
                    break

            rows_with_sends = [r for r, c in row_sent_count.items() if c > 0]
            summary.rows_sent = rows_with_sends
        finally:
            context.close()

    mark_rows_sent(rows_with_sends)
    return summary


def cmd_send(args: argparse.Namespace) -> int:
    summary = run_sendgru(
        args.rows,
        apply_daily_cap=args.apply_daily_cap,
        dry_run=args.dry_run,
        headless=args.headless,
    )
    print(json.dumps(asdict(summary), indent=2))
    if summary.stopped_reason and not summary.dry_run:
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="SendGru Playwright fallback (no browser MCP required)"
    )
    p.add_argument("--rows", required=True, help='Row spec: "64-70", "4,6,9"')
    p.add_argument("--apply-daily-cap", action="store_true", help="Cap at 20 sends/run")
    p.add_argument("--dry-run", action="store_true", help="Select targets only, no browser")
    p.add_argument("--headless", action="store_true", help="Headless browser (not recommended for LinkedIn)")
    p.set_defaults(func=cmd_send)
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
