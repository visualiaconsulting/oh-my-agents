# Quick installation. Arguments are forwarded unchanged to setup.ps1.
# .\install.ps1 --runtime codex --profile chatgpt --export
& (Join-Path $PSScriptRoot 'setup.ps1') @args
exit $LASTEXITCODE
