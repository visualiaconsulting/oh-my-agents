import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import tomlkit

import adapters
from adapters import export_runtime
from agent_catalog import ROLES, SPECIALISTS, load_catalog, load_profile


def test_catalog_has_only_five_roles():
    assert set(load_catalog()["roles"]) == set(ROLES)
    for profile in ("go", "chatgpt", "lmstudio", "copilot", "openrouter"):
        assert set(load_profile(profile)["models"]) == set(ROLES)


def test_codex_uses_all_four_requested_models():
    models = load_profile("chatgpt")["models"]
    assert models["orchestrator"]["model"] == "gpt-6-astra"
    assert models["writer"]["model"] == "gpt-6-luna"
    assert models["coder"]["model"] == models["database"]["model"] == "gpt-6.1-sol"
    assert models["dashboard-designer"]["model"] == "gpt-6.1-terra"


def test_opencode_model_selection_survives_reload(tmp_path):
    from plan_manager import PlanManager
    export_runtime(tmp_path, "opencode", "go", model_overrides={"coder": "opencode-go/deepseek-v4-pro"})
    reloaded = PlanManager(project_root=tmp_path)
    assert reloaded.get_model("coder") == "opencode-go/deepseek-v4-pro"
    assert reloaded.get_model("python-engineer") == reloaded.get_model("coder")
    reloaded.save_plan("copilot")
    assert PlanManager(project_root=tmp_path).get_model("coder") == "copilot/gpt-4o"


def test_inventory_validates_effective_overrides_instead_of_defaults(tmp_path):
    overrides = {role: f"lmstudio/local-{role}" for role in ROLES}
    inventory = list(overrides.values())
    result = export_runtime(tmp_path, "opencode", "lmstudio", available_models=inventory,
                            model_overrides=overrides)
    assert result["model_validation"] == "supplied_inventory"
    saved = json.loads((tmp_path / ".opencode/plan.json").read_text(encoding="utf-8"))
    assert saved["models"] == overrides


def test_inventory_rejects_missing_effective_override_before_writing(tmp_path):
    overrides = {role: f"lmstudio/local-{role}" for role in ROLES}
    inventory = [model for role, model in overrides.items() if role != "database"]
    with pytest.raises(ValueError, match="lmstudio/local-database"):
        export_runtime(tmp_path, "opencode", "lmstudio", available_models=inventory,
                       model_overrides=overrides)
    assert list(tmp_path.iterdir()) == []


def test_runtime_cli_roundtrip_preserves_custom_lmstudio_models(tmp_path):
    from plan_manager import PlanManager
    from runtime_cli import export_project

    overrides = {role: f"lmstudio/local-{role}" for role in ROLES}
    inventory = list(overrides.values())
    export_runtime(tmp_path, "opencode", "lmstudio", model_overrides=overrides)
    path = tmp_path / ".opencode/plan.json"
    before = path.read_bytes()
    preview = export_project(tmp_path, "opencode", "lmstudio", dry_run=True, inventory=inventory)
    assert preview["changed"] == 0
    assert not (tmp_path / ".oh-my-agents/active.json").exists()
    result = export_project(tmp_path, "opencode", "lmstudio", inventory=inventory)
    assert result["changed"] == 0
    assert path.read_bytes() == before
    assert export_project(tmp_path, "opencode", inventory=inventory)["changed"] == 0
    reloaded = PlanManager(project_root=tmp_path)
    assert {role: reloaded.get_model(role) for role in ROLES} == overrides


def test_dry_run_does_not_create_project(tmp_path):
    project = tmp_path / "new-project"
    report = export_runtime(project, "codex", dry_run=True)
    assert report["changed"] == 6
    assert report["dry_run"]
    assert not project.exists()


def test_invalid_runtime_profile_and_inventory_do_not_write(tmp_path):
    for runtime, profile, inventory in (("unknown", None, None), ("codex", "go", None),
                                        ("opencode", "chatgpt", None), ("codex", "missing", None),
                                        ("codex", "chatgpt", ["gpt-6-astra"])):
        with pytest.raises(ValueError):
            export_runtime(tmp_path, runtime, profile, available_models=inventory)
    assert list(tmp_path.iterdir()) == []


