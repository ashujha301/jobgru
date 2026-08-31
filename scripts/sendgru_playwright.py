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

# Profile action bar is left column; sidebar "More profiles for you" is ~x>=740.
PROFILE_ACTION_MIN_Y = 100
PROFILE_ACTION_MAX_X = 700
PROFILE_ACTION_Y_TOLERANCE = 80


def _leftmost_visible_locator(
    root_locator,
    *,
    max_x: float = PROFILE_ACTION_MAX_X,
    min_y: float = PROFILE_ACTION_MIN_Y,
    y_anchor: float | None = None,
    y_tolerance: float = PROFILE_ACTION_Y_TOLERANCE,
):
    """Pick the leftmost visible control in the profile header (not sidebar/nav)."""
    best = None
    best_x = float("inf")
    try:
        count = root_locator.count()
    except Exception:
        return None
    for i in range(count):
        el = root_locator.nth(i)
        try:
            if not el.is_visible(timeout=500):
                continue
            box = el.bounding_box()
            if not box:
                continue
            if box["y"] < min_y or box["x"] > max_x:
                continue
            if y_anchor is not None and abs(box["y"] - y_anchor) > y_tolerance:
                continue
            if box["x"] < best_x:
                best_x = box["x"]
                best = el
        except Exception:
            continue
    return best


def _profile_follow_locator(page):
    return _leftmost_visible_locator(
        page.locator("main").get_by_role(
            "button",
            name=re.compile(r"^Follow\b", re.I),
        )
    )


def _profile_action_y_anchor(page) -> float | None:
    follow = _profile_follow_locator(page)
    if follow is None:
        return None
    try:
        box = follow.bounding_box()
        return box["y"] if box else None
    except Exception:
        return None


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
    """Blue Connect in the profile header (primary path), not sidebar suggestions."""
    y_anchor = _profile_action_y_anchor(page)
    for role in ("button", "link"):
        loc = page.locator("main").get_by_role(role, name=re.compile(r"^Connect$", re.I))
        found = _leftmost_visible_locator(loc, y_anchor=y_anchor)
        if found is not None:
            return found
    loc = page.locator("main").locator('[aria-label*="Invite"][aria-label*="connect" i]')
    return _leftmost_visible_locator(loc, y_anchor=y_anchor)


def header_follow_visible(page) -> bool:
    return _profile_follow_locator(page) is not None


def header_more_locator(page):
    """More dropdown beside Follow/Message — not global nav or sidebar."""
    return _leftmost_visible_locator(
        page.locator("main").get_by_role("button", name=re.compile(r"^More$", re.I)),
        y_anchor=_profile_action_y_anchor(page),
    )


def dropdown_connect_locator(page):
    """Connect inside the More dropdown list (menu), not sidebar cards."""
    getters = [
        lambda: page.get_by_role("menuitem", name=re.compile(r"^Connect$", re.I)),
        lambda: page.locator('[role="menu"] button, [role="menu"] a').filter(
            has_text=re.compile(r"^Connect$", re.I)
        ),
        lambda: page.locator(".artdeco-dropdown__content-inner button, .artdeco-dropdown__content-inner a").filter(
            has_text=re.compile(r"^Connect$", re.I)
        ),
    ]
    for getter in getters:
        loc = _visible_locator(page, getter, timeout_ms=1500)
        if loc is not None:
            return loc
    return None


def message_button_locator(page):
    """Profile header Message — not sidebar 'Message {name}' links."""
    y_anchor = _profile_action_y_anchor(page)
    for role in ("button", "link"):
        loc = page.locator("main").get_by_role(role, name=re.compile(r"^Message$", re.I))
        found = _leftmost_visible_locator(loc, y_anchor=y_anchor)
        if found is not None:
            return found
    loc = page.locator("main").locator('[aria-label*="Message" i]').filter(
        has_text=re.compile(r"^Message$", re.I)
    )
    return _leftmost_visible_locator(loc, y_anchor=y_anchor)


def is_pending(page) -> bool:
    text = page_text_lower(page)
    if "pending" in text:
        return True
    try:
        if page.get_by_role("button", name=re.compile(r"^Pending$", re.I)).count() > 0:
            btn = page.get_by_role("button", name=re.compile(r"^Pending$", re.I)).first
            if btn.is_visible(timeout=1500):
                return True
    except Exception:
        pass
    return False


