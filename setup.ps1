# setup.ps1 — Bootstrap for Windows
# oh-my-agents — OpenCode Multi-Agent Framework
#
# IMPORTANT: If you get an execution policy error, run PowerShell as Administrator
# and execute the following command once:
#   Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
#
# Alternatively, run this script with:
#   powershell -ExecutionPolicy Bypass -File setup.ps1

# Determine and switch to the script's own directory so relative paths resolve
# correctly no matter where the user launches the script from.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# ---------------------------------------------------------------------------
# Helper: find a working Python 3 (≥3.8) interpreter
# ---------------------------------------------------------------------------
function Find-Python {
    <#
    .SYNOPSIS
        Searches for a Python 3.8+ interpreter on the system.

    .DESCRIPTION
        Tries the following commands in order (first to succeed wins):
        1. py -3            (Windows Python Launcher — installed by python.org)
        2. python3          (common alias, e.g. from WSL or Chocolatey)
        3. python           (standard PATH entry)

    .OUTPUTS
        Returns the executable string on success; exits the script on failure.
    #>
    $candidates = @("py -3", "python3", "python")

    foreach ($cmd in $candidates) {
        $exe = ($cmd -split ' ')[0]
        $arg = ($cmd -split ' ')[1]
        $found = $false

        # Check if the executable exists on PATH
        try {
            $null = Get-Command $exe -ErrorAction Stop
        } catch {
            continue
        }

        # Try to get the version
        try {
            if ($arg) {
                $versionOutput = & $exe $arg --version 2>&1
            } else {
                $versionOutput = & $exe --version 2>&1
            }

            if ($versionOutput -match "Python (\d+)\.(\d+)") {
                $major = [int]$matches[1]
                $minor = [int]$matches[2]

                if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 8)) {
                    Write-Host "    Found $exe but version $major.$minor is too old (need 3.8+)." -ForegroundColor DarkYellow
                    continue
                }

                # Return the invocation string for later use
                if ($arg) {
                    return "$exe $arg"
                } else {
                    return $exe
                }
            }
        } catch {
            # This candidate failed; try the next one
            continue
        }
    }

    # Nothing found — fatal
    Write-Host "  ERROR: Python 3.8+ not found." -ForegroundColor Red
    Write-Host "  Install Python from https://python.org and make sure 'Add to PATH' is checked." -ForegroundColor Red
    Write-Host ""
    exit 1
}

# ---------------------------------------------------------------------------
# Handle -Uninstall flag
# ---------------------------------------------------------------------------
if ($args -contains "--uninstall" -or $args -contains "-Uninstall") {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  oh-my-agents — Uninstall" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    $PythonCmd = Find-Python
    & $PythonCmd main.py --uninstall
    exit $LASTEXITCODE
}

# ---------------------------------------------------------------------------
# Handle -Update flag
# ---------------------------------------------------------------------------
if ($args -contains "--update" -or $args -contains "-Update") {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  oh-my-agents — Update" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    $PythonCmd = Find-Python
    & $PythonCmd main.py --update
    exit $LASTEXITCODE
}

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  oh-my-agents — Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ---------------------------------------------------------------------------
# 1. Verify Python
# ---------------------------------------------------------------------------
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
$PythonCmd = Find-Python
$versionOutput = Invoke-Expression "& $PythonCmd --version 2>&1"
Write-Host "  OK: $versionOutput" -ForegroundColor Green

# ---------------------------------------------------------------------------
# 2. Install dependencies
# ---------------------------------------------------------------------------
Write-Host "[2/5] Installing dependencies..." -ForegroundColor Yellow
$reqFile = Join-Path $ScriptDir "requirements.txt"

if (-not (Test-Path $reqFile)) {
    Write-Host "  ERROR: requirements.txt not found at $reqFile" -ForegroundColor Red
    exit 1
}

# Use the discovered Python to run pip as a module (guarantees correct pip)
& $PythonCmd -m pip install -r $reqFile --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: Dependency installation failed. Check the output above for details." -ForegroundColor Red
    exit 1
}
Write-Host "  OK: Dependencies installed" -ForegroundColor Green

# ---------------------------------------------------------------------------
# 3. Verify OpenCode CLI
# ---------------------------------------------------------------------------
Write-Host "[3/5] Checking OpenCode CLI..." -ForegroundColor Yellow
$opencodeAvailable = Get-Command opencode -ErrorAction SilentlyContinue
if ($opencodeAvailable) {
    Write-Host "  OK: OpenCode CLI found" -ForegroundColor Green
} else {
    Write-Host "  WARNING: OpenCode CLI not found" -ForegroundColor Yellow
    Write-Host "  Install from https://opencode.ai" -ForegroundColor Yellow
    Write-Host ""
}

# ---------------------------------------------------------------------------
# 4. Run the main CLI
# ---------------------------------------------------------------------------
Write-Host "[4/5] Starting system..." -ForegroundColor Yellow
Write-Host ""

try {
    & $PythonCmd main.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n  ERROR: main.py exited with code $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
} catch {
    Write-Host "  ERROR: Failed to run main.py. Details: $_" -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------------------
# 5. Global install (automatic — agents available from any directory)
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "[5/5] Installing agents globally..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  OpenCode looks for .opencode/ in the current directory by default."
Write-Host "  Installing agents to ~/.opencode/agents/ so"
Write-Host "  'opencode --agent orchestrator' works from ANY folder on your system."
Write-Host ""

& $PythonCmd main.py --install-global
if ($LASTEXITCODE -ne 0) {
    Write-Host "  WARNING: Global install reported an error. Check the output above." -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 6. Auto-session continuity
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "[6/6] Session continuity..." -ForegroundColor Yellow
Write-Host ""
$enableAuto = Read-Host "Enable auto-session saving? This keeps context between sessions. (Y/n)"
if ($enableAuto -eq "" -or $enableAuto -eq "y" -or $enableAuto -eq "Y") {
    & $PythonCmd main.py --inject-context 2>&1 | Out-Null
    $flagDir = Join-Path $PWD.Path ".opencode"
    if (-not (Test-Path $flagDir)) {
        $null = New-Item -ItemType Directory -Path $flagDir -Force
    }
    $flagFile = Join-Path $flagDir ".auto_session_enabled"
    "# Auto-session saving enabled for $((Get-Item $PWD.Path).Name)`n# Created: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -FilePath $flagFile -Encoding utf8
    Write-Host "  Auto-session enabled." -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Run: opencode --agent orchestrator" -ForegroundColor White
Write-Host ""
Write-Host "  Interactive dashboard:" -ForegroundColor Cyan
Write-Host "    python main.py                     Open dashboard and select a provider" -ForegroundColor White
Write-Host "    python main.py --plan go           Switch to Go plan" -ForegroundColor White
Write-Host "    python main.py --plan lmstudio     Switch to LM Studio (local models)" -ForegroundColor White
Write-Host "    python main.py --plan copilot      Switch to GitHub Copilot" -ForegroundColor White
Write-Host "    python main.py --plan openrouter   Switch to OpenRouter" -ForegroundColor White
Write-Host "    python main.py --doctor            Run diagnostics" -ForegroundColor White
Write-Host ""
