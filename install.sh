#!/usr/bin/env bash
# Jobgru global installer — idempotent.
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/ashujha301/jobgru/main/install.sh | bash
#   ./install.sh --local /path/to/jobgru-repo

set -euo pipefail

JOBGRU_HOME="${JOBGRU_HOME:-$HOME/.jobgru}"
JOBGRU_REPO="${JOBGRU_REPO:-https://github.com/ashujha301/jobgru.git}"
LOCAL_SOURCE=""
SKIP_MCP=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --local)
      LOCAL_SOURCE="$2"
      shift 2
      ;;
    --skip-mcp)
      SKIP_MCP=1
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

echo "==> Jobgru install (HOME=$JOBGRU_HOME)"

install_engine() {
  if [[ -n "$LOCAL_SOURCE" ]]; then
    echo "==> Syncing from local path: $LOCAL_SOURCE"
    mkdir -p "$JOBGRU_HOME"
    rsync -a --delete \
      --exclude '.venv' \
      --exclude '.git' \
      --exclude 'config/sheet.json' \
      --exclude 'data/runs/*.json' \
      --exclude 'data/resumes/*.pdf' \
      --exclude '__pycache__' \
      "$LOCAL_SOURCE/" "$JOBGRU_HOME/"
  elif [[ -d "$JOBGRU_HOME/.git" ]]; then
    echo "==> Updating existing clone"
    git -C "$JOBGRU_HOME" pull --ff-only
  else
    echo "==> Cloning $JOBGRU_REPO"
    git clone "$JOBGRU_REPO" "$JOBGRU_HOME"
  fi
}

install_venv() {
  if [[ ! -d "$JOBGRU_HOME/.venv" ]]; then
    echo "==> Creating Python venv"
    python3 -m venv "$JOBGRU_HOME/.venv"
  fi
  echo "==> Installing Python dependencies"
  "$JOBGRU_HOME/.venv/bin/pip" install -q -r "$JOBGRU_HOME/scripts/requirements.txt"
}

install_router_skills() {
  local router="$JOBGRU_HOME/skill-global/jobgru/SKILL.md"
  if [[ ! -f "$router" ]]; then
    echo "WARN: Router skill not found at $router" >&2
    return
  fi
  for dir in "$HOME/.cursor/skills/jobgru" "$HOME/.claude/skills/jobgru" "$HOME/.codex/skills/jobgru"; do
    if [[ -d "$(dirname "$dir")" ]] || [[ "$dir" == *".cursor"* && -d "$HOME/.cursor" ]]; then
      mkdir -p "$dir"
      cp "$router" "$dir/SKILL.md"
      echo "==> Installed router skill: $dir/SKILL.md"
    fi
  done
}

install_path_command() {
  mkdir -p "$JOBGRU_HOME/bin"
  chmod +x "$JOBGRU_HOME/bin/jobgru"
  mkdir -p "$HOME/.local/bin"
  ln -sf "$JOBGRU_HOME/bin/jobgru" "$HOME/.local/bin/jobgru"
  echo "==> Linked jobgru → ~/.local/bin/jobgru"
  case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) echo "NOTE: Add to PATH: export PATH=\"\$HOME/.local/bin:\$PATH\"" ;;
  esac
}

register_mcp() {
  [[ "$SKIP_MCP" -eq 1 ]] && return
  if command -v claude >/dev/null 2>&1; then
    if claude mcp list 2>/dev/null | grep -q playwright; then
      echo "==> Playwright MCP already registered (claude)"
    else
      echo "==> Registering Playwright MCP (claude)"
      claude mcp add playwright -- npx @playwright/mcp@latest || echo "WARN: claude mcp add failed" >&2
    fi
  fi
  if command -v codex >/dev/null 2>&1; then
    if codex mcp list 2>/dev/null | grep -q playwright; then
      echo "==> Playwright MCP already registered (codex)"
    else
      echo "==> Registering Playwright MCP (codex)"
      codex mcp add playwright -- npx @playwright/mcp@latest || echo "WARN: codex mcp add failed" >&2
    fi
  fi
}

install_engine
install_venv
install_router_skills
install_path_command
register_mcp

echo ""
echo "Jobgru installed to $JOBGRU_HOME"
echo ""
echo "Next steps:"
echo "  1. Copy sheet template → File → Make a copy (tab: Job Applications)"
echo "     https://docs.google.com/spreadsheets/d/18TQRl1dh0Ivdk8YbxkdiWb6__XkpHM32T1ohPTuMJ_4/edit"
echo "  2. In any agent chat: Jobgru setup — my sheet: <URL>, my name: <NAME>"
echo "  3. Terminal (once): gcloud auth login --enable-gdrive-access --update-adc"
echo "  4. Browser for Claude/Codex (once): jobgru mcp install"
echo "  5. Resume for ATS: cp your-resume.pdf $JOBGRU_HOME/data/resumes/"
echo "  6. Verify: jobgru check   (or Jobgru check in Cursor/Claude/Codex)"
echo ""
echo "Commands: jobgru help"
echo "Update later: jobgru update"
