#!/usr/bin/env bash
# Jobgru global installer — idempotent interactive wizard.
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/ashujha301/jobgru/main/install.sh | bash
#   ./install.sh --local /path/to/jobgru-repo
#   ./install.sh --local . --skip-setup   # engine only, no wizard

set -euo pipefail

JOBGRU_HOME="${JOBGRU_HOME:-$HOME/.jobgru}"
JOBGRU_REPO="${JOBGRU_REPO:-https://github.com/ashujha301/jobgru.git}"
LOCAL_SOURCE=""
SKIP_MCP=0
SKIP_SETUP=0

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
    --skip-setup)
      SKIP_SETUP=1
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

PY=""
SCRIPTS=""

echo "==> Jobgru install (HOME=$JOBGRU_HOME)"

is_ci() {
  [[ "${CI:-}" == "true" || "${GITHUB_ACTIONS:-}" == "true" ]]
}

has_tty() {
  # curl | bash pipes stdin (not a tty) — prompts use /dev/tty instead
  [[ -e /dev/tty ]] && { : >/dev/tty; } 2>/dev/null
}

read_tty() {
  # Usage: read_tty "prompt" varname
  local prompt="$1"
  local __var="$2"
  local value=""
  if has_tty; then
    printf "%s" "$prompt" > /dev/tty 2>/dev/null || true
    IFS= read -r value < /dev/tty 2>/dev/null || true
  fi
  printf -v "$__var" '%s' "$value"
}

prompt_yn() {
  # Usage: prompt_yn "Question? [Y/n]" default_y|default_n
  local prompt="$1"
  local default="${2:-y}"
  local ans=""
  if ! has_tty; then
    return 1
  fi
  read_tty "$prompt " ans
  ans="${ans:-}"
  if [[ -z "$ans" ]]; then
    [[ "$default" == "y" ]]
    return
  fi
  [[ "$ans" == "y" || "$ans" == "Y" ]]
}

open_browser() {
  local url="$1"
  local os
  os="$(uname -s)"
  if [[ "$os" == "Darwin" ]] && command -v open >/dev/null 2>&1; then
    open "$url" >/dev/null 2>&1 || true
  elif [[ "$os" == MINGW* || "$os" == MSYS* || "$os" == CYGWIN* ]]; then
    # Git Bash / Cygwin on Windows
    start "" "$url" >/dev/null 2>&1 || cmd.exe /c start "" "$url" >/dev/null 2>&1 || \
      echo "Open this URL in your browser: $url"
  elif grep -qi microsoft /proc/version 2>/dev/null; then
    # WSL
    if command -v wslview >/dev/null 2>&1; then
      wslview "$url" >/dev/null 2>&1 || true
    else
      powershell.exe -NoProfile -Command "Start-Process '$url'" >/dev/null 2>&1 || \
        echo "Open this URL in your browser: $url"
    fi
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1 || true
  else
    echo "Open this URL in your browser: $url"
  fi
}

template_url() {
  PYTHONPATH="$SCRIPTS" "$PY" -c "from sheet_config import get_template_sheet_url; print(get_template_sheet_url())"
}

template_id() {
  PYTHONPATH="$SCRIPTS" "$PY" -c "from sheet_config import get_template_sheet_url, parse_spreadsheet_id; print(parse_spreadsheet_id(get_template_sheet_url()))"
}

gcloud_adc_ok() {
  command -v gcloud >/dev/null 2>&1 && gcloud auth application-default print-access-token >/dev/null 2>&1
}

