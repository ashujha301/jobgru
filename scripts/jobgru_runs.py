#!/usr/bin/env python3
"""Local run-log retention. Sheet data is never touched.

Run JSON under data/runs/ is a debug log, not the source of truth.
Default: delete *.json older than 6 days. Markdown notes are kept.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from jobgru_home import get_jobgru_home  # noqa: E402

RETENTION_DAYS = 6
RUNS_DIRNAME = "data/runs"


def runs_dir(home: Path | None = None) -> Path:
    return (home or get_jobgru_home()) / "data" / "runs"


def prune_old_runs(*, days: int = RETENTION_DAYS, dry_run: bool = False) -> dict:
    """Delete data/runs/*.json whose mtime is older than `days`. Keep .md and other files."""
    root = runs_dir()
    cutoff = time.time() - (max(1, days) * 86400)
    deleted: list[str] = []
    kept: list[str] = []

    if not root.is_dir():
        return {"deleted": [], "kept": [], "days": days, "dry_run": dry_run}

    for path in sorted(root.glob("*.json")):
        try:
            age_ok = path.stat().st_mtime >= cutoff
        except OSError:
            continue
        if age_ok:
            kept.append(path.name)
            continue
        deleted.append(path.name)
        if not dry_run:
            try:
                path.unlink()
            except OSError:
                deleted.pop()

    return {
        "deleted": deleted,
        "kept": kept,
        "days": days,
        "dry_run": dry_run,
        "dir": str(root),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prune old Jobgru run JSON logs")
    parser.add_argument("command", choices=["prune"], nargs="?", default="prune")
    parser.add_argument("--days", type=int, default=RETENTION_DAYS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = prune_old_runs(days=args.days, dry_run=args.dry_run)
    if args.json:
        print(json.dumps(result, indent=2))
    elif result["deleted"]:
        print(f"Pruned {len(result['deleted'])} run JSON(s) older than {args.days} days")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