def is_first_degree_connected(page) -> bool:
    """True when Message is available and Connect invite flow is not."""
    if header_connect_locator(page) is not None:
        return False
    if header_follow_visible(page) and header_more_locator(page) is not None:
        return False
    if is_pending(page):
        return False
    return message_button_locator(page) is not None


def already_connected_or_pending(page) -> bool:
    """Legacy helper — pending skips; connected profiles are handled via direct message."""
    if is_pending(page):
        return True
    return is_first_degree_connected(page)


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


_INVITE_MODAL_PHRASES = (
    "add a note",
    "send without a note",
    "send invitation",
    "personalize your invitation",
)


def invite_modal(page):
    """LinkedIn invite dialog (Connect → Add a note flow), not message overlays."""
    selectors = ('[role="dialog"]', ".artdeco-modal", "[data-test-modal]")
    for sel in selectors:
        try:
            loc = page.locator(sel)
            count = loc.count()
        except Exception:
            continue
        for i in range(count - 1, -1, -1):
            modal = loc.nth(i)
            try:
                if not modal.is_visible(timeout=500):
                    continue
                text = modal.inner_text(timeout=1500).lower()
            except Exception:
                continue
            if any(p in text for p in _INVITE_MODAL_PHRASES):
                return modal
    return None


def _normalize_note_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def note_field_matches(expected: str, actual: str) -> bool:
    exp = _normalize_note_text(expected)
    got = _normalize_note_text(actual)
    if not exp:
        return False
    return exp == got or exp in got


def wait_for_invite_modal(page, *, timeout_sec: float = 8):
    """Return modal locator once invite UI is visible."""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        modal = invite_modal(page)
        if modal is not None:
            try:
                text = modal.inner_text(timeout=2000).lower()
                if any(p in text for p in _INVITE_MODAL_PHRASES):
                    return modal
            except Exception:
                pass
        time.sleep(0.5)
    return None


def click_add_note(page, modal=None) -> bool:
    modal = modal or invite_modal(page)
    if modal is None:
        return False
    patterns = [
        re.compile(r"Add a note", re.I),
        re.compile(r"Add note", re.I),
    ]
    for pat in patterns:
        try:
            btn = modal.get_by_role("button", name=pat).first
            if btn.count() > 0 and btn.is_visible(timeout=3000):
                btn.click(timeout=5000)
                return True
        except Exception:
            continue
    return False


def fill_note(page, note: str, *, modal=None) -> bool:
    modal = modal or invite_modal(page)
    if modal is None:
        return False
    selectors = [
        'textarea[name="message"]',
        "textarea#custom-message",
        'div[role="textbox"]',
        "textarea",
    ]
    for sel in selectors:
        try:
            loc = modal.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=3000):
                loc.click(timeout=3000)
                loc.fill("", timeout=3000)
                loc.fill(note, timeout=5000)
                try:
                    actual = loc.input_value(timeout=2000)
                except Exception:
                    actual = loc.inner_text(timeout=2000)
                if note_field_matches(note, actual):
                    return True
                loc.click(timeout=3000)
                loc.press("ControlOrMeta+A")
                loc.fill(note, timeout=5000)
                try:
                    actual = loc.input_value(timeout=2000)
                except Exception:
                    actual = loc.inner_text(timeout=2000)
                return note_field_matches(note, actual)
        except Exception:
            continue
    return False


def click_send(page, *, modal=None) -> bool:
    modal = modal or invite_modal(page)
    if modal is None:
        return False
    patterns = [
        re.compile(r"^Send invitation$", re.I),
        re.compile(r"^Send$", re.I),
        re.compile(r"Send now", re.I),
    ]
    for pat in patterns:
        try:
            btn = modal.get_by_role("button", name=pat).first
            if btn.count() > 0 and btn.is_visible(timeout=3000):
                btn.click(timeout=5000)
                return True
        except Exception:
            continue
    return False


def message_compose(page):
    """LinkedIn DM compose overlay after clicking Message on a profile."""
    selectors = [
        ".msg-overlay-conversation-bubble",
        ".msg-convo-wrapper",
        ".msg-form",
        '[role="dialog"]',
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel).last
            if loc.count() > 0 and loc.is_visible(timeout=1500):
                return loc
        except Exception:
            continue
    return None


def wait_for_message_compose(page, *, timeout_sec: float = 8):
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        compose = message_compose(page)
        if compose is not None:
            try:
                text = compose.inner_text(timeout=2000).lower()
                if any(p in text for p in ("write a message", "send", "message")):
                    return compose
                if compose.locator('div[role="textbox"], textarea').count() > 0:
                    return compose
            except Exception:
                return compose
        time.sleep(0.5)
    return None


