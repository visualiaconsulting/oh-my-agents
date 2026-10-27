# Bootstrap for Windows. Run from the project you want to configure.
# C:\path\oh-my-agents\setup.ps1 --runtime codex --profile chatgpt --export
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'scripts\python-bootstrap.ps1')

try {
    $python = Find-ProjectPython
    $executable = $python.Executable
    $prefix = @($python.Prefix)
    $mainScript = Join-Path $PSScriptRoot 'main.py'
    $requirements = Join-Path $PSScriptRoot 'requirements.txt'

    Write-Host 'oh-my-agents - Setup' -ForegroundColor Cyan
    & $executable @prefix --version
    & $executable @prefix -m pip install -r $requirements --quiet
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    # Keep the caller's cwd: main.py binds data to that project.
    if ($args.Count -gt 0) {
        & $executable @prefix $mainScript @args
        exit $LASTEXITCODE
    }

    & $executable @prefix $mainScript
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $enableAuto = Read-Host 'Enable OpenCode auto-session saving for this project? (Y/n)'
    if ($enableAuto -eq '' -or $enableAuto -match '^[yY]$') {
        & $executable @prefix $mainScript --enable-auto-session
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        & $executable @prefix $mainScript --inject-context
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    Write-Host 'Setup complete. Run python main.py --help for project commands.' -ForegroundColor Green
} catch {
    Write-Error $_
    exit 1
}
