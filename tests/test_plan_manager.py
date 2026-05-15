import os
from plan_manager import PlanManager


class TestPlanDetection:
    """Tests for _detect_plan() method."""

    def test_default_plan_is_go(self, clean_env):
        pm = PlanManager()
        assert pm.plan == "go"

    def test_explicit_env_var(self, clean_env):
        os.environ["OPENCODE_PLAN"] = "zen"
        pm = PlanManager()
        assert pm.plan == "zen"

    def test_env_var_case_insensitive(self, clean_env):
        os.environ["OPENCODE_PLAN"] = "ENTERPRISE"
        pm = PlanManager()
        assert pm.plan == "enterprise"

    def test_anthropic_key_detects_api(self, clean_env):
        os.environ["ANTHROPIC_API_KEY"] = "sk-fake"
        pm = PlanManager()
        assert pm.plan == "api"

    def test_github_token_detects_zen(self, clean_env):
        os.environ["GITHUB_TOKEN"] = "ghp_fake"
        pm = PlanManager()
        assert pm.plan == "zen"

    def test_copilot_token_detects_zen(self, clean_env):
        os.environ["COPILOT_TOKEN"] = "fake-copilot-token"
        pm = PlanManager()
        assert pm.plan == "zen"

    def test_openrouter_key_detected(self, clean_env):
        os.environ["OPENROUTER_API_KEY"] = "sk-or-fake"
        pm = PlanManager()
        assert pm.plan == "openrouter"

    def test_ollama_host_detected(self, clean_env):
        os.environ["OLLAMA_HOST"] = "http://localhost:11434"
        pm = PlanManager()
        assert pm.plan == "ollama"

    def test_env_var_takes_priority(self, clean_env):
        os.environ["OPENCODE_PLAN"] = "go"
        os.environ["ANTHROPIC_API_KEY"] = "sk-fake"
        pm = PlanManager()
        assert pm.plan == "go"


class TestGetModel:
    """Tests for get_model() method."""

    def test_orchestrator_model(self, clean_env):
        pm = PlanManager()
        assert pm.get_model("orchestrator") == "opencode-go/deepseek-v4-pro"

    def test_code_analyst_model(self, clean_env):
        pm = PlanManager()
        assert pm.get_model("code-analyst") == "opencode-go/deepseek-v4-flash"

    def test_validator_model(self, clean_env):
        pm = PlanManager()
        assert pm.get_model("validator") == "opencode-go/mimo-v2.5-pro"

    def test_bulk_processor_model(self, clean_env):
        pm = PlanManager()
        assert pm.get_model("bulk-processor") == "opencode-go/minimax-m2.7"

    def test_subagent_model(self, clean_env):
        pm = PlanManager()
        assert pm.get_model("subagent") == "opencode-go/glm-5.1"

    def test_fallback_model(self, clean_env):
        pm = PlanManager()
        assert pm.get_model("fallback") == "opencode-go/minimax-m2.5"

    def test_frontend_model(self, clean_env):
        pm = PlanManager()
        assert pm.get_model("frontend") == "opencode-go/qwen3.6-plus"

    def test_ml_specialist_model(self, clean_env):
        pm = PlanManager()
        assert pm.get_model("ml-specialist") == "opencode-go/minimax-m2.7"

    def test_unknown_role_returns_fallback(self, clean_env):
        pm = PlanManager()
        assert pm.get_model("nonexistent") == pm.get_model("fallback")

    def test_zen_plan_models(self, clean_env):
        pm = PlanManager(plan="zen")
        assert pm.get_model("orchestrator") == "opencode/claude-sonnet-4.5"
        assert pm.get_model("code-analyst") == "opencode/gpt-5.1-codex"

    def test_copilot_plan_models(self, clean_env):
        pm = PlanManager(plan="copilot")
        assert pm.get_model("orchestrator") == "copilot/claude-sonnet-4"


class TestGetAvailableModels:
    """Tests for get_available_models()."""

    def test_go_plan_has_available_models(self, clean_env):
        pm = PlanManager()
        models = pm.get_available_models()
        assert isinstance(models, list)
        assert len(models) > 0
        assert "opencode-go/deepseek-v4-pro" in models

    def test_api_plan_falls_back_to_values(self, clean_env):
        pm = PlanManager(plan="api")
        models = pm.get_available_models()
        assert isinstance(models, list)
        assert len(models) >= 1


class TestProjectRoot:
    """Tests for project_root parameter."""

    def test_custom_project_root(self, clean_env, temp_project):
        pm = PlanManager(project_root=temp_project)
        assert pm.project_root == temp_project.resolve()

    def test_default_project_root(self, clean_env):
        pm = PlanManager()
        assert pm.project_root is not None
        assert pm.project_root.exists()


class TestPlanLimits:
    """Tests for plan limits."""

    def test_go_plan_has_limits(self, clean_env):
        pm = PlanManager()
        assert pm.limits["daily"] == 5000
        assert pm.limits["weekly"] == 25000

    def test_ollama_plan_has_unlimited(self, clean_env):
        pm = PlanManager(plan="ollama")
        assert pm.limits["daily"] == "unlimited"


class TestValidateModels:
    """Tests for validate_models()."""

    def test_valid_models_pass(self, clean_env, temp_project):
        from plan_manager import PlanManager
        pm = PlanManager(project_root=temp_project)
        valid, invalid = pm.validate_models()
        assert len(valid) == 2
        assert len(invalid) == 0

    def test_invalid_model_detected(self, clean_env, temp_empty_project):
        agent_dir = temp_empty_project / ".opencode" / "agents"
        agent_dir.mkdir(parents=True)
        (agent_dir / "bad-agent.md").write_text("""---
name: bad-agent
description: Test
mode: subagent
model: opencode-go/nonexistent-model-xyz
temperature: 0.2
permission:
  edit: allow
  bash: allow
  read: allow
  task: deny
---

Bad agent.
""", encoding="utf-8")

        from plan_manager import PlanManager
        pm = PlanManager(project_root=temp_empty_project)
        valid, invalid = pm.validate_models()
        assert len(valid) == 0
        assert len(invalid) == 1
        assert invalid[0][0] == "bad-agent"
        assert "nonexistent-model-xyz" in invalid[0][1]

    def test_mixed_valid_and_invalid(self, clean_env, temp_empty_project):
        agent_dir = temp_empty_project / ".opencode" / "agents"
        agent_dir.mkdir(parents=True)
        (agent_dir / "good.md").write_text("""---
name: good
description: Test
mode: subagent
model: opencode-go/deepseek-v4-pro
temperature: 0.2
permission:
  edit: allow
  bash: allow
  read: allow
  task: deny
---

Good.
""", encoding="utf-8")
        (agent_dir / "bad.md").write_text("""---
name: bad
description: Test
mode: subagent
model: opencode-go/invalid-model
temperature: 0.2
permission:
  edit: allow
  bash: allow
  read: allow
  task: deny
---

Bad.
""", encoding="utf-8")

        from plan_manager import PlanManager
        pm = PlanManager(project_root=temp_empty_project)
        valid, invalid = pm.validate_models()
        assert len(valid) == 1
        assert len(invalid) == 1
        assert valid[0] == "good"
        assert invalid[0][0] == "bad"