def fill_message(page, note: str, *, compose=None) -> bool:
    compose = compose or message_compose(page)
    if compose is None:
        return False
    selectors = [
        'div[role="textbox"]',
        "textarea",
        ".msg-form__contenteditable",
    ]
    for sel in selectors:
        try:
            loc = compose.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=3000):
                loc.click(timeout=3000)
                loc.fill("", timeout=3000)
                loc.fill(note, timeout=5000)
                try:
                    actual = loc.input_value(timeout=2000)
                except Exception:
                    actual = loc.inner_text(timeout=2000)
                if note_field_matches(note, actual):
                    return True
                loc.click(timeout=3000)
                loc.press("ControlOrMeta+A")
                loc.fill(note, timeout=5000)
                try:
                    actual = loc.input_value(timeout=2000)
                except Exception:
                    actual = loc.inner_text(timeout=2000)
                return note_field_matches(note, actual)
        except Exception:
            continue
    return False


def click_message_send(page, *, compose=None) -> bool:
    compose = compose or message_compose(page)
    if compose is None:
        return False
    patterns = [
        re.compile(r"^Send$", re.I),
        re.compile(r"Send message", re.I),
    ]
    for pat in patterns:
        try:
            btn = compose.get_by_role("button", name=pat).first
            if btn.count() > 0 and btn.is_visible(timeout=3000):
                return _safe_click(btn)
        except Exception:
            continue
    try:
        btn = compose.locator('button[type="submit"], .msg-form__send-button').first
        if btn.count() > 0 and btn.is_visible(timeout=3000):
            return _safe_click(btn)
    except Exception:
        pass
    return False


def send_direct_message(page, note: str) -> tuple[str, str]:
    msg_btn = message_button_locator(page)
    if msg_btn is None:
        return "skipped", "Message button not found"
    if not _safe_click(msg_btn):
        return "failed", "could not click Message"

    time.sleep(2)
    compose = wait_for_message_compose(page)
    if compose is None:
        return "failed", "message compose did not open"

    time.sleep(1)
    if not fill_message(page, note, compose=compose):
        return "failed", "could not verify message text"

    time.sleep(1)
    if not click_message_send(page, compose=compose):
        return "failed", "Send button not found in message compose"

    time.sleep(3)
    stop = check_stop(page)
    if stop:
        return "stopped", stop

    return "sent", "ok (direct message)"


def send_to_person(
    page,
    *,
    url: str,
    note: str,
    company: str,
    first_navigate: bool,
) -> tuple[str, str]:
    if not first_navigate:
        delay = random.randint(PACING_MIN, PACING_MAX)
        time.sleep(delay)

    note = (note or "").strip()
    if not note:
        return "failed", "empty note for row"

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
    except Exception as exc:
        return "failed", f"navigate: {exc}"

    time.sleep(3)
    stop = check_stop(page)
    if stop:
        return "stopped", stop

    if is_pending(page):
        return "skipped", "pending invitation"

    if is_first_degree_connected(page):
        return send_direct_message(page, note)

    if not click_connect(page):
        if header_follow_visible(page):
            return "skipped", "Connect not found in More menu"
        return "skipped", "Connect button not found"

    modal = wait_for_invite_modal(page)
    if modal is None:
        if message_button_locator(page) is not None:
            return send_direct_message(page, note)
        return "skipped", "Invite modal did not open"

    time.sleep(1)
    if not click_add_note(page, modal):
        return "skipped", "Add a note not available"

    time.sleep(1)
    if not fill_note(page, note, modal=modal):
        return "failed", f"could not verify note for {company!r}"

    time.sleep(1)
    if not click_send(page, modal=modal):
        return "failed", "Send invitation button not found in modal"

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
                    # Re-read note from sheet so each person gets this row's exact H text.
                    fresh, _, _ = load_actionable_rows(str(row_target.row), apply_daily_cap=False)
                    row_note = fresh[0].note if fresh else row_target.note
                    print(
                        f"SendGru row {row_target.row} ({row_target.company}) → {person.name or person.url}",
                        file=sys.stderr,
                    )
                    print(f"  note: {row_note[:80]}...", file=sys.stderr)
                    status, detail = send_to_person(
                        page,
                        url=person.url,
                        note=row_note,
                        company=row_target.company,
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
