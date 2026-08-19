"""Resolve Jobgru engine home directory (~/.jobgru global install or repo checkout)."""

from __future__ import annotations

import os
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
_GLOBAL_HOME = Path.home() / ".jobgru"


def get_jobgru_home() -> Path:
    """Return JOBGRU_HOME: env var, else ~/.jobgru if installed, else repo root."""
    env = os.environ.get("JOBGRU_HOME")
    if env:
        return Path(env).expanduser().resolve()
    if (_GLOBAL_HOME / "scripts" / "jobgru_check.py").is_file():
        return _GLOBAL_HOME.resolve()
    if (_GLOBAL_HOME / "scripts" / "sheets_write.py").is_file():
        return _GLOBAL_HOME.resolve()
    return _REPO_ROOT.resolve()


def get_install_mode() -> str:
    home = get_jobgru_home()
    if home == _GLOBAL_HOME.resolve() and _GLOBAL_HOME.is_dir():
        return "global"
    if home == _REPO_ROOT.resolve():
        return "repo"
    return "custom"


def venv_python(home: Path | None = None) -> Path:
    root = home or get_jobgru_home()
    candidate = root / ".venv" / "bin" / "python"
    if candidate.is_file():
        return candidate
    return Path(os.environ.get("JOBGRU_PYTHON", "python3"))