install_engine() {
  if [[ -n "$LOCAL_SOURCE" ]]; then
    echo "==> Syncing from local path: $LOCAL_SOURCE"
    mkdir -p "$JOBGRU_HOME"
    if command -v rsync >/dev/null 2>&1; then
      rsync -a --delete \
        --exclude '.venv' \
        --exclude '.git' \
        --exclude 'config/sheet.json' \
        --exclude 'data/runs/*.json' \
        --exclude 'data/resumes/*.pdf' \
        --exclude '__pycache__' \
        "$LOCAL_SOURCE/" "$JOBGRU_HOME/"
    else
      # rsync missing (e.g. Git Bash on Windows) — fall back to tar copy
      echo "NOTE: rsync not found — using tar copy (config/data preserved)"
      (cd "$LOCAL_SOURCE" && tar -cf - \
        --exclude '.venv' \
        --exclude '.git' \
        --exclude 'config/sheet.json' \
        --exclude 'data/runs' \
        --exclude 'data/resumes' \
        --exclude '__pycache__' \
        .) | (cd "$JOBGRU_HOME" && tar -xf -)
    fi
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
  PY="$JOBGRU_HOME/.venv/bin/python"
  SCRIPTS="$JOBGRU_HOME/scripts"
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
  local os
  os="$(uname -s)"
  if [[ "$os" == MINGW* || "$os" == MSYS* || "$os" == CYGWIN* ]]; then
    # Git Bash "symlinks" are copies that go stale — install a tiny wrapper instead
    printf '#!/usr/bin/env bash\nexec "%s/bin/jobgru" "$@"\n' "$JOBGRU_HOME" > "$HOME/.local/bin/jobgru"
    chmod +x "$HOME/.local/bin/jobgru"
  else
    ln -sf "$JOBGRU_HOME/bin/jobgru" "$HOME/.local/bin/jobgru"
  fi
  echo "==> Linked jobgru → ~/.local/bin/jobgru"
  case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) echo "NOTE: Add to PATH: export PATH=\"\$HOME/.local/bin:\$PATH\"" ;;
  esac
}

register_mcp() {
  [[ "$SKIP_MCP" -eq 1 ]] && return
  local profile="$JOBGRU_HOME/browser-profile"
  mkdir -p "$profile"
  if command -v claude >/dev/null 2>&1; then
    if claude mcp list 2>/dev/null | grep -q playwright; then
      echo "==> Playwright MCP already registered (claude)"
    else
      echo "==> Registering Playwright MCP (claude)"
      claude mcp add playwright -- npx @playwright/mcp@latest --user-data-dir "$profile" || echo "WARN: claude mcp add failed" >&2
    fi
  fi
  if command -v codex >/dev/null 2>&1; then
    if codex mcp list 2>/dev/null | grep -q playwright; then
      echo "==> Playwright MCP already registered (codex)"
    else
      echo "==> Registering Playwright MCP (codex)"
      codex mcp add playwright -- npx @playwright/mcp@latest --user-data-dir "$profile" || echo "WARN: codex mcp add failed" >&2
    fi
  fi
}

setup_gcloud() {
  echo ""
  echo "═══════════════════════════════════════"
  echo " Step: Google Cloud SDK (Sheets access)"
  echo "═══════════════════════════════════════"
  echo ""

  if ! command -v gcloud >/dev/null 2>&1; then
    echo "Google Cloud SDK (gcloud) is not installed."
    echo "Jobgru needs it to read and write your Google Sheet."
    echo ""
    local os
    os="$(uname -s)"
    if [[ "$os" == "Darwin" ]] && command -v brew >/dev/null 2>&1; then
      if prompt_yn "Install Google Cloud SDK via Homebrew now? [y/N]" n; then
        echo "==> Installing google-cloud-sdk (this may take a few minutes)..."
        brew install --cask google-cloud-sdk || echo "WARN: brew install failed — install manually" >&2
      else
        echo "Install manually: https://cloud.google.com/sdk/docs/install"
      fi
    elif [[ "$os" == MINGW* || "$os" == MSYS* || "$os" == CYGWIN* ]]; then
      echo "Windows: download the installer from https://cloud.google.com/sdk/docs/install"
      echo "(run GoogleCloudSDKInstaller.exe, then reopen Git Bash so gcloud is on PATH)"
    else
      echo "Install from: https://cloud.google.com/sdk/docs/install"
    fi

    if ! command -v gcloud >/dev/null 2>&1; then
      if has_tty; then
        echo ""
        local wait_input=""
        read_tty "Press ENTER when gcloud is installed (or type 'skip' to finish setup later): " wait_input
        if [[ "$(echo "$wait_input" | tr '[:upper:]' '[:lower:]')" == "skip" ]]; then
          echo "Skipped gcloud setup. Run later: gcloud auth login --enable-gdrive-access --update-adc"
          return
        fi
      fi
    fi
  fi

  if ! command -v gcloud >/dev/null 2>&1; then
    echo "WARN: gcloud still not found — skip sheet verification for now."
    echo "After installing gcloud, run: gcloud auth login --enable-gdrive-access --update-adc"
    return
  fi

  echo "gcloud found: $(command -v gcloud)"

  if gcloud_adc_ok; then
    echo "Google auth already active (application-default credentials OK)."
    return
  fi

  echo ""
  echo "Sign in with the Google account that OWNS your sheet copy."
  echo "Command: gcloud auth login --enable-gdrive-access --update-adc"
  echo ""

  if prompt_yn "Sign into Google now? [Y/n]" y; then
    echo "==> Opening Google sign-in in your browser..."
    if has_tty; then
      gcloud auth login --enable-gdrive-access --update-adc < /dev/tty || {
        echo "WARN: gcloud auth did not complete — you can retry later."
        return
      }
    else
      gcloud auth login --enable-gdrive-access --update-adc || true
    fi
    if gcloud_adc_ok; then
      echo "OK: Google auth configured."
    else
      echo "WARN: Auth may not be complete. Retry: gcloud auth login --enable-gdrive-access --update-adc"
    fi
  else
    echo "Skipped. Run before your first job search:"
    echo "  gcloud auth login --enable-gdrive-access --update-adc"
  fi
}

