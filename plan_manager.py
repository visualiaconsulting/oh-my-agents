# plan_manager.py
"""
Plan Manager — Go plan as the only standard. Other plans require explicit installation.
"""
import os
import json
from pathlib import Path
from typing import Dict, Optional


class PlanManager:
    # Plan-to-model mapping by role
    # Using registry IDs (provider/model-id) that OpenCode recognizes
    PLAN_MODELS = {
        "go": {
            "orchestrator": "opencode-go/deepseek-v4-pro",
            "code-analyst": "opencode-go/deepseek-v4-flash",
            "validator": "opencode-go/mimo-v2.5-pro",
            "bulk-processor": "opencode-go/minimax-m2.7",
            "subagent": "opencode-go/glm-5.1",
            "summarizer": "opencode-go/minimax-m2.5",
            "frontend": "opencode-go/qwen3.6-plus",
            "ml-specialist": "opencode-go/minimax-m2.7",
            "fallback": "opencode-go/minimax-m2.5",
            "all_available": [
                "opencode-go/glm-5", "opencode-go/glm-5.1",
                "opencode-go/kimi-k2.5", "opencode-go/kimi-k2.6",
                "opencode-go/mimo-v2-pro", "opencode-go/mimo-v2-omni",
                "opencode-go/mimo-v2.5-pro", "opencode-go/mimo-v2.5",
                "opencode-go/minimax-m2.5", "opencode-go/minimax-m2.7",
                "opencode-go/deepseek-v4-pro", "opencode-go/deepseek-v4-flash",
                "opencode-go/qwen3.5-plus", "opencode-go/qwen3.6-plus"
            ]
        },
        "lmstudio": {
            # Models are set dynamically by lmstudio_manager.py
            # These are fallback defaults if plan.json says lmstudio but no agents installed
            "orchestrator": "lmstudio/default-orchestrator",
            "code-analyst": "lmstudio/default-code-analyst",
            "validator": "lmstudio/default-validator",
            "bulk-processor": "lmstudio/default-bulk",
            "subagent": "lmstudio/default-subagent",
            "summarizer": "lmstudio/default-summarizer",
            "frontend": "lmstudio/default-frontend",
            "ml-specialist": "lmstudio/default-ml",
            "fallback": "lmstudio/default-fallback"
        }
    }
    
    # Approximate limits per plan (for monitoring)
    PLAN_LIMITS = {
        "go": {"daily": 5000, "weekly": 25000, "monthly": 100000},
        "lmstudio": {"daily": "unlimited", "weekly": "unlimited", "monthly": "unlimited"}
    }
    
    def __init__(self, plan: Optional[str] = None, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent
        self.plan = plan or self._detect_plan()
        self.models = self.PLAN_MODELS.get(self.plan, self.PLAN_MODELS["go"])
        self.limits = self.PLAN_LIMITS.get(self.plan, self.PLAN_LIMITS["go"])
    
    def _detect_plan(self) -> str:
        """Returns 'go' as default, or 'lmstudio' if explicitly set in plan.json.
        Other plans require explicit installation via main.py or wizard.
        """
        config_path = self.project_root / ".opencode" / "plan.json"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    plan = json.load(f).get("plan", "go")
                    if plan in self.PLAN_MODELS:
                        return plan
            except (json.JSONDecodeError, OSError):
                pass
        return "go"

    def get_available_models(self) -> list:
        """Returns a list of available model names for the current plan"""
        if "all_available" in self.models:
            return self.models["all_available"]
        return list(set(self.models.values()))

    def get_model(self, role: str) -> str:
        """Gets the model for a role, with fallback if not available"""
        return self.models.get(role, self.models.get("fallback"))
    
    def validate_models(self):
        """Validate that agent models in .opencode/agents/*.md exist in the registry.

        Returns:
            (valid, invalid): tuple of (list of valid agent names,
                              list of (name, model) tuples for invalid agents)
        """
        import yaml

        agent_dir = self.project_root / ".opencode" / "agents"
        if not agent_dir.exists():
            return [], []

        known_models = set()
        for plan_data in self.PLAN_MODELS.values():
            if "all_available" in plan_data:
                known_models.update(plan_data["all_available"])
            for key, val in plan_data.items():
                if key != "all_available" and isinstance(val, str):
                    known_models.add(val)

        valid = []
        invalid = []

        for md_file in agent_dir.glob("*.md"):
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()
                if content.startswith("---"):
                    parts = content.split("---")
                    if len(parts) >= 3:
                        metadata = yaml.safe_load(parts[1])
                        name = metadata.get("name", md_file.stem)
                        model = metadata.get("model", "")
                        if model and model in known_models:
                            valid.append(name)
                        else:
                            invalid.append((name, model))
            except (yaml.YAMLError, OSError):
                invalid.append((md_file.stem, "parse error"))

        return valid, invalid

    def generate_config_snippet(self) -> Dict:
        """Generates a configuration snippet for opencode.json"""
        return {
            "plan": self.plan,
            "models": {role: self.get_model(role) for role in 
             ["orchestrator", "code-analyst", "validator", "bulk-processor",
              "subagent", "summarizer", "frontend", "ml-specialist"]},
            "limits": self.limits,
            "requires_api_keys": self.plan == "api",
            "auto_fallback": True
        }


