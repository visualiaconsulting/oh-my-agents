import pytest
from lmstudio_manager import (
    _parse_params,
    auto_assign_roles,
    format_agent_md,
    ROLE_NAMES,
)


class TestParseParams:
    def test_7b(self):
        assert _parse_params("7B") == 7.0

    def test_14b(self):
        assert _parse_params("14B") == 14.0

    def test_3_8b(self):
        assert _parse_params("3.8B") == 3.8

    def test_70b(self):
        assert _parse_params("70B") == 70.0

    def test_empty(self):
        assert _parse_params("") == 0.0

    def test_none(self):
        assert _parse_params(None) == 0.0

    def test_lowercase_b(self):
        assert _parse_params("7b") == 7.0

    def test_with_space(self):
        assert _parse_params("7 B") == 7.0


class TestAutoAssignRoles:
    def _make_model(self, name, params, is_code=False):
        return {
            "id": name,
            "display_name": name,
            "params": params,
            "params_string": f"{int(params)}B",
            "max_context_length": 8192,
            "is_code": is_code,
            "is_loaded": False,
            "publisher": "test",
            "arch": "llama",
            "quantization": "Q4",
            "state": "not-loaded",
        }

    def test_empty_models(self):
        assert auto_assign_roles([]) == []

    def test_single_model(self):
        models = [self._make_model("test-7b", 7.0)]
        result = auto_assign_roles(models)
        assert len(result) == 1
        assert result[0][0] == "orchestrator"

    def test_eight_models_ordered_by_size(self):
        models = [self._make_model(f"model-{i}b", float(i)) for i in range(1, 9)]
        result = auto_assign_roles(models)
        assert len(result) == 8
        # Largest (8B) should be orchestrator
        assert result[0][0] == "orchestrator"
        assert result[0][1]["id"] == "model-8b"
        # Smallest (1B) should be last assigned role
        assert result[-1][1]["id"] == "model-1b"

    def test_fewer_than_eight_models(self):
        models = [self._make_model(f"model-{i}b", float(i)) for i in range(1, 4)]
        result = auto_assign_roles(models)
        assert len(result) == 3
        roles = [r[0] for r in result]
        assert roles == ["orchestrator", "code-analyst", "validator"]

    def test_code_model_boost(self):
        # A 6B code model should beat a 7B non-code for code-analyst
        models = [
            self._make_model("large-7b", 7.0),
            self._make_model("coder-6b", 6.0, is_code=True),
            self._make_model("medium-5b", 5.0),
        ]
        result = auto_assign_roles(models)
        # Orchestrator should still be largest (7B)
        assert result[0][0] == "orchestrator"
        assert result[0][1]["id"] == "large-7b"
        # Code-analyst should be the code model (6B + 0.5 boost = 6.5 > 5.0)
        assert result[1][0] == "code-analyst"
        assert result[1][1]["id"] == "coder-6b"


class TestFormatAgentMd:
    def test_orchestrator_format(self):
        model = {
            "id": "qwen2.5-7b-instruct",
            "display_name": "Qwen2.5 7B Instruct",
            "params_string": "7B",
        }
        content = format_agent_md("orchestrator", model)
        assert "name: orchestrator" in content
        assert "mode: primary" in content
        assert "lmstudio/qwen2.5-7b-instruct" in content
        assert "edit: deny" in content
        assert "bash: deny" in content
        assert "read: allow" in content
        assert "task: allow" in content

    def test_subagent_format(self):
        model = {
            "id": "llama-3.1-8b",
            "display_name": "Llama 3.1 8B",
            "params_string": "8B",
        }
        content = format_agent_md("code-analyst", model)
        assert "name: code-analyst" in content
        assert "mode: subagent" in content
        assert "lmstudio/llama-3.1-8b" in content
        assert "edit: allow" in content
        assert "bash: allow" in content
        assert "task: deny" in content

    def test_all_roles_produce_valid_md(self):
        model = {
            "id": "test-model",
            "display_name": "Test",
            "params_string": "7B",
        }
        for role in ROLE_NAMES:
            content = format_agent_md(role, model)
            assert content.startswith("---")
            assert "name:" in content
            assert "model:" in content
            assert "permission:" in content