setup_sheet() {
  echo ""
  echo "═══════════════════════════════════════"
  echo " Step: Google Sheet setup"
  echo "═══════════════════════════════════════"
  echo ""
  echo "1. Open the Jobgru template (read-only — you copy from it)"
  echo "2. File → Make a copy → save to your Google Drive"
  echo "3. Tab name must stay: Job Applications"
  echo "4. Paste YOUR copy's URL below (not the template URL)"
  echo ""

  local tpl_url tpl_id
  tpl_url="$(template_url)"
  tpl_id="$(template_id)"
  echo "Template: $tpl_url"
  echo ""

  if prompt_yn "Open the template in your browser now? [Y/n]" y; then
    echo "==> Opening template in browser..."
    open_browser "$tpl_url"
    echo "In Google Sheets: File → Make a copy, then come back here."
  fi

  if ! has_tty; then
    echo "No interactive terminal — finish sheet setup later:"
    echo "  jobgru setup --url \"YOUR_COPY_URL\""
    return
  fi

  local attempt=0
  local max_attempts=3
  local pasted=""

  while [[ $attempt -lt $max_attempts ]]; do
    echo ""
    read_tty "Paste YOUR sheet copy URL (or 'skip' to finish later): " pasted
    pasted="$(echo "$pasted" | tr -d '[:space:]')"

    if [[ -z "$pasted" ]]; then
      echo "No URL entered."
      ((attempt++)) || true
      continue
    fi

    if [[ "$(echo "$pasted" | tr '[:upper:]' '[:lower:]')" == "skip" ]]; then
      echo "Skipped sheet setup. Finish later:"
      echo "  jobgru setup --url \"YOUR_COPY_URL\""
      return
    fi

    # Reject template URL
    local pasted_id=""
    pasted_id="$(PYTHONPATH="$SCRIPTS" "$PY" -c "
from sheet_config import parse_spreadsheet_id
import sys
try:
    print(parse_spreadsheet_id(sys.argv[1]))
except Exception:
    print('INVALID')
" "$pasted" 2>/dev/null || echo "INVALID")"

    if [[ "$pasted_id" == "INVALID" ]]; then
      echo "Could not parse that URL. Paste a full Google Sheets link."
      ((attempt++)) || true
      continue
    fi

    if [[ "$pasted_id" == "$tpl_id" ]]; then
      echo ""
      echo "That is the read-only TEMPLATE — Jobgru cannot write to it."
      echo "Use File → Make a copy in Google Sheets, then paste YOUR copy's URL."
      ((attempt++)) || true
      continue
    fi

    echo "==> Saving sheet config..."
    if ! "$PY" "$SCRIPTS/sheet_config.py" set --url "$pasted"; then
      echo "Failed to save config."
      ((attempt++)) || true
      continue
    fi

    echo "==> Verifying sheet (tab, headers, formulas, write test)..."
    if "$PY" "$SCRIPTS/jobgru_verify_sheet.py"; then
      echo ""
      echo "OK: Sheet configured and verified."
      return
    fi

    echo ""
    echo "Sheet verification failed (see message above)."
    if ! gcloud_adc_ok; then
      echo "Tip: run gcloud auth first, then paste your sheet URL again."
    fi
    ((attempt++)) || true
  done

  echo ""
  echo "Sheet setup not completed after $max_attempts attempts."
  echo "Finish manually: jobgru setup --url \"YOUR_COPY_URL\""
}

