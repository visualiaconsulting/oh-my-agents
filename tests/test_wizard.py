import pytest
import yaml

from agent_catalog import ROLES
from cli.wizard import SetupWizard


def test_custom_project_root(temp_project):
    wizard = SetupWizard(project_root=temp_project)
    assert wizard.project_root == temp_project.resolve()
    # Windows CI may expose an 8.3 TEMP path (RUNNER~1) that resolve expands.
    assert wizard.agent_dir == temp_project.resolve() / ".opencode" / "agents"


def test_auto_project_root():
    assert SetupWizard().project_root.exists()


def test_detects_existing_agents(temp_project):
    assert SetupWizard(temp_project).check_existing_config()


def test_detects_missing_agents(tmp_path):
    assert not SetupWizard(tmp_path).check_existing_config()


def test_defaults_are_exactly_five_roles(tmp_path):
    wizard = SetupWizard(tmp_path)
    wizard.setup_defaults()
    assert [a["name"] for a in wizard.agents] == list(ROLES)
    assert sum(a["mode"] == "primary" for a in wizard.agents) == 1


def test_orchestrator_permissions_restrict_execution(tmp_path):
    wizard = SetupWizard(tmp_path)
    wizard.setup_defaults()
    primary = wizard.agents[0]
    assert primary["permissions"] == {"edit": "deny", "bash": "deny", "read": "allow", "task": "allow"}


def test_specialists_can_work_but_cannot_delegate(tmp_path):
    wizard = SetupWizard(tmp_path)
    wizard.setup_defaults()
    for agent in wizard.agents[1:]:
        assert agent["permissions"]["edit"] == "allow"
        assert agent["permissions"]["bash"] == "allow"
        assert agent["permissions"]["task"] == "deny"


def test_saves_complete_prompts_and_five_files(tmp_path):
    wizard = SetupWizard(tmp_path)
    wizard.setup_defaults()
    wizard.save_all()
    paths = sorted(wizard.agent_dir.glob("*.md"))
    assert {p.stem for p in paths} == set(ROLES)
    for path in paths:
        content = path.read_text(encoding="utf-8")
        meta = yaml.safe_load(content.split("---", 2)[1])
        assert meta["name"] == path.stem
        assert meta["permission"]["read"] == "allow"
        assert "Return: outcome" in content
    assert "exactly four specialists" in (wizard.agent_dir / "orchestrator.md").read_text(encoding="utf-8")


def test_save_rejects_incomplete_catalog(tmp_path):
    wizard = SetupWizard(tmp_path)
    wizard.setup_defaults()
    wizard.agents.pop()
    with pytest.raises(ValueError, match="exactly"):
        wizard.save_all()
    assert not wizard.agent_dir.exists()


def test_save_rejects_custom_file_without_overwriting(tmp_path):
    wizard = SetupWizard(tmp_path)
    wizard.setup_defaults()
    wizard.agent_dir.mkdir(parents=True)
    path = wizard.agent_dir / "coder.md"
    path.write_text("My custom coder", encoding="utf-8")
    with pytest.raises(ValueError, match="overwritten"):
        wizard.save_all()
    assert path.read_text(encoding="utf-8") == "My custom coder"


def test_manual_agent_restricts_role_names(tmp_path):
    with pytest.raises(ValueError, match="supported role"):
        SetupWizard(tmp_path).setup_agent("another-specialist")


def test_format_custom_compatibility_entry(tmp_path):
    agent = {"name": "test", "description": "Test agent", "model": "opencode-go/deepseek-v4-pro",
             "permissions": {"edit": "allow", "bash": "deny", "read": "allow", "task": "deny"}}
    content = SetupWizard(tmp_path)._format_md(agent)
    assert content.startswith("---")
    assert yaml.safe_load(content.split("---", 2)[1])["name"] == "test"
    assert "Test agent" in content.split("---", 2)[2]
