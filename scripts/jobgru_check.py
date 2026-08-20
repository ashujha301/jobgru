#!/usr/bin/env python3
"""Jobgru environment and sheet readiness checks.

Usage:
  .venv/bin/python scripts/jobgru_check.py
  .venv/bin/python scripts/jobgru_check.py --json
  jobgru check   (after global install)
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from jobgru_home import get_install_mode, get_jobgru_home, venv_python  # noqa: E402
from sheet_config import (  # noqa: E402
    CONFIG_PATH,
    GCLOUD_AUTH_COMMAND,
    config_is_configured,
    get_spreadsheet_id,
    get_tab,
    get_template_sheet_url,
    load_sheet_config,
)
from sheet_validate import (  # noqa: E402
    sheet_has_tab,
    validate_headers,
    validate_status_dropdown,
    validate_summary_formulas,
)

PROJECT_ROOT = get_jobgru_home()
VENV_PYTHON = venv_python(PROJECT_ROOT)
RESUMES_DIR = PROJECT_ROOT / "data" / "resumes"


@dataclass
class CheckResult:
    id: str
    status: str  # pass | warn | fail
    message: str
    fix: str = ""
    fix_command: str = ""
    manual: bool = False
    readme_anchor: str = ""


@dataclass
class Report:
    ready: bool = False
    checks: list[CheckResult] = field(default_factory=list)

    def add(self, check: CheckResult) -> None:
        self.checks.append(check)

    def finalize(self) -> None:
        failures = [c for c in self.checks if c.status == "fail"]
        self.ready = not failures


def _python_version_ok() -> tuple[bool, str]:
    v = sys.version_info
    if v.major >= 3 and v.minor >= 10:
        return True, f"Python {v.major}.{v.minor}.{v.micro}"
    return False, f"Python {v.major}.{v.minor}.{v.micro} (need 3.10+)"


def check_install_mode(report: Report) -> None:
    mode = get_install_mode()
    home = str(PROJECT_ROOT)
    report.add(
        CheckResult(
            id="install_mode",
            status="pass",
            message=f"install_mode={mode}, JOBGRU_HOME={home}",
        )
    )


def check_python(report: Report) -> None:
    ok, detail = _python_version_ok()
    report.add(
        CheckResult(
            id="python",
            status="pass" if ok else "fail",
            message=detail,
            fix="Install Python 3.10+ from https://www.python.org/downloads/",
            readme_anchor="README.md#first-time-you-only-do-2-things",
        )
    )


def check_router_skills(report: Report) -> None:
    """Router skill must be installed for every agent present on this machine."""
    agents = [
        ("cursor", Path.home() / ".cursor"),
        ("claude", Path.home() / ".claude"),
        ("codex", Path.home() / ".codex"),
    ]
    installed: list[str] = []
    missing: list[str] = []
    for cli, agent_home in agents:
        present = agent_home.is_dir() or shutil.which(cli) is not None
        if not present:
            continue
        skill = agent_home / "skills" / "jobgru" / "SKILL.md"
        if skill.is_file():
            installed.append(cli)
        else:
            missing.append(cli)

    if missing:
        report.add(
            CheckResult(
                id="router_skills",
                status="fail",
                message=f"Router skill missing for: {', '.join(missing)}"
                + (f" (installed: {', '.join(installed)})" if installed else ""),
                fix="Run: jobgru update — reinstalls the skill for every detected agent",
                fix_command="jobgru update",
                readme_anchor="README.md#chat-commands",
            )
        )
    elif installed:
        report.add(
            CheckResult(
                id="router_skills",
                status="pass",
                message=f"Router skill installed for: {', '.join(installed)}",
            )
        )
    else:
        report.add(
            CheckResult(
                id="router_skills",
                status="warn",
                message="No agent detected (~/.cursor, ~/.claude, ~/.codex) — /jobgru chat command unavailable",
                fix="Install Cursor, Claude Code, or Codex, then run: jobgru update",
            )
        )


def check_venv(report: Report) -> None:
    exists = VENV_PYTHON.is_file()
    report.add(
        CheckResult(
            id="venv",
            status="pass" if exists else "fail",
            message=f".venv at {VENV_PYTHON.parent.parent}" if exists else ".venv missing",
            fix='Run: jobgru setup — or "Jobgru setup" in chat',
            fix_command="python3 -m venv .venv",
            readme_anchor="README.md#chat-commands",
        )
    )


def check_deps(report: Report) -> None:
    python = str(VENV_PYTHON if VENV_PYTHON.is_file() else sys.executable)
    req = PROJECT_ROOT / "scripts" / "requirements.txt"
    try:
        subprocess.run(
            [python, "-c", "import googleapiclient; import pypdf"],
            check=True,
            capture_output=True,
            cwd=PROJECT_ROOT,
        )
        report.add(CheckResult(id="deps", status="pass", message="Python dependencies installed"))
    except subprocess.CalledProcessError:
        report.add(
            CheckResult(
                id="deps",
                status="fail",
                message="Missing Python dependencies",
                fix='Run: jobgru setup — or pip install -r scripts/requirements.txt',
                fix_command=f"{python} -m pip install -r {req}",
            )
        )


def check_gcloud_cli(report: Report) -> None:
    gcloud = shutil.which("gcloud")
    if gcloud:
        report.add(CheckResult(id="gcloud_cli", status="pass", message=f"gcloud at {gcloud}"))
    else:
        report.add(
            CheckResult(
                id="gcloud_cli",
                status="fail",
                message="gcloud CLI not on PATH",
                fix="Install Google Cloud SDK: https://cloud.google.com/sdk/docs/install",
                fix_command=GCLOUD_AUTH_COMMAND,
                manual=True,
            )
        )


def check_config(report: Report) -> None:
    if config_is_configured():
        cfg = load_sheet_config()
        report.add(
            CheckResult(
                id="config",
                status="pass",
                message=f"{CONFIG_PATH} → {cfg.get('spreadsheet_id')}",
            )
        )
    else:
        report.add(
            CheckResult(
                id="config",
                status="fail",
                message="config/sheet.json missing or not configured",
                fix=(
                    f"Copy template ({get_template_sheet_url()}), "
                    "File → Make a copy, then: Jobgru setup with your sheet URL"
                ),
                manual=True,
            )
        )


def check_browser_tools(report: Report) -> None:
    from jobgru_mcp import agent_present, playwright_registered, status_payload

    data = status_payload()
    claude = data["agents"]["claude"]
    codex = data["agents"]["codex"]

    if claude["present"] and not claude["playwright_registered"]:
        report.add(
            CheckResult(
                id="browser_mcp_claude",
                status="warn",
                message="Claude Code: Playwright MCP not registered (LeadGru will skip)",
                fix="Run: jobgru mcp install",
                fix_command="jobgru mcp install",
                readme_anchor="docs/SETUP.md#browser-and-mcp",
            )
        )
    elif claude["present"]:
        report.add(
            CheckResult(
                id="browser_mcp_claude",
                status="pass",
                message="Claude Code: Playwright MCP registered",
            )
        )

    if codex["present"] and not codex["playwright_registered"]:
        report.add(
            CheckResult(
                id="browser_mcp_codex",
                status="warn",
                message="Codex: Playwright MCP not registered (LeadGru will skip)",
                fix="Run: jobgru mcp install",
                fix_command="jobgru mcp install",
                readme_anchor="docs/SETUP.md#browser-and-mcp",
            )
        )
    elif codex["present"]:
        report.add(
            CheckResult(
                id="browser_mcp_codex",
                status="pass",
                message="Codex: Playwright MCP registered",
            )
        )

    report.add(
        CheckResult(
            id="browser_tools",
            status="pass",
            message="Cursor: built-in browser. Claude/Codex: Playwright MCP (jobgru mcp install).",
            fix="jobgru mcp install — registers Playwright for Claude Code and Codex",
            fix_command="jobgru mcp install",
            readme_anchor="docs/SETUP.md#browser-and-mcp",
        )
    )


def _get_sheets_service():
    from sheets_write import sheets_service

    return sheets_service()


def check_sheet_tab(report: Report) -> None:
    if not config_is_configured():
        report.add(
            CheckResult(
                id="sheet_tab",
                status="fail",
                message="Skipped — config not set",
                fix="Complete Jobgru setup with your sheet URL",
                manual=True,
            )
        )
        return
    try:
        service = _get_sheets_service()
        tab = get_tab()
        if sheet_has_tab(service, get_spreadsheet_id(), tab):
            report.add(CheckResult(id="sheet_tab", status="pass", message=f'Tab "{tab}" exists'))
        else:
            report.add(
                CheckResult(
                    id="sheet_tab",
                    status="fail",
                    message=f'Tab "{tab}" not found',
                    fix=f'Rename tab to "{tab}" or recopy the Jobgru template',
                    manual=True,
                )
            )
    except Exception as exc:
        report.add(
            CheckResult(
                id="sheet_tab",
                status="fail",
                message=str(exc),
                fix_command=GCLOUD_AUTH_COMMAND,
                manual=True,
            )
        )


def check_sheet_headers(report: Report) -> None:
    if not config_is_configured():
        return
    try:
        service = _get_sheets_service()
        ok, issues = validate_headers(service, get_spreadsheet_id(), get_tab())
        report.add(
            CheckResult(
                id="sheet_headers",
                status="pass" if ok else "fail",
                message="Headers A1:J1 OK" if ok else "; ".join(issues),
                fix="Recopy the Jobgru template",
                manual=True,
            )
        )
    except Exception as exc:
        report.add(
            CheckResult(
                id="sheet_headers",
                status="fail",
                message=str(exc),
                fix_command=GCLOUD_AUTH_COMMAND,
                manual=True,
            )
        )


def check_sheet_formulas(report: Report) -> None:
    if not config_is_configured():
        return
    try:
        service = _get_sheets_service()
        ok, issues = validate_summary_formulas(service, get_spreadsheet_id(), get_tab())
        report.add(
            CheckResult(
                id="sheet_formulas",
                status="pass" if ok else "fail",
                message="Summary formulas M2:M7 OK" if ok else "; ".join(issues),
                fix="Recopy the Jobgru template",
                manual=True,
            )
        )
    except Exception as exc:
        report.add(
            CheckResult(
                id="sheet_formulas",
                status="fail",
                message=str(exc),
                fix_command=GCLOUD_AUTH_COMMAND,
                manual=True,
            )
        )


def check_sheet_dropdown(report: Report) -> None:
    if not config_is_configured():
        return
    try:
        service = _get_sheets_service()
        ok, issues = validate_status_dropdown(service, get_spreadsheet_id(), get_tab())
        report.add(
            CheckResult(
                id="sheet_dropdown",
                status="pass" if ok else "fail",
                message="Status dropdown D2 OK" if ok else "; ".join(issues),
                fix="Recopy the Jobgru template",
                manual=True,
            )
        )
    except Exception as exc:
        report.add(
            CheckResult(
                id="sheet_dropdown",
                status="fail",
                message=str(exc),
                fix_command=GCLOUD_AUTH_COMMAND,
                manual=True,
            )
        )


def check_sheet_auth(report: Report) -> None:
    if not config_is_configured():
        return
    try:
        from sheets_write import read_range

        service = _get_sheets_service()
        read_range(service, get_spreadsheet_id(), get_tab(), "A1")
        report.add(CheckResult(id="sheet_auth", status="pass", message="Sheets API read OK"))
    except SystemExit:
        report.add(
            CheckResult(
                id="sheet_auth",
                status="fail",
                message="Google Sheets auth failed",
                fix=f"Run: {GCLOUD_AUTH_COMMAND}",
                fix_command=GCLOUD_AUTH_COMMAND,
                manual=True,
            )
        )
    except Exception as exc:
        report.add(
            CheckResult(
                id="sheet_auth",
                status="fail",
                message=str(exc),
                fix_command=GCLOUD_AUTH_COMMAND,
                manual=True,
            )
        )


def check_sheet_write(report: Report) -> None:
    if not config_is_configured():
        return
    python = str(VENV_PYTHON if VENV_PYTHON.is_file() else sys.executable)
    try:
        subprocess.run(
            [python, str(SCRIPT_DIR / "sheets_write.py"), "test", "--cleanup"],
            check=True,
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        report.add(CheckResult(id="sheet_write", status="pass", message="Sheets API write verified"))
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or exc.stdout or "").strip()
        report.add(
            CheckResult(
                id="sheet_write",
                status="fail",
                message=err[:300] if err else "Sheets API write test failed",
                fix=f"Run: {GCLOUD_AUTH_COMMAND}",
                fix_command=GCLOUD_AUTH_COMMAND,
                manual=True,
            )
        )


def check_resume(report: Report) -> None:
    pdfs = list(RESUMES_DIR.glob("*.pdf")) if RESUMES_DIR.is_dir() else []
    if pdfs:
        report.add(
            CheckResult(
                id="resume",
                status="pass",
                message=f"Resume PDF(s): {', '.join(p.name for p in pdfs[:3])}",
            )
        )
    else:
        report.add(
            CheckResult(
                id="resume",
                status="warn",
                message="No resume PDF (ATS skipped)",
                fix='Jobgru setup with resume attachment, or drop PDF in data/resumes/',
            )
        )


def check_resume_manifest(report: Report) -> None:
    pdfs = list(RESUMES_DIR.glob("*.pdf")) if RESUMES_DIR.is_dir() else []
    if not pdfs:
        return
    python = str(VENV_PYTHON if VENV_PYTHON.is_file() else sys.executable)
    try:
        subprocess.run(
            [python, str(SCRIPT_DIR / "ats_score.py"), "sync"],
            check=True,
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        report.add(CheckResult(id="resume_manifest", status="pass", message="Resume manifest synced"))
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or exc.stdout or "").strip()
        report.add(
            CheckResult(
                id="resume_manifest",
                status="fail",
                message=err[:200] if err else "manifest sync failed",
                fix_command=f"{python} {SCRIPT_DIR / 'ats_score.py'} sync",
            )
        )


def run_all_checks() -> Report:
    try:
        from jobgru_runs import prune_old_runs

        prune_old_runs()
    except Exception:
        pass
    report = Report()
    check_install_mode(report)
    check_python(report)
    check_router_skills(report)
    check_venv(report)
    check_deps(report)
    check_gcloud_cli(report)
    check_config(report)
    check_browser_tools(report)
    check_sheet_tab(report)
    check_sheet_headers(report)
    check_sheet_formulas(report)
    check_sheet_dropdown(report)
    check_sheet_auth(report)
    check_sheet_write(report)
    check_resume(report)
    check_resume_manifest(report)
    report.finalize()
    return report


def format_human(report: Report) -> str:
    lines = ["Jobgru check", "=" * 40]
    icon = {"pass": "OK", "warn": "WARN", "fail": "FAIL"}
    for c in report.checks:
        lines.append(f"[{icon[c.status]}] {c.id}: {c.message}")
        if c.status != "pass" and c.fix:
            lines.append(f"     Fix: {c.fix}")
        if c.fix_command:
            lines.append(f"     Command: {c.fix_command}")
    lines.append("=" * 40)
    lines.append("READY" if report.ready else "NOT READY — fix FAIL items above")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Jobgru setup is complete")
    parser.add_argument("--json", action="store_true", help="Output JSON for agents")
    args = parser.parse_args()

    report = run_all_checks()
    if args.json:
        print(json.dumps({"ready": report.ready, "checks": [asdict(c) for c in report.checks]}, indent=2))
    else:
        print(format_human(report))

    return 0 if report.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
