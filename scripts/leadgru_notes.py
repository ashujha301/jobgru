#!/usr/bin/env python3
"""Fill Add note Message from Q2–Q7 templates, always ≤ 200 chars when written to H."""

from __future__ import annotations

import argparse
import json
import re
import sys

MAX_FILLED_NOTE_CHARS = 200
URL_RE = re.compile(r"https?://\S+")
THANKS_SUFFIX = " Thanks"

# No lead name, no sender name, no "!". Resume short link stays. LeadGru fills
# {Position}/{Company}/{Link} then clamps to 200 if the titles are long.
DEFAULT_TEMPLATES = [
    "Hi, I just applied for {Position} at {Company} and would appreciate a referral. Resume: {Link} Thanks",
    "Hi, I applied for {Position} at {Company} and would love a referral. Resume: {Link} Thanks",
    "Hi, I am excited about {Position} at {Company} and just applied. Could you refer me. Resume: {Link} Thanks",
    "Hi, I recently applied for {Position} at {Company}. Could you share my resume with the team. Resume: {Link} Thanks",
    "Hi, I applied for {Position} at {Company} and would be grateful for a referral. Resume: {Link} Thanks",
    "Hi, I just applied for {Position} at {Company}. A referral would mean a lot. Resume: {Link} Thanks",
]


def fill_add_note(
    template: str,
    *,
    position: str,
    company: str,
    link: str,
) -> str:
    """Substitute placeholders and clamp to MAX_FILLED_NOTE_CHARS."""
    text = (template or "").replace("Hi {Name},", "Hi,")
    text = text.replace("{Name}", "")
    text = text.replace("{Position}", (position or "").strip())
    text = text.replace("{Company}", (company or "").strip())
    text = text.replace("{Link}", (link or "").strip())
    text = re.sub(r" {2,}", " ", text).strip()
    text = re.sub(r"Hi,\s*,", "Hi,", text)
    text = re.sub(r"!\s*", " ", text)
    text = re.sub(r" {2,}", " ", text).strip()
    if not text.endswith("Thanks"):
        text = text.rstrip(".!") + THANKS_SUFFIX
    return clamp_note(text, MAX_FILLED_NOTE_CHARS)


def clamp_note(text: str, max_len: int = MAX_FILLED_NOTE_CHARS) -> str:
    """Keep resume URL and trailing Thanks; shorten the body if over max_len."""
    text = (text or "").strip()
    if len(text) <= max_len:
        return text

    thanks = ""
    rest = text
    if rest.endswith("Thanks"):
        thanks = THANKS_SUFFIX
        rest = rest[: -len("Thanks")].rstrip()

    url = ""
    urls = list(URL_RE.finditer(rest))
    if urls:
        url = urls[-1].group(0).rstrip(".,;)")
        rest = rest[: urls[-1].start()].rstrip(" :")

    suffix = f" Resume: {url}{thanks}" if url else thanks
    budget = max_len - len(suffix)
    if budget < 12:
        return text[:max_len].rstrip()

    body = rest[:budget].rstrip(" .,;:-")
    return f"{body}{suffix}"


def cmd_fill(args: argparse.Namespace) -> int:
    note = fill_add_note(
        args.template,
        position=args.position,
        company=args.company,
        link=args.link,
    )
    print(note)
    return 0


def cmd_write_templates(args: argparse.Namespace) -> int:
    from sheets_write import sheets_service, write_range
    from sheet_config import get_spreadsheet_id, get_tab

    service = sheets_service()
    sid = get_spreadsheet_id()
    tab = get_tab()
    values = [[t] for t in DEFAULT_TEMPLATES]
    result = write_range(service, sid, tab, "Q2:Q7", values)
    print(
        json.dumps(
            {
                "updatedRange": result.get("updatedRange"),
                "templates": DEFAULT_TEMPLATES,
                "max_filled_note_chars": MAX_FILLED_NOTE_CHARS,
            },
            indent=2,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="LeadGru add-note fill (≤ 200 chars)")
    sub = p.add_subparsers(dest="cmd", required=True)

    fill_p = sub.add_parser("fill", help="Print filled note for one row")
    fill_p.add_argument("--template", required=True)
    fill_p.add_argument("--position", required=True)
    fill_p.add_argument("--company", required=True)
    fill_p.add_argument("--link", required=True)
    fill_p.set_defaults(func=cmd_fill)

    write_p = sub.add_parser("write-templates", help="Write Q2:Q7 (does not change column H)")
    write_p.set_defaults(func=cmd_write_templates)
    return p


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
