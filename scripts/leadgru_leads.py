#!/usr/bin/env python3
"""LeadGru column-G rules: hard cap of 5 people + company people page."""

from __future__ import annotations

import re

MAX_PEOPLE_PER_COMPANY = 5
IN_RE = re.compile(r"https?://(?:[\w.-]+\.)?linkedin\.com/in/[^\s/]+/?", re.I)
COMPANY_RE = re.compile(
    r"https?://(?:[\w.-]+\.)?linkedin\.com/company/[^\s]+",
    re.I,
)


def _normalize_in_url(url: str) -> str:
    m = IN_RE.search(url or "")
    if not m:
        return ""
    return m.group(0).rstrip("/") + "/"


def merge_leads(
    priority: list[tuple[str, str, str]],
    extra: list[tuple[str, str, str]],
    company_people_url: str,
) -> str:
    """Dedupe by /in/ URL; job-posting profiles first; cap at 5; append Company line."""
    seen: set[str] = set()
    merged: list[tuple[str, str, str]] = []
    for source in (priority, extra):
        for name, title, url in source:
            norm = _normalize_in_url(url)
            if not norm or norm in seen:
                continue
            seen.add(norm)
            merged.append((name.strip(), title.strip(), norm))
            if len(merged) >= MAX_PEOPLE_PER_COMPANY:
                break
        if len(merged) >= MAX_PEOPLE_PER_COMPANY:
            break
    return format_leads(merged, company_people_url)


def format_leads(
    people: list[tuple[str, str, str]],
    company_people_url: str,
) -> str:
    """Build Leads cell: at most 5 people, then a Company: people-page URL."""
    lines = [
        f"{name} — {title} — {url.rstrip('/')}/"
        for name, title, url in people[:MAX_PEOPLE_PER_COMPANY]
    ]
    handle = company_people_url.strip()
    if handle and not handle.lower().startswith("http"):
        handle = f"https://www.linkedin.com/company/{handle.strip('/')}/people/"
    if "/people" not in handle.rstrip("/").lower() and "/company/" in handle.lower():
        handle = handle.rstrip("/") + "/people/"
    lines.append(f"Company: {handle}")
    return "\n".join(lines)


def validate_leads_cell(text: str) -> list[str]:
    """Return error strings if the Leads cell violates the hard cap."""
    errors: list[str] = []
    people = IN_RE.findall(text or "")
    if len(people) > MAX_PEOPLE_PER_COMPANY:
        errors.append(
            f"too many /in/ links: {len(people)} (max {MAX_PEOPLE_PER_COMPANY})"
        )
    if not COMPANY_RE.search(text or ""):
        errors.append("missing Company: linkedin.com/company/... people page")
    return errors
