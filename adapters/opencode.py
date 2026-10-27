"""OpenCode Markdown rendering from shared instructions and profile data."""
import json

import yaml

from agent_catalog import ROLES, instructions_for


def format_agent(role, model, description, permissions, body=None):
    metadata = {"name": role, "description": description,
                "mode": "primary" if role == "orchestrator" else "subagent",
                "model": model, "temperature": 0.2, "permission": permissions}
    return "---\n" + yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True) + "---\n\n" + (body or instructions_for(role))


def render_files(root, catalog, profile):
    result = {}
    for role in ROLES:
        definition = catalog["roles"][role]
        result[f".opencode/agents/{role}.md"] = format_agent(
            role, profile["models"][role]["model"], definition["description"], definition["permissions"])
    plan_path = root / ".opencode" / "plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8")) if plan_path.exists() else {}
    if not isinstance(plan, dict):
        raise ValueError("Existing plan.json must be a JSON object")
    plan["plan"] = profile["name"]
    plan["models"] = {role: profile["models"][role]["model"] for role in ROLES}
    result[".opencode/plan.json"] = json.dumps(plan, indent=2) + "\n"
    return result
