"""Run bootstrap entry points with a fake interpreter, never a real install."""
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")


def test_ci_yaml_is_valid_and_keeps_platform_matrix():
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    assert workflow["jobs"]["test"]["strategy"]["matrix"]["os"] == ["ubuntu-latest", "windows-latest"]
    assert "python scripts/validate_agents.py --require-codex" in [step.get("run") for step in workflow["jobs"]["test"]["steps"]]


@pytest.mark.skipif(not POWERSHELL, reason="PowerShell unavailable")
def test_windows_launcher_keeps_py_prefix_cwd_and_cli_args(tmp_path):
    log = tmp_path / "calls.jsonl"
    # Get-Command and Python are replaced in this process, so neither pip nor
    # main.py runs. Simulate the Windows launcher being the first match.
    harness = tmp_path / "harness.ps1"
    harness.write_text(r'''
param($Setup, $Log)
function global:Get-Command {
    param($Name)
    return [PSCustomObject]@{ Source = 'Invoke-FakePython' }
}
function global:Invoke-FakePython {
    if ($args -contains '-c') {
        $global:LASTEXITCODE = 0
        '3 11'
        return
    }
    [PSCustomObject]@{ argv = @($args); cwd = $PWD.Path } |
        ConvertTo-Json -Compress | Add-Content -LiteralPath $Log
    $global:LASTEXITCODE = 0
}
& $Setup --runtime codex --profile chatgpt --export --dry-run
exit $LASTEXITCODE
''', encoding="utf-8")
    result = subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(harness),
         str(ROOT / "setup.ps1"), str(log)],
        cwd=tmp_path, capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    calls = [json.loads(line) for line in log.read_text(encoding="utf-8-sig").splitlines()]
    assert all(call["argv"][0] == "-3" for call in calls)
    assert all(Path(call["cwd"]) == tmp_path for call in calls)
    assert calls[-1]["argv"] == [
        "-3", str(ROOT / "main.py"), "--runtime", "codex", "--profile", "chatgpt", "--export", "--dry-run"
    ]


@pytest.mark.skipif(os.name != "posix", reason="requires native Bash")
def test_unix_installed_launcher_preserves_project_and_arguments(tmp_path):
    framework = tmp_path / "framework with spaces"
    framework.mkdir()
    shutil.copy2(ROOT / "setup.sh", framework / "setup.sh")
    (framework / "main.py").write_text("# fake interpreter records this path\n")
    fakebin = tmp_path / "fake bin"
    fakebin.mkdir()
    log = tmp_path / "calls.log"
    fakepython = fakebin / "python3"
    fakepython.write_text('''#!/usr/bin/env bash
if [ "${1:-}" = '-c' ] || [ "${1:-}" = '--version' ] || [ "${1:-}" = '-m' ]; then
    exit 0
fi
printf '%s\\n' "$PWD" "$@" > "$BOOTSTRAP_TEST_LOG"
''')
    fakepython.chmod(0o755)
    installbin = tmp_path / "launcher bin"
    project = tmp_path / "target project"
    project.mkdir()
    env = dict(os.environ, PATH=str(fakebin) + os.pathsep + os.environ["PATH"],
               OH_MY_AGENTS_BIN_DIR=str(installbin), BOOTSTRAP_TEST_LOG=str(log))
    result = subprocess.run(["bash", str(framework / "setup.sh"), "--install-global"],
                            cwd=project, env=env, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
    result = subprocess.run([str(installbin / "oh-my-agents"), "--runtime", "codex", "--dir", "a project"],
                            cwd=project, env=env, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
    assert log.read_text().splitlines() == [
        str(project), str(framework / "main.py"), "--runtime", "codex", "--dir", "a project"
    ]
