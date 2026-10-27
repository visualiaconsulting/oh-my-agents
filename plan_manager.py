"""OpenCode plan compatibility facade over the shared five-role catalog."""
import json
from pathlib import Path
from typing import Dict, Optional

from agent_catalog import LEGACY_ROLE_MAP, ROLES, load_catalog, load_profile

_CATALOG = load_catalog()["roles"]
_PROFILES = {name: load_profile(name) for name in ("go", "lmstudio", "copilot", "openrouter")}
_FALLBACKS = {"go": "opencode-go/minimax-m2.5", "lmstudio": "lmstudio/default-fallback",
              "copilot": "copilot/claude-3.5-haiku", "openrouter": "openrouter/google/gemini-2.5-flash"}


class PlanManager:
    """Select an OpenCode provider; Codex exports use adapters.export_runtime."""
    ALL_ROLES = list(ROLES)
    ROLE_PERMISSIONS = {name: item["permissions"] for name, item in _CATALOG.items()}
    ROLE_DESCRIPTIONS = {name: item["description"] for name, item in _CATALOG.items()}
    PLAN_DISPLAY_NAMES = {name: profile["display_name"] for name, profile in _PROFILES.items()}
    PLAN_DESCRIPTIONS = {
        "go": "OpenCode Go cloud models with five focused agents",
        "lmstudio": "Run the five agents with local models",
        "copilot": "Use your GitHub Copilot subscription models",
        "openrouter": "Use your OpenRouter API credits",
    }
    PLAN_MODELS = {
        name: {**{role: settings["model"] for role, settings in profile["models"].items()},
               "fallback": _FALLBACKS[name],
               "all_available": sorted({s["model"] for s in profile["models"].values()} | {_FALLBACKS[name]})}
        for name, profile in _PROFILES.items()
    }
    # Historical estimates kept for old consumers; these are not ChatGPT quotas.
    PLAN_LIMITS = {
        "go": {"daily": 5000, "weekly": 25000, "monthly": 100000,
               "5h_dollars": 12, "weekly_dollars": 30, "monthly_dollars": 60},
        "lmstudio": {"daily": "unlimited", "weekly": "unlimited", "monthly": "unlimited"},
        "copilot": {"daily": "copilot_limits", "weekly": "copilot_limits", "monthly": "copilot_limits"},
        "openrouter": {"daily": "pay_as_you_go", "weekly": "pay_as_you_go", "monthly": "pay_as_you_go"},
    }

    def __init__(self, plan: Optional[str] = None, project_root: Optional[Path] = None):
        self.project_root = Path(project_root).resolve() if project_root else Path(__file__).resolve().parent
        self.plan = plan or self._detect_plan()
        if self.plan not in self.PLAN_MODELS:
            raise ValueError(f"Unsupported OpenCode plan: {self.plan}")
        self.models = dict(self.PLAN_MODELS[self.plan])
        self.limits = dict(self.PLAN_LIMITS[self.plan])
        path = self.project_root / ".opencode" / "plan.json"
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(saved, dict) and saved.get("plan") == self.plan and isinstance(saved.get("models"), dict):
                for role, model in saved["models"].items():
                    if role in ROLES and isinstance(model, str) and model:
                        self.models[role] = model
        except (json.JSONDecodeError, OSError):
            pass

    def _detect_plan(self) -> str:
        path = self.project_root / ".opencode" / "plan.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            plan = data.get("plan") if isinstance(data, dict) else None
            return plan if plan in self.PLAN_MODELS else "go"
        except (json.JSONDecodeError, OSError):
            return "go"

    def write_agent_files(self, working_root, plan_models=None):
        """Export five complete agents with backups and ownership checks."""
        from adapters import export_runtime
        models = plan_models or self.models
        overrides = {role: models[role] for role in ROLES if role in models}
        export_runtime(working_root, "opencode", self.plan, model_overrides=overrides)
        return len(ROLES)

    def get_available_models(self) -> list:
        return sorted(set(self.models["all_available"]) | {self.models[role] for role in ROLES})

    def get_model(self, role: str) -> str:
        # Compatibility aliases do not create additional active roles.
        return self.models.get(LEGACY_ROLE_MAP.get(role, role), self.models["fallback"])

    def validate_models(self):
        """Validate shipped profile IDs, not live account availability."""
        import yaml
        directory = self.project_root / ".opencode" / "agents"
        if not directory.exists():
            return [], []
        known = {model for data in self.PLAN_MODELS.values() for model in data["all_available"]}
        valid, invalid = [], []
        for path in sorted(directory.glob("*.md")):
            try:
                parts = path.read_text(encoding="utf-8").split("---", 2)
                meta = yaml.safe_load(parts[1]) if len(parts) == 3 else None
                if not isinstance(meta, dict):
                    raise ValueError("Invalid front matter")
                name, model = meta.get("name", path.stem), meta.get("model", "")
                if model in known or (self.plan == "lmstudio" and isinstance(model, str) and model.startswith("lmstudio/")):
                    valid.append(name)
                else:
                    invalid.append((name, model))
            except (yaml.YAMLError, OSError, ValueError):
                invalid.append((path.stem, "parse error"))
        return valid, invalid

    def generate_config_snippet(self) -> Dict:
        return {"plan": self.plan, "models": {role: self.get_model(role) for role in ROLES},
                "limits": self.limits, "requires_api_keys": self.plan == "openrouter",
                "auto_fallback": False}

    def get_plan_display_name(self, plan: Optional[str] = None) -> str:
        name = plan or self.plan
        return self.PLAN_DISPLAY_NAMES.get(name, name.capitalize())

    def get_plan_description(self, plan: Optional[str] = None) -> str:
        return self.PLAN_DESCRIPTIONS.get(plan or self.plan, "")

    def save_plan(self, plan: str):
        if plan not in self.PLAN_MODELS:
            raise ValueError(f"Unsupported OpenCode plan: {plan}")
        path = self.project_root / ".opencode" / "plan.json"
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        if not isinstance(data, dict):
            raise ValueError("plan.json must contain an object")
        if data.get("plan") != plan:
            data.pop("models", None)
        data["plan"] = plan
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        self.plan = plan
        self.models = dict(self.PLAN_MODELS[plan])
        self.limits = dict(self.PLAN_LIMITS[plan])
