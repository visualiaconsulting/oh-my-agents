"""Offline coverage of command validation, runtime choice and honest records."""

import json
from unittest.mock import MagicMock

import pytest

import main
import runtime_cli
from project_db import ProjectDB


def run_cli(monkeypatch, root, *arguments):
    monkeypatch.setattr("sys.argv", ["main.py", "--dir", str(root), *arguments])
    return main.main()


def test_cli_export_preview_leaves_nonexistent_project_absent(tmp_path, monkeypatch, capsys):
    root = tmp_path / "project"
    run_cli(monkeypatch, root, "--runtime", "codex", "--profile", "chatgpt", "--export", "--dry-run")
    assert not root.exists()
    assert "preview" in capsys.readouterr().out


@pytest.mark.parametrize("arguments", [
    ("--dry-run",),
    ("--runtime", "codex", "--plan", "go"),
    ("--runtime", "codex", "--install-global"),
    ("--available-models", "does-not-exist.json"),
    ("--runtime", "codex", "--profile", "go", "--export"),
    ("--runtime", "opencode", "--profile", "chatgpt", "--export"),
    ("--runtime", "opencode", "--install-design-skills"),
    ("--runtime", "codex", "--profile", "go"),
    ("--profile", "chatgpt"),
])
def test_invalid_commands_exit_without_creating_project(tmp_path, monkeypatch, arguments):
    root = tmp_path / "project"
    monkeypatch.setattr(main, "show_dashboard", MagicMock(side_effect=AssertionError("Invalid command reached dashboard")))
    with pytest.raises(SystemExit) as error:
        run_cli(monkeypatch, root, *arguments)
    assert error.value.code in (1, 2)
    assert not root.exists()


@pytest.mark.parametrize("extra", ["--enable-auto-session", "--resume-context", "--inject-context"])
def test_export_preview_rejects_combined_continuity_actions(tmp_path, monkeypatch, extra):
    root = tmp_path / "project"
    with pytest.raises(SystemExit) as error:
        run_cli(monkeypatch, root, "--runtime", "codex", "--export", "--dry-run", extra)
    assert error.value.code in (1, 2)
    assert not root.exists()


def test_record_does_not_infer_model_or_success_from_profile(tmp_path):
    root = tmp_path / "project"
    filename = tmp_path / "record.json"
    filename.write_text(json.dumps({
        "summary": "Code saved; verification remains pending",
        "role": "coder",
        "checks": [{"command": "pytest tests/example.py"}],
    }), encoding="utf-8")
    sid = runtime_cli.record_session(root, filename, "codex", "chatgpt")
    with ProjectDB(root) as db:
        saved = db.get_session(sid)
        assert saved["runtime"] == "codex"
        assert saved["profile"] == "chatgpt"
        assert saved["model"] == ""
        assert saved["status"] == "partial"
        assert saved["checks"][0]["status"] == "not_run"


def test_record_preserves_explicit_actual_model_and_results(tmp_path):
    filename = tmp_path / "record.json"
    filename.write_text(json.dumps({
        "summary": "Reviewed dashboard",
        "role": "dashboard-designer",
        "runtime": "codex",
        "profile": "chatgpt",
        "model": "gpt-6.1-terra",
        "status": "completed",
        "checks": [{"name": "Visual inspection", "status": "passed"}],
        "evidence": [{"path": "screenshots/dashboard.png"}],
    }), encoding="utf-8")
    sid = runtime_cli.record_session(tmp_path / "project", filename, "codex", "chatgpt")
    with ProjectDB(tmp_path / "project") as db:
        saved = db.get_session(sid)
        assert saved["model"] == "gpt-6.1-terra"
        assert saved["checks"][0]["status"] == "passed"
        assert saved["evidence"] == [{"path": "screenshots/dashboard.png"}]


@pytest.mark.parametrize("data", [
    {"summary": "Invalid profile", "runtime": "codex", "profile": "go"},
    {"summary": "Unknown role", "role": "sixth-specialist"},
    {"summary": ""},
    ["Not an object"],
])
def test_invalid_session_record_is_rejected_before_creating_database(tmp_path, data):
    filename = tmp_path / "invalid.json"
    filename.write_text(json.dumps(data), encoding="utf-8")
    root = tmp_path / "project"
    with pytest.raises(ValueError):
        runtime_cli.record_session(root, filename, "codex", "chatgpt")
    assert not root.exists()


def test_read_inventory_accepts_response_data_and_rejects_empty_ids(tmp_path):
    filename = tmp_path / "models.json"
    filename.write_text(json.dumps({"data": [{"id": "gpt-6-astra"}, {"id": "gpt-6-luna"}]}), encoding="utf-8")
    assert runtime_cli.read_inventory(filename) == ["gpt-6-astra", "gpt-6-luna"]
    filename.write_text(json.dumps({"models": [" "]}), encoding="utf-8")
    with pytest.raises(ValueError, match="nonempty"):
        runtime_cli.read_inventory(filename)


def test_dashboard_displays_selected_codex_profile(tmp_path, monkeypatch):
    panel = MagicMock()
    monkeypatch.setattr(runtime_cli, "active_runtime", lambda root: ("codex", "chatgpt"))
    monkeypatch.setattr(runtime_cli, "configured_agents", lambda *args: [])
    monkeypatch.setattr("cli.ui.print_plan_panel", panel)
    continuity = MagicMock()
    continuity.has_history.return_value = False
    monkeypatch.setattr("continuity.ContinuityManager", lambda **kwargs: continuity)
    selection = MagicMock()
    selection.ask.return_value = "0"
    monkeypatch.setattr("questionary.select", lambda *args, **kwargs: selection)
    main.show_dashboard(tmp_path)
    assert panel.call_args.args[0] == "chatgpt"
    assert "Codex" in panel.call_args.args[1]["chatgpt"]["name"]


def test_dashboard_codex_choice_exports_project_profile(tmp_path, monkeypatch):
    selection = MagicMock()
    selection.ask.return_value = "chatgpt"
    monkeypatch.setattr("questionary.select", lambda *args, **kwargs: selection)
    export = MagicMock(return_value={"runtime": "codex", "profile": "chatgpt"})
    monkeypatch.setattr(runtime_cli, "export_project", export)
    monkeypatch.setattr(runtime_cli, "print_export_report", MagicMock())
    main._switch_provider(tmp_path, MagicMock())
    export.assert_called_once_with(tmp_path, "codex", "chatgpt")


def test_cli_runtime_selection_reaches_dashboard(tmp_path, monkeypatch):
    root = tmp_path / "project"
    displayed = []
    monkeypatch.setattr(main, "check_dependencies", lambda: [])
    monkeypatch.setattr(main, "show_dashboard", lambda project: displayed.append(runtime_cli.active_runtime(project)))
    run_cli(monkeypatch, root, "--runtime", "codex")
    assert displayed == [("codex", "chatgpt")]


def test_malformed_active_selection_is_actionable(tmp_path):
    directory = tmp_path / ".oh-my-agents"
    directory.mkdir()
    (directory / "active.json").write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        runtime_cli.active_runtime(tmp_path)
