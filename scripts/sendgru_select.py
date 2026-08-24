#!/usr/bin/env python3
"""SendGru row selection: applied rows, first 2 /in/ URLs, note length check."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field

MAX_NOTE_CHARS = 300  # LinkedIn desktop Premium connection-note limit
MAX_PEOPLE_PER_ROW = 2
MAX_SENDS_PER_DAY = 20
SENT_MARKER = "Sent add note"
APPLIED_STATUS = "applied"

IN_RE = re.compile(r"https?://(?:[\w.-]+\.)?linkedin\.com/in/[^\s/]+/?", re.I)


@dataclass
class PersonTarget:
    url: str
    name: str = ""
    title: str = ""


@dataclass
class RowTarget:
    row: int
    company: str
    position: str
    status: str
    note: str
    people: list[PersonTarget] = field(default_factory=list)
    skip_reason: str = ""


def parse_row_spec(spec: str) -> list[int]:
    """Parse '4-12', '4,6,9', '8', 'row 8'."""
    spec = spec.strip().lower().replace("rows", "").replace("row", "").strip()
    if not spec:
        return []
    out: list[int] = []
    for part in re.split(r"[\s,]+", spec):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            lo, hi = int(a), int(b)
            if lo > hi:
                lo, hi = hi, lo
            out.extend(range(lo, hi + 1))
        else:
            out.append(int(part))
    return sorted(set(out))


def parse_leads_people(leads_text: str, limit: int = MAX_PEOPLE_PER_ROW) -> list[PersonTarget]:
    """First N /in/ profiles from column G (skip Company: lines)."""
    if not leads_text or not leads_text.strip():
        return []
    seen: set[str] = set()
    people: list[PersonTarget] = []
    for line in leads_text.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("company:"):
            continue
        m = IN_RE.search(line)
        if not m:
            continue
        url = m.group(0).rstrip("/") + "/"
        if url in seen:
            continue
        seen.add(url)
        parts = [p.strip() for p in line.split("—")]
        name = parts[0] if parts else ""
        title = parts[1] if len(parts) > 1 else ""
        people.append(PersonTarget(url=url, name=name, title=title))
        if len(people) >= limit:
            break
    return people


def note_length_ok(note: str) -> tuple[bool, str]:
    n = len(note or "")
    if n == 0:
        return False, "empty note"
    if n > MAX_NOTE_CHARS:
        return False, f"note too long ({n} chars, max {MAX_NOTE_CHARS})"
    return True, ""


def is_sent_marker(note: str) -> bool:
    """True if column H already contains the sent marker (exact or appended)."""
    return SENT_MARKER.lower() in (note or "").lower()


def append_sent_marker(note: str) -> str:
    """Keep the original note and append the marker in the same cell."""
    text = (note or "").rstrip()
    if is_sent_marker(text):
        return text
    if not text:
        return SENT_MARKER
    return f"{text} {SENT_MARKER}"


def is_applied_status(status: str) -> bool:
    return (status or "").strip().lower() == APPLIED_STATUS


def evaluate_row(
    row_num: int,
    cells: list[str],
) -> RowTarget:
    """cells: [A, B, C, D, E, F, G, H] or shorter."""
    pad = (cells + [""] * 8)[:8]
    company, position, _apply, status, _date, _details, leads, note = pad
    target = RowTarget(
        row=row_num,
        company=company,
        position=position,
        status=status,
        note=note,
    )
    if not is_applied_status(status):
        target.skip_reason = f"status is '{status}' (need '{APPLIED_STATUS}')"
        return target
    if is_sent_marker(note):
        target.skip_reason = "already Sent add note"
        return target
    ok, reason = note_length_ok(note)
    if not ok:
        target.skip_reason = reason
        return target
    people = parse_leads_people(leads)
    if not people:
        target.skip_reason = "no /in/ URLs in Leads"
        return target
    target.people = people
    return target


def select_from_sheet_rows(
    row_numbers: list[int],
    sheet_rows: dict[int, list[str]],
) -> tuple[list[RowTarget], list[RowTarget]]:
    """Return (actionable, skipped)."""
    actionable: list[RowTarget] = []
    skipped: list[RowTarget] = []
    for rn in row_numbers:
        cells = sheet_rows.get(rn)
        if cells is None:
            skipped.append(
                RowTarget(
                    row=rn,
                    company="",
                    position="",
                    status="",
                    note="",
                    skip_reason="row not in sheet read",
                )
            )
            continue
        t = evaluate_row(rn, cells)
        if t.skip_reason:
            skipped.append(t)
        else:
            actionable.append(t)
    return actionable, skipped


def total_send_count(actionable: list[RowTarget]) -> int:
    return sum(len(r.people) for r in actionable)


def apply_daily_cap(
    actionable: list[RowTarget],
    max_sends: int = MAX_SENDS_PER_DAY,
) -> tuple[list[RowTarget], list[RowTarget]]:
    """Trim actionable list to max_sends people total; rest go to capped list."""
    kept: list[RowTarget] = []
    capped: list[RowTarget] = []
    count = 0
    for row in actionable:
        if count >= max_sends:
            capped.append(
                RowTarget(
                    row=row.row,
                    company=row.company,
                    position=row.position,
                    status=row.status,
                    note=row.note,
                    skip_reason=f"daily cap ({max_sends} sends)",
                )
            )
            continue
        slots = max_sends - count
        if len(row.people) <= slots:
            kept.append(row)
            count += len(row.people)
        else:
            partial = RowTarget(
                row=row.row,
                company=row.company,
                position=row.position,
                status=row.status,
                note=row.note,
                people=row.people[:slots],
            )
            kept.append(partial)
            count += len(partial.people)
            if len(row.people) > slots:
                capped.append(
                    RowTarget(
                        row=row.row,
                        company=row.company,
                        position=row.position,
                        status=row.status,
                        note=row.note,
                        people=row.people[slots:],
                        skip_reason=f"daily cap ({max_sends} sends)",
                    )
                )
    return kept, capped


def row_to_json(row: RowTarget) -> dict:
    d = asdict(row)
    d["people"] = [asdict(p) for p in row.people]
    return d


def cmd_mark_sent(args: argparse.Namespace) -> int:
    """Read H for each row and append SENT_MARKER without replacing the note."""
    row_nums = parse_row_spec(args.rows)
    if not row_nums:
        print("No rows parsed from --rows", file=sys.stderr)
        return 1
    from sheets_write import read_range, sheets_service, write_range
    from sheet_config import get_spreadsheet_id, get_tab

    service = sheets_service()
    sid = get_spreadsheet_id()
    tab = get_tab()
    marked = []
    for rn in row_nums:
        values = read_range(service, sid, tab, f"H{rn}")
        current = values[0][0] if values and values[0] else ""
        updated = append_sent_marker(current)
        if updated != current:
            write_range(service, sid, tab, f"H{rn}", [[updated]])
        marked.append({"row": rn, "before": current, "after": updated})
    print(json.dumps({"marked": marked, "sent_marker": SENT_MARKER}, indent=2))
    return 0


def cmd_select(args: argparse.Namespace) -> int:
    row_nums = parse_row_spec(args.rows)
    if not row_nums:
        print("No rows parsed from --rows", file=sys.stderr)
        return 1
    lo, hi = min(row_nums), max(row_nums)
    from sheets_write import read_range, sheets_service
    from sheet_config import get_spreadsheet_id, get_tab

    service = sheets_service()
    sid = get_spreadsheet_id()
    tab = get_tab()
    values = read_range(service, sid, tab, f"A{lo}:H{hi}")
    sheet_rows: dict[int, list[str]] = {}
    for i, cells in enumerate(values):
        sheet_rows[lo + i] = cells
    actionable, skipped = select_from_sheet_rows(row_nums, sheet_rows)
    if args.apply_daily_cap:
        actionable, extra = apply_daily_cap(actionable, args.max_sends)
        skipped.extend(extra)
    payload = {
        "rows_requested": row_nums,
        "actionable": [row_to_json(r) for r in actionable],
        "skipped": [row_to_json(r) for r in skipped],
        "total_sends_planned": total_send_count(actionable),
        "max_note_chars": MAX_NOTE_CHARS,
        "max_people_per_row": MAX_PEOPLE_PER_ROW,
        "sent_marker": SENT_MARKER,
    }
    print(json.dumps(payload, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="SendGru row selection for LinkedIn add-note send")
    p.add_argument("--rows", required=True, help='Row spec: "4-12", "4,6,9", "8"')
    p.add_argument(
        "--apply-daily-cap",
        action="store_true",
        help=f"Trim to {MAX_SENDS_PER_DAY} sends per run",
    )
    p.add_argument(
        "--max-sends",
        type=int,
        default=MAX_SENDS_PER_DAY,
        help="Max connection sends this run",
    )
    p.add_argument(
        "--mark-sent",
        action="store_true",
        help=f'Append "{SENT_MARKER}" to column H for --rows (do not replace the note)',
    )
    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.mark_sent:
        return cmd_mark_sent(args)
    return cmd_select(args)


if __name__ == "__main__":
    raise SystemExit(main())
