# Jobgru Windows installer bootstrapper
# Usage (PowerShell or CMD):
#   irm https://raw.githubusercontent.com/ashujha301/jobgru/main/install.ps1 | iex
#
# Delegates to install.sh inside WSL (Linux). Mac/Linux users should use curl | bash instead.

$ErrorActionPreference = "Stop"

$JobgruRepo = "https://github.com/ashujha301/jobgru.git"
$InstallShUrl = "https://raw.githubusercontent.com/ashujha301/jobgru/main/install.sh"
$IrmCommand = "irm https://raw.githubusercontent.com/ashujha301/jobgru/main/install.ps1 | iex"

function Write-JobgruHeader {
    Write-Host ""
    Write-Host "Jobgru install (Windows)" -ForegroundColor Cyan
    Write-Host "========================" -ForegroundColor Cyan
    Write-Host ""
}

function Test-WslInstalled {
    if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
        return $false
    }
    try {
        $list = & wsl.exe -l -q 2>$null
        if ($LASTEXITCODE -ne 0) {
            return $false
        }
        $distros = @($list | Where-Object { $_.Trim() -ne "" })
        return $distros.Count -gt 0
    } catch {
        return $false
    }
}

function Invoke-JobgruInWsl {
    Write-Host "==> WSL detected — running the Linux installer inside WSL..." -ForegroundColor Green
    Write-Host ""
    Write-Host "The setup wizard will run in WSL (gcloud, sheet URL, LinkedIn login)."
    Write-Host "Use the same Google account and paste your sheet copy URL when asked."
    Write-Host ""

    $bashCmd = @(
        "set -e"
        "export JOBGRU_REPO='$JobgruRepo'"
        "if ! command -v curl >/dev/null 2>&1; then"
        "  echo 'Installing curl in WSL...'"
        "  sudo apt-get update -qq && sudo apt-get install -y curl"
        "fi"
        "curl -fsSL '$InstallShUrl' | bash"
    ) -join "; "

    & wsl.exe bash -lc $bashCmd
    $code = $LASTEXITCODE
    Write-Host ""
    if ($code -eq 0) {
        Write-Host "OK: Jobgru installed in WSL (~/.jobgru inside Linux)." -ForegroundColor Green
        Write-Host ""
        Write-Host "Run Jobgru from WSL or Git Bash:"
        Write-Host "  wsl jobgru check"
        Write-Host "  wsl jobgru prompts"
        Write-Host ""
        Write-Host "Codex/Claude on Windows: use WSL terminal for jobgru CLI, or run agents from WSL."
    } else {
        Write-Host "Install exited with code $code. Fix errors above and re-run:" -ForegroundColor Yellow
        Write-Host "  $IrmCommand"
    }
    exit $code
}

function Offer-WslInstall {
    Write-Host "WSL (Windows Subsystem for Linux) is not set up yet." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Jobgru needs bash + Linux tools. Recommended: install WSL (one time)."
    Write-Host ""
    Write-Host "This runs: wsl --install (may need Administrator PowerShell + reboot)."
    Write-Host ""

    $reply = Read-Host "Install WSL now? [y/N]"
    if ($reply -notmatch '^[yY]$') {
        Write-ManualFallback
        exit 0
    }

    Write-Host ""
    Write-Host "==> Running: wsl --install" -ForegroundColor Cyan
    Write-Host "(If this fails, open PowerShell as Administrator and run: wsl --install)"
    Write-Host ""

    try {
        & wsl.exe --install
    } catch {
        Write-Host "Could not run wsl --install: $_" -ForegroundColor Red
        Write-ManualFallback
        exit 1
    }

    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Green
    Write-Host "  1. Reboot Windows if prompted"
    Write-Host "  2. Open Ubuntu from Start menu once (finish Linux user setup)"
    Write-Host "  3. Open PowerShell again and run:"
    Write-Host "       $IrmCommand"
    Write-Host ""
    exit 0
}

function Write-ManualFallback {
    Write-Host ""
    Write-Host "Manual options:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  A) WSL (recommended) — Admin PowerShell:"
    Write-Host "       wsl --install"
    Write-Host "     Reboot, open Ubuntu once, then:"
    Write-Host "       $IrmCommand"
    Write-Host ""
    Write-Host "  B) Mac/Linux-style (inside WSL or Git Bash after WSL setup):"
    Write-Host "       curl -fsSL $InstallShUrl | bash"
    Write-Host ""
    Write-Host "  Note: Plain Git Bash without WSL is not fully supported yet (Python venv paths)."
    Write-Host ""
}

# --- Main ---
if ($PSVersionTable.PSVersion.Major -lt 5) {
    Write-Host "PowerShell 5+ required." -ForegroundColor Red
    exit 1
}

Write-JobgruHeader

if (Test-WslInstalled) {
    Invoke-JobgruInWsl
} else {
    Offer-WslInstall
}