offer_linkedin_login() {
  [[ "$SKIP_MCP" -eq 1 ]] && return
  command -v claude >/dev/null 2>&1 || command -v codex >/dev/null 2>&1 || return 0

  echo ""
  echo "═══════════════════════════════════════"
  echo " Step: LinkedIn login (LeadGru contacts)"
  echo "═══════════════════════════════════════"
  echo ""
  echo "LeadGru finds LinkedIn hiring contacts. One login is saved and reused."
  echo "Profile: $JOBGRU_HOME/browser-profile"
  echo "Cursor users: skip this — sign into LinkedIn in Cursor Browser instead."
  echo ""

  if ! has_tty; then
    echo "NOTE: Run 'jobgru mcp login' once to sign into LinkedIn (needed for LeadGru)."
    return 0
  fi

  if ! prompt_yn "Sign into LinkedIn now? Browser opens; press ENTER in terminal when done. [y/N]" n; then
    echo "Skipped. Run before LeadGru: jobgru mcp login"
    return 0
  fi

  local attempt=0
  local max_attempts=3
  while [[ $attempt -lt $max_attempts ]]; do
    if "$PY" "$SCRIPTS/jobgru_mcp.py" login; then
      echo "OK: LinkedIn login verified."
      return 0
    fi
    echo ""
    echo "LinkedIn login was not detected (browser closed early or sign-in incomplete)."
    if prompt_yn "Try LinkedIn login again? [Y/n]" y; then
      attempt=$((attempt + 1))
      continue
    fi
    echo "Skipped. Run before LeadGru: jobgru mcp login"
    return 0
  done

  echo "LinkedIn login not completed after $max_attempts attempts."
  echo "Run later: jobgru mcp login"
}

run_final_check() {
  echo ""
  echo "═══════════════════════════════════════"
  echo " Final check"
  echo "═══════════════════════════════════════"
  echo ""
  if command -v jobgru >/dev/null 2>&1 || [[ -x "$HOME/.local/bin/jobgru" ]]; then
    "$PY" "$SCRIPTS/jobgru_check.py" || true
  else
    "$PY" "$SCRIPTS/jobgru_check.py" || true
  fi
}

print_next_steps() {
  echo ""
  echo "Jobgru installed to $JOBGRU_HOME"
  echo ""
  echo "Optional (for ATS resume scoring):"
  echo "  cp your-resume.pdf $JOBGRU_HOME/data/resumes/"
  echo "  Or in chat: Jobgru add resume"
  echo ""
  echo "Run your first job search (any agent):"
  echo "  jobgru prompts    # copy example, edit filters, paste into chat"
  echo "  jobgru filter     # see all filter types"
  echo ""
  echo "Commands: jobgru help · jobgru check · jobgru update"
}

print_manual_setup() {
  echo ""
  echo "Non-interactive install — finish setup manually:"
  echo "  1. Copy template → File → Make a copy (tab: Job Applications)"
  echo "     $(template_url 2>/dev/null || echo 'https://docs.google.com/spreadsheets/d/18TQRl1dh0Ivdk8YbxkdiWb6__XkpHM32T1ohPTuMJ_4/edit')"
  echo "  2. gcloud auth login --enable-gdrive-access --update-adc"
  echo "  3. jobgru setup --url \"YOUR_COPY_URL\""
  echo "  4. jobgru mcp login   (Codex/Claude — LinkedIn for LeadGru)"
  echo "  5. jobgru check"
}

# ── Main install ──────────────────────────────────────────────────────────────

install_engine
install_venv
install_router_skills
install_path_command
register_mcp

echo ""
echo "Jobgru engine installed to $JOBGRU_HOME"
echo ""

if [[ "$SKIP_SETUP" -eq 1 ]]; then
  print_manual_setup
  exit 0
fi

if is_ci; then
  echo "CI environment detected — engine installed. Use --skip-setup for automated installs."
  exit 0
fi

if ! has_tty; then
  echo ""
  echo "ERROR: No interactive terminal (cannot read /dev/tty)." >&2
  echo "Save and run the installer directly so the wizard can prompt you:" >&2
  echo "  curl -fsSL https://raw.githubusercontent.com/ashujha301/jobgru/main/install.sh -o install.sh" >&2
  echo "  bash install.sh" >&2
  echo ""
  echo "Or finish setup with: jobgru setup --url \"YOUR_COPY_URL\"" >&2
  exit 1
fi

echo "==> Starting interactive setup wizard"
setup_gcloud
setup_sheet
offer_linkedin_login
run_final_check
print_next_steps
