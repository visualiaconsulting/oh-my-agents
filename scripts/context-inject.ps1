<#
.SYNOPSIS
  Context Injector for oh-my-agents.
  Injects session continuity context and shows project status before running opencode.

.DESCRIPTION
  Run this before `opencode` to:
  1. Check/ask for auto-session enablement
  2. Inject last session context into .opencode/context.md
  3. Show project status banner

  Usage:
    .\context-inject.ps1
    opencode --agent orchestrator
#>

# Resolve script and project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")

# Path to main.py
$MainPy = Join-Path $ProjectRoot "main.py"

if (-not (Test-Path $MainPy)) {
    Write-Host "[context-inject] ERROR: main.py not found at $MainPy" -ForegroundColor Red
    exit 1
}

# Step 1: Inject context and show banner
Write-Host ""
python $MainPy --inject-context 2>&1 | ForEach-Object { $_ }
Write-Host ""

# Step 2: Check/ask for auto-session enablement
$AutoSessionFlag = Join-Path $ProjectRoot ".opencode" ".auto_session_enabled"
if (-not (Test-Path $AutoSessionFlag)) {
    $enable = Read-Host "Enable auto-session saving for this project? (y/N)"
    if ($enable -eq "y" -or $enable -eq "Y") {
        python $MainPy --plan go --auto-enable 2>&1 | Out-Null
        Write-Host "[context-inject] Auto-session enabled." -ForegroundColor Green
    }
}

# Done — opencode CLI will run next