def test_codex_export_is_native_and_idempotent(tmp_path):
    first = export_runtime(tmp_path, "codex")
    assert first["changed"] == 6
    files = list((tmp_path / ".codex" / "agents").glob("*.toml"))
    assert {p.stem for p in files} == set(SPECIALISTS)
    for path in files:
        doc = tomlkit.parse(path.read_text(encoding="utf-8"))
        assert doc["name"] == path.stem
        assert doc["developer_instructions"]
        assert "permission" not in doc and "temperature" not in doc
        assert "model_provider" not in doc and "sandbox_mode" not in doc
    config = tomlkit.parse((tmp_path / ".codex/config.toml").read_text(encoding="utf-8"))
    assert config["model"] == "gpt-6-astra"
    assert config["agents"]["max_concurrent_threads_per_session"] == 3
    for role in SPECIALISTS:
        registered = config["agents"][role]
        assert registered["config_file"] == f"agents/{role}.toml"
        assert (tmp_path / ".codex" / registered["config_file"]).exists()
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert export_runtime(tmp_path, "codex")["changed"] == 0
    assert before == {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


def test_preserves_unrelated_toml_and_project_instructions(tmp_path):
    directory = tmp_path / ".codex"
    directory.mkdir()
    (directory / "config.toml").write_text('# Keep this comment\nmodel = "old"\n[mcp_servers.docs]\nurl = "https://example.test/mcp"\n', encoding="utf-8")
    instructions = tmp_path / "agents.md"
    instructions.write_text("# Local rules\nPreserve my rules.\n", encoding="utf-8")
    report = export_runtime(tmp_path, "codex")
    config = (directory / "config.toml").read_text(encoding="utf-8")
    assert "# Keep this comment" in config
    assert tomlkit.parse(config)["mcp_servers"]["docs"]["url"] == "https://example.test/mcp"
    assert instructions.read_text(encoding="utf-8").startswith("# Local rules\nPreserve my rules.")
    assert "backup" in report
    assert export_runtime(tmp_path, "codex")["changed"] == 0
    assert instructions.read_text(encoding="utf-8").count("<!-- oh-my-agents:begin -->") == 1


def test_custom_codex_registration_is_not_overwritten(tmp_path):
    directory = tmp_path / ".codex"
    directory.mkdir()
    path = directory / "config.toml"
    original = '[agents.writer]\nconfig_file = "my-writer.toml"\n'
    path.write_text(original, encoding="utf-8")
    with pytest.raises(ValueError, match="registration conflicts"):
        export_runtime(tmp_path, "codex")
    assert path.read_text(encoding="utf-8") == original
    assert not (directory / "agents").exists()


def test_legacy_concurrency_alias_is_migrated(tmp_path):
    directory = tmp_path / ".codex"
    directory.mkdir()
    path = directory / "config.toml"
    path.write_text('[agents]\nmax_threads = 8\ninterrupt_message = false\n', encoding="utf-8")
    export_runtime(tmp_path, "codex")
    agents = tomlkit.parse(path.read_text(encoding="utf-8"))["agents"]
    assert "max_threads" not in agents
    assert agents["max_concurrent_threads_per_session"] == 3
    assert agents["interrupt_message"] is False


def test_legacy_codex_schema_is_explicit_and_persisted(tmp_path):
    result = export_runtime(tmp_path, "codex", codex_compat="legacy")
    assert result["codex_compat"] == "legacy"
    path = tmp_path / ".codex/config.toml"
    config = tomlkit.parse(path.read_text(encoding="utf-8"))
    assert config["model"] == "gpt-6-astra"
    assert config["agents"]["max_threads"] == 3
    assert "enabled" not in config["agents"]
    assert "max_concurrent_threads_per_session" not in config["agents"]
    assert config["features"]["multi_agent"] is True
    for role in SPECIALISTS:
        assert config["agents"][role]["config_file"] == f"agents/{role}.toml"
    manifest = tmp_path / ".oh-my-agents/exports/codex.json"
    assert json.loads(manifest.read_text(encoding="utf-8"))["codex_compat"] == "legacy"
    before = manifest.read_bytes()
    preview = export_runtime(tmp_path, "codex", dry_run=True)
    assert preview["codex_compat"] == "legacy" and preview["changed"] == 0
    assert manifest.read_bytes() == before
    assert export_runtime(tmp_path, "codex")["changed"] == 0


def test_codex_schema_migration_preserves_models_and_unrelated_features(tmp_path):
    directory = tmp_path / ".codex"
    directory.mkdir()
    path = directory / "config.toml"
    path.write_text('[features]\ncustom_feature = false\n', encoding="utf-8")
    export_runtime(tmp_path, "codex", codex_compat="legacy")
    before_models = {p.name: tomlkit.parse(p.read_text(encoding="utf-8"))["model"]
                     for p in (directory / "agents").glob("*.toml")}
    result = export_runtime(tmp_path, "codex", codex_compat="modern")
    assert result["codex_compat"] == "modern" and "backup" in result
    config = tomlkit.parse(path.read_text(encoding="utf-8"))
    assert config["agents"]["enabled"] is True
    assert config["agents"]["max_concurrent_threads_per_session"] == 3
    assert "max_threads" not in config["agents"]
    assert "multi_agent" not in config["features"]
    assert config["features"]["custom_feature"] is False
    assert before_models == {p.name: tomlkit.parse(p.read_text(encoding="utf-8"))["model"]
                             for p in (directory / "agents").glob("*.toml")}
    assert export_runtime(tmp_path, "codex")["changed"] == 0
    export_runtime(tmp_path, "codex", codex_compat="legacy")
    assert export_runtime(tmp_path, "codex")["changed"] == 0


def test_codex_compat_rejects_invalid_or_other_runtime_without_writes(tmp_path):
    for runtime, compatibility in (("codex", "unknown"), ("opencode", "legacy"),
                                    ("opencode", "modern")):
        with pytest.raises(ValueError, match="codex_compat"):
            export_runtime(tmp_path, runtime, codex_compat=compatibility)
    assert list(tmp_path.iterdir()) == []


def test_modified_managed_agent_conflicts_without_partial_update(tmp_path):
    export_runtime(tmp_path, "codex")
    custom = tmp_path / ".codex/agents/coder.toml"
    custom.write_text(custom.read_text(encoding="utf-8") + "\n# My change\n", encoding="utf-8")
    config = tmp_path / ".codex/config.toml"
    before = config.read_bytes()
    with pytest.raises(ValueError, match="modified agent"):
        export_runtime(tmp_path, "codex")
    assert "# My change" in custom.read_text(encoding="utf-8")
    assert config.read_bytes() == before


def test_unknown_custom_agent_preserved_with_warning(tmp_path):
    directory = tmp_path / ".opencode/agents"
    directory.mkdir(parents=True)
    custom = directory / "my-specialist.md"
    custom.write_text("Custom instructions", encoding="utf-8")
    report = export_runtime(tmp_path, "opencode", "go")
    assert custom.read_text(encoding="utf-8") == "Custom instructions"
    assert len(report["warnings"]) == 1


def test_legacy_archive_requires_exact_fingerprint(tmp_path, monkeypatch):
    source = tmp_path / "source"
    (source / "agents").mkdir(parents=True)
    old = "Legacy exact framework content\n"
    fingerprint = hashlib.sha256(old.encode()).hexdigest()
    (source / "agents/legacy-fingerprints.json").write_text(json.dumps({
        ".opencode/agents/python-engineer.md": fingerprint,
        ".opencode/agents/db-architect.md": fingerprint,
    }), encoding="utf-8")
    monkeypatch.setattr(adapters, "ROOT", source)
    project = tmp_path / "project"
    directory = project / ".opencode/agents"
    directory.mkdir(parents=True)
    (directory / "python-engineer.md").write_text(old, encoding="utf-8")
    (directory / "db-architect.md").write_text(old + "User edits\n", encoding="utf-8")
    report = export_runtime(project, "opencode", "go", dry_run=True)
    assert (directory / "python-engineer.md").exists()
    assert any(change["action"] == "archive" for change in report["files"])
    report = export_runtime(project, "opencode", "go")
    assert not (directory / "python-engineer.md").exists()
    assert (directory / "db-architect.md").exists()
    backup = Path(report["backup"]) / ".opencode/agents/python-engineer.md"
    assert backup.read_text(encoding="utf-8") == old


def test_failed_write_rolls_back_existing_files(tmp_path):
    export_runtime(tmp_path, "opencode", "go")
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    original = adapters._atomic_write
    calls = 0

    def fail_second(path, content):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated disk failure")
        original(path, content)

    with patch.object(adapters, "_atomic_write", side_effect=fail_second):
        with pytest.raises(OSError, match="disk failure"):
            export_runtime(tmp_path, "opencode", "copilot")
    for relative, content in before.items():
        assert (tmp_path / relative).read_bytes() == content


def test_symlink_escape_is_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    try:
        (project / ".opencode").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("OS does not permit test symlinks")
    with pytest.raises(ValueError, match="escapes project"):
        export_runtime(project, "opencode", "go")
    assert not list(outside.iterdir())
