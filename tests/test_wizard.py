from pathlib import Path
from cli.wizard import SetupWizard


class TestSetupWizardInit:
    """Tests for SetupWizard initialization."""

    def test_custom_project_root(self, temp_project):
        wizard = SetupWizard(project_root=temp_project)
        assert wizard.project_root == temp_project.resolve()
        assert wizard.agent_dir == temp_project / ".opencode" / "agents"

    def test_auto_project_root(self):
        wizard = SetupWizard()
        assert wizard.project_root is not None
        assert wizard.project_root.exists()


class TestCheckExistingConfig:
    """Tests for check_existing_config()."""

    def test_detects_existing_agents(self, temp_project):
        wizard = SetupWizard(project_root=temp_project)
        assert wizard.check_existing_config() is True

    def test_detects_no_agents(self, temp_empty_project):
        wizard = SetupWizard(project_root=temp_empty_project)
        assert wizard.check_existing_config() is False

    def test_detects_empty_agent_dir(self, temp_empty_project):
        agent_dir = temp_empty_project / ".opencode" / "agents"
        agent_dir.mkdir(parents=True)
        wizard = SetupWizard(project_root=temp_empty_project)
        assert wizard.check_existing_config() is False


class TestSetupDefaults:
    """Tests for setup_defaults()."""

    def test_creates_eight_agents(self, temp_empty_project):
        wizard = SetupWizard(project_root=temp_empty_project)
        wizard.setup_defaults()
        assert len(wizard.agents) == 8

    def test_summarizer_is_included(self, temp_empty_project):
        wizard = SetupWizard(project_root=temp_empty_project)
        wizard.setup_defaults()
        names = [a["name"] for a in wizard.agents]
        assert "summarizer" in names

    def test_frontend_is_included(self, temp_empty_project):
        wizard = SetupWizard(project_root=temp_empty_project)
        wizard.setup_defaults()
        names = [a["name"] for a in wizard.agents]
        assert "frontend" in names

    def test_ml_specialist_is_included(self, temp_empty_project):
        wizard = SetupWizard(project_root=temp_empty_project)
        wizard.setup_defaults()
        names = [a["name"] for a in wizard.agents]
        assert "ml-specialist" in names

    def test_agents_have_required_fields(self, temp_empty_project):
        wizard = SetupWizard(project_root=temp_empty_project)
        wizard.setup_defaults()
        for agent in wizard.agents:
            assert "name" in agent
            assert "description" in agent
            assert "mode" in agent
            assert "model" in agent
            assert "permissions" in agent
            perms = agent["permissions"]
            assert "edit" in perms
            assert "bash" in perms
            assert "read" in perms
            assert "task" in perms

    def test_orchestrator_permissions_are_restricted(self, temp_empty_project):
        wizard = SetupWizard(project_root=temp_empty_project)
        wizard.setup_defaults()
        orch = next(a for a in wizard.agents if a["name"] == "orchestrator")
        assert orch["permissions"]["edit"] == "deny"
        assert orch["permissions"]["task"] == "allow"

    def test_validator_is_read_only(self, temp_empty_project):
        wizard = SetupWizard(project_root=temp_empty_project)
        wizard.setup_defaults()
        val = next(a for a in wizard.agents if a["name"] == "validator")
        assert val["permissions"]["edit"] == "deny"
        assert val["permissions"]["bash"] == "deny"
        assert val["permissions"]["read"] == "allow"

    def test_code_analyst_can_edit_and_bash(self, temp_empty_project):
        wizard = SetupWizard(project_root=temp_empty_project)
        wizard.setup_defaults()
        ca = next(a for a in wizard.agents if a["name"] == "code-analyst")
        assert ca["permissions"]["edit"] == "allow"
        assert ca["permissions"]["bash"] == "allow"

    def test_orchestrator_model_is_deepseek(self, temp_empty_project):
        wizard = SetupWizard(project_root=temp_empty_project)
        wizard.setup_defaults()
        orch = next(a for a in wizard.agents if a["name"] == "orchestrator")
        assert orch["model"] == "opencode-go/deepseek-v4-pro"

    def test_validator_model_is_qwen(self, temp_empty_project):
        wizard = SetupWizard(project_root=temp_empty_project)
        wizard.setup_defaults()
        val = next(a for a in wizard.agents if a["name"] == "validator")
        assert val["model"] == "opencode-go/qwen3.6-plus"


class TestSaveAll:
    """Tests for save_all()."""

    def test_saves_agents_to_disk(self, temp_empty_project):
        wizard = SetupWizard(project_root=temp_empty_project)
        wizard.setup_defaults()
        wizard.save_all()

        agent_dir = temp_empty_project / ".opencode" / "agents"
        assert agent_dir.exists()
        md_files = list(agent_dir.glob("*.md"))
        assert len(md_files) == 8

    def test_summarizer_saved(self, temp_empty_project):
        wizard = SetupWizard(project_root=temp_empty_project)
        wizard.setup_defaults()
        wizard.save_all()

        agent_dir = temp_empty_project / ".opencode" / "agents"
        assert (agent_dir / "summarizer.md").exists()

    def test_frontend_saved(self, temp_empty_project):
        wizard = SetupWizard(project_root=temp_empty_project)
        wizard.setup_defaults()
        wizard.save_all()

        agent_dir = temp_empty_project / ".opencode" / "agents"
        assert (agent_dir / "frontend.md").exists()

    def test_ml_specialist_saved(self, temp_empty_project):
        wizard = SetupWizard(project_root=temp_empty_project)
        wizard.setup_defaults()
        wizard.save_all()

        agent_dir = temp_empty_project / ".opencode" / "agents"
        assert (agent_dir / "ml-specialist.md").exists()

    def test_saved_files_are_valid_yaml_frontmatter(self, temp_empty_project):
        import yaml
        wizard = SetupWizard(project_root=temp_empty_project)
        wizard.setup_defaults()
        wizard.save_all()

        agent_dir = temp_empty_project / ".opencode" / "agents"
        for md_file in agent_dir.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            assert content.startswith("---")
            parts = content.split("---")
            metadata = yaml.safe_load(parts[1])
            assert "name" in metadata
            assert "model" in metadata
            assert "permission" in metadata


class TestFormatMd:
    """Tests for _format_md()."""

    def test_output_contains_frontmatter(self, temp_empty_project):
        wizard = SetupWizard(project_root=temp_empty_project)
        agent = {
            "name": "test",
            "description": "Test agent",
            "mode": "subagent",
            "model": "opencode-go/deepseek-v4-pro",
            "permissions": {
                "edit": "allow",
                "bash": "allow",
                "read": "allow",
                "task": "deny",
            }
        }
        md = wizard._format_md(agent)
        assert md.startswith("---")
        assert "name: test" in md
        assert "model: opencode-go/deepseek-v4-pro" in md
        assert "edit: allow" in md
        assert md.endswith("efficiently.\n")

    def test_output_has_body(self, temp_empty_project):
        wizard = SetupWizard(project_root=temp_empty_project)
        agent = {
            "name": "test",
            "description": "Test agent",
            "mode": "subagent",
            "model": "opencode-go/deepseek-v4-pro",
            "permissions": {
                "edit": "allow",
                "bash": "deny",
                "read": "allow",
                "task": "deny",
            }
        }
        md = wizard._format_md(agent)
        parts = md.split("---")
        assert len(parts) >= 3
        body = parts[2].strip()
        assert "Test agent" in body
