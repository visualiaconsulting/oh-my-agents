import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from lmstudio_manager import (
    _parse_params,
    auto_assign_roles,
    safe_assign_roles,
    ensure_global_lmstudio_config,
    format_agent_md,
    GLOBAL_OPENCODE_CONFIG,
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

    def test_fewer_than_fifteen_models(self):
        models = [self._make_model(f"model-{i}b", float(i)) for i in range(1, 4)]
        result = auto_assign_roles(models)
        assert len(result) == 3
        roles = [r[0] for r in result]
        assert roles == ["orchestrator", "python-engineer", "db-architect"]

    def test_code_model_boost(self):
        # A 6B code model should beat a 7B non-code for python-engineer
        models = [
            self._make_model("large-7b", 7.0),
            self._make_model("coder-6b", 6.0, is_code=True),
            self._make_model("medium-5b", 5.0),
        ]
        result = auto_assign_roles(models)
        # Orchestrator should still be largest (7B)
        assert result[0][0] == "orchestrator"
        assert result[0][1]["id"] == "large-7b"
        # python-engineer should be the code model (6B + 0.5 boost = 6.5 > 5.0)
        assert result[1][0] == "python-engineer"
        assert result[1][1]["id"] == "coder-6b"


class TestSafeAssignRoles:
    def _make_model(self, name, params, is_code=False):
        return {
            "id": name,
            "display_name": name,
            "params": params,
            "params_string": f"{int(params)}B" if params > 0 else "",
            "max_context_length": 32768,
            "is_code": is_code,
            "is_loaded": True,
            "publisher": "test",
            "arch": "llama",
            "quantization": "Q4",
            "state": "loaded",
        }

    def test_avoids_nemotron_for_orchestrator(self):
        models = [
            self._make_model("nvidia/nemotron-3-nano-4b", 4.0),
            self._make_model("mistralai/ministral-3-3b", 3.0),
        ]
        result = safe_assign_roles(models)
        assert result[0][0] == "orchestrator"
        assert "nemotron" not in result[0][1]["id"]
        assert result[0][1]["id"] == "mistralai/ministral-3-3b"

    def test_skips_embedding_models(self):
        models = [
            self._make_model("text-embedding-nomic", 0.0),
            self._make_model("nemotron-4b", 4.0),
            self._make_model("ministral-3b", 3.0),
        ]
        result = safe_assign_roles(models)
        assigned_ids = [m["id"] for _, m in result]
        assert "text-embedding-nomic" not in assigned_ids

    def test_passes_through_if_no_nemotron(self):
        models = [
            self._make_model("ministral-3b", 3.0),
            self._make_model("gemma-2b", 2.0),
        ]
        result = safe_assign_roles(models)
        assert result[0][1]["id"] == "ministral-3b"

    def test_nemotron_goes_to_least_critical_role(self):
        models = [
            self._make_model("nemotron-4b", 4.0),
            self._make_model("ministral-3b", 3.0),
            self._make_model("gemma-2b", 2.0),
        ]
        result = safe_assign_roles(models)
        nemotron_role = None
        for role, model in result:
            if "nemotron" in model["id"]:
                nemotron_role = role
                break
        assert nemotron_role in ["prompt-engineer", "git-manager", "docs-writer"]

    def test_empty_models(self):
        assert safe_assign_roles([]) == []

    def test_only_broken_models_falls_back(self):
        models = [self._make_model("nemotron-4b", 4.0)]
        result = safe_assign_roles(models)
        assert len(result) == 1
        assert result[0][1]["id"] == "nemotron-4b"


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
        content = format_agent_md("python-engineer", model)
        assert "name: python-engineer" in content
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


class TestEnsureGlobalLmstudioConfig:
    def _make_installed(self, model_id, display, role="orchestrator"):
        return {
            "role": role,
            "model": model_id,
            "display": display,
            "params": "7B",
        }

    def _run_with_temp_home(self, installed, preexisting_config=None):
        """
        Temporarily redirect Path.home() to a temp directory so
        GLOBAL_OPENCODE_CONFIG resolves inside tmpdir.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_home = Path(tmpdir)
            config_dir = fake_home / ".config" / "opencode"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "opencode.jsonc"

            if preexisting_config is not None:
                config_file.write_text(
                    json.dumps(preexisting_config, indent=2), encoding="utf-8"
                )
                assert config_file.exists()

            with patch.object(Path, "home", return_value=fake_home):
                ensure_global_lmstudio_config(installed)

                assert config_file.exists()
                with open(config_file, encoding="utf-8") as f:
                    return json.load(f)

    def test_creates_new_file_when_not_exists(self):
        installed = [
            self._make_installed("qwen2.5-7b-instruct", "Qwen2.5 7B Instruct"),
            self._make_installed("llama-3.1-8b", "Llama 3.1 8B", "python-engineer"),
        ]
        data = self._run_with_temp_home(installed)

        assert "provider" in data
        assert "lmstudio" in data["provider"]
        lmstudio = data["provider"]["lmstudio"]
        assert lmstudio["npm"] == "@ai-sdk/openai-compatible"
        assert lmstudio["name"] == "LM Studio (local)"
        assert lmstudio["options"]["baseURL"] == "http://127.0.0.1:1234/v1"
        assert "qwen2.5-7b-instruct" in lmstudio["models"]
        assert lmstudio["models"]["qwen2.5-7b-instruct"]["name"] == "Qwen2.5 7B Instruct"
        assert "llama-3.1-8b" in lmstudio["models"]

    def test_merges_with_existing_config(self):
        installed = [
            self._make_installed("qwen2.5-7b-instruct", "Qwen2.5 7B Instruct"),
        ]
        data = self._run_with_temp_home(installed, {
            "mcp": {
                "filesystem": {"type": "local", "command": ["npx", "..."]}
            }
        })

        assert "mcp" in data
        assert "filesystem" in data["mcp"]
        assert "provider" in data
        assert "lmstudio" in data["provider"]

    def test_updates_existing_lmstudio_config(self):
        installed = [
            self._make_installed("new-model", "New Model"),
        ]
        data = self._run_with_temp_home(installed, {
            "provider": {
                "lmstudio": {
                    "npm": "@ai-sdk/openai-compatible",
                    "name": "LM Studio (old)",
                    "options": {"baseURL": "http://127.0.0.1:1234/v1"},
                    "models": {"old-model": {"name": "Old Model"}},
                }
            }
        })

        lmstudio = data["provider"]["lmstudio"]
        assert "new-model" in lmstudio["models"]
        assert "old-model" not in lmstudio["models"]
        assert lmstudio["name"] == "LM Studio (local)"

    def test_handles_empty_installed_list(self):
        data = self._run_with_temp_home([])
        assert data["provider"]["lmstudio"]["models"] == {}
