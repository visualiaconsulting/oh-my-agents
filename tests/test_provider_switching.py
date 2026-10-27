import sys
from unittest.mock import patch

from main import _pick_models_for_plan, _switch_provider, main
from plan_manager import PlanManager
from runtime_cli import active_runtime, export_project, select_runtime


def test_reexport_preserves_installed_local_models(tmp_path):
    manager = PlanManager(plan="lmstudio", project_root=tmp_path)
    models = {role: "lmstudio/installed-model" for role in manager.ALL_ROLES}
    manager.write_agent_files(tmp_path, models)
    report = export_project(tmp_path, "opencode", "lmstudio", dry_run=True,
                            inventory=["lmstudio/installed-model"])
    assert report["changed"] == 0
    export_project(tmp_path, "opencode", "lmstudio")
    assert PlanManager(project_root=tmp_path).get_model("coder") == "lmstudio/installed-model"


def test_picker_saves_models_for_requested_plan(tmp_path):
    PlanManager(plan="go", project_root=tmp_path).write_agent_files(tmp_path)
    with patch("questionary.select") as select:
        select.return_value.ask.return_value = "copilot/my-chosen-model"
        agents = _pick_models_for_plan("copilot", tmp_path)
    assert len(agents) == 5
    saved = PlanManager(project_root=tmp_path)
    assert saved.plan == "copilot"
    assert all(saved.get_model(role) == "copilot/my-chosen-model" for role in saved.ALL_ROLES)


def test_failed_activation_preserves_dashboard_selection(tmp_path):
    select_runtime(tmp_path, "codex", "chatgpt")
    with patch("questionary.select") as select, patch("main.activate_lmstudio_plan", return_value=None):
        select.return_value.ask.return_value = "lmstudio"
        _switch_provider(tmp_path, PlanManager(project_root=tmp_path))
    assert active_runtime(tmp_path) == ("codex", "chatgpt")


def test_failed_activation_preserves_cli_selection(tmp_path):
    select_runtime(tmp_path, "codex", "chatgpt")
    with patch.object(sys, "argv", ["main.py", "--dir", str(tmp_path), "--plan", "lmstudio"]), \
            patch("main.activate_lmstudio_plan", return_value=None):
        main()
    assert active_runtime(tmp_path) == ("codex", "chatgpt")
