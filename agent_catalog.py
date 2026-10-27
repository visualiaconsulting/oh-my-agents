"""Shared five-role catalog and validated model profiles.

Profile IDs are configuration, not a claim about account availability.
"""
from pathlib import Path
from typing import Optional

import yaml

ROOT = Path(__file__).resolve().parent
ROLES = ("orchestrator", "writer", "coder", "database", "dashboard-designer")
SPECIALISTS = tuple(role for role in ROLES if role != "orchestrator")
LEGACY_ROLE_MAP = {
    "python-engineer": "coder", "db-architect": "database",
    "structured-engineer": "coder", "docs-writer": "writer",
    "bulk-processor": "coder", "validator": "orchestrator",
    "researcher": "orchestrator", "frontend-engineer": "dashboard-designer",
    "devops": "coder", "ml-specialist": "coder",
    "security-reviewer": "orchestrator", "git-manager": "coder",
    "test-engineer": "coder", "prompt-engineer": "orchestrator",
    "summarizer": "writer", "formatter": "coder",
    "changelog-writer": "writer", "architect": "orchestrator",
    "api-designer": "coder", "code-reviewer": "orchestrator",
}


def _read_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping in {path.name}")
    return data


def load_catalog() -> dict:
    data = _read_yaml(ROOT / "agents" / "catalog.yaml")
    if set(data.get("roles", {})) != set(ROLES):
        raise ValueError("Catalog must define exactly the five supported roles")
    return data


def load_profile(profile: str, available_models: Optional[list] = None) -> dict:
    if profile not in ("chatgpt", "go", "lmstudio", "copilot", "openrouter"):
        raise ValueError(f"Unsupported profile: {profile}")
    filename = "codex-chatgpt" if profile == "chatgpt" else profile
    data = _read_yaml(ROOT / "profiles" / f"{filename}.yaml")
    models = data.get("models", {})
    if set(models) != set(ROLES):
        raise ValueError(f"Profile {profile} must assign all five roles")
    for role, settings in models.items():
        if not isinstance(settings, dict) or not isinstance(settings.get("model"), str) or not settings["model"]:
            raise ValueError(f"Invalid model for {role}")
        effort = settings.get("reasoning_effort")
        if effort is not None and effort not in ("low", "medium", "high", "xhigh", "max"):
            raise ValueError(f"Invalid reasoning effort for {role}: {effort}")
    if available_models is not None:
        missing = sorted({s["model"] for s in models.values()} - set(available_models))
        if missing:
            raise ValueError("Models absent from supplied inventory: " + ", ".join(missing))
    return data


def instructions_for(role: str) -> str:
    if role not in ROLES:
        raise ValueError(f"Unsupported role: {role}")
    directory = ROOT / "agents" / "prompts"
    common = (directory / "common.md").read_text(encoding="utf-8").strip()
    specific = (directory / f"{role}.md").read_text(encoding="utf-8").strip()
    return common + "\n\n" + specific + "\n"
