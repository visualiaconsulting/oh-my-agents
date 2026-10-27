"""Detect native export drift without mutating a project or contacting a model."""
import pytest
import tomlkit

from adapters import export_runtime
from scripts.validate_agents import validate_codex


def test_native_export_validates_without_modifying_files(tmp_path):
    export_runtime(tmp_path, "codex", "chatgpt")
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert validate_codex(tmp_path, require=True) == []
    after = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after


def test_require_codex_rejects_missing_export(tmp_path):
    assert validate_codex(tmp_path) == []
    assert validate_codex(tmp_path, require=True) == ["Native Codex config is missing"]


@pytest.mark.parametrize("field,value", [
    ("model", "wrong-model"),
    ("model_reasoning_effort", "low"),
    ("developer_instructions", "lost specialist instructions"),
])
def test_specialist_drift_is_reported(tmp_path, field, value):
    export_runtime(tmp_path, "codex", "chatgpt")
    path = tmp_path / ".codex/agents/database.toml"
    agent = tomlkit.parse(path.read_text(encoding="utf-8"))
    agent[field] = value
    path.write_text(tomlkit.dumps(agent), encoding="utf-8")
    assert any(f"database.{field}" in error for error in validate_codex(tmp_path))


def test_parent_model_and_unsafe_child_path_are_rejected(tmp_path):
    export_runtime(tmp_path, "codex", "chatgpt")
    path = tmp_path / ".codex/config.toml"
    config = tomlkit.parse(path.read_text(encoding="utf-8"))
    config["model"] = "different-parent"
    config["agents"]["writer"]["config_file"] = "../../outside.toml"
    path.write_text(tomlkit.dumps(config), encoding="utf-8")
    errors = validate_codex(tmp_path)
    assert any("config" in error.lower() for error in errors)
    assert errors


def test_unrelated_settings_are_retained_and_ignored(tmp_path):
    export_runtime(tmp_path, "codex", "chatgpt")
    path = tmp_path / ".codex/config.toml"
    config = tomlkit.parse(path.read_text(encoding="utf-8"))
    config["unrelated_setting"] = "user preference"
    path.write_text(tomlkit.dumps(config), encoding="utf-8")
    assert validate_codex(tmp_path) == []


def test_extra_native_agent_is_rejected_for_repository_release(tmp_path):
    export_runtime(tmp_path, "codex", "chatgpt")
    (tmp_path / ".codex/agents/extra.toml").write_text('name = "extra"', encoding="utf-8")
    assert any("exactly four" in error for error in validate_codex(tmp_path))


def test_legacy_export_uses_recorded_compatibility_and_validates(tmp_path):
    export_runtime(tmp_path, "codex", "chatgpt", codex_compat="legacy")
    config = tomlkit.parse((tmp_path / ".codex/config.toml").read_text(encoding="utf-8"))
    assert config["features"]["multi_agent"] is True
    assert config["agents"]["max_threads"] == 3
    assert "enabled" not in config["agents"]
    assert "max_concurrent_threads_per_session" not in config["agents"]
    assert validate_codex(tmp_path, require=True) == []


def test_legacy_export_without_manifest_is_inferred_without_writes(tmp_path):
    export_runtime(tmp_path, "codex", "chatgpt", codex_compat="legacy")
    (tmp_path / ".oh-my-agents/exports/codex.json").unlink()
    assert validate_codex(tmp_path, require=True) == []


def test_legacy_feature_cannot_be_disabled(tmp_path):
    export_runtime(tmp_path, "codex", "chatgpt", codex_compat="legacy")
    path = tmp_path / ".codex/config.toml"
    config = tomlkit.parse(path.read_text(encoding="utf-8"))
    config["features"]["multi_agent"] = False
    path.write_text(tomlkit.dumps(config), encoding="utf-8")
    assert any("multi_agent" in error for error in validate_codex(tmp_path))
