"""
lmstudio_manager.py — LM Studio integration for oh-my-agents

Detects LM Studio server, lists downloaded models, ranks them by size,
and assigns roles automatically or manually.
"""
import json
import re
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Dict, Optional, Tuple

LMSTUDIO_BASE = "http://localhost:1234"
LMSTUDIO_API_V0 = f"{LMSTUDIO_BASE}/api/v0"
LMSTUDIO_API_V1 = f"{LMSTUDIO_BASE}/api/v1"

ROLE_NAMES = [
    "orchestrator", "code-analyst", "validator", "bulk-processor",
    "subagent", "summarizer", "frontend", "ml-specialist"
]

ROLE_DESCRIPTIONS = {
    "orchestrator": "Main coordinator — delegates tasks to sub-agents",
    "code-analyst": "Senior software engineer — implements code",
    "validator": "QA specialist — validates and reviews code",
    "bulk-processor": "Bulk data processing",
    "subagent": "Debugger and fallback agent",
    "summarizer": "Session summarizer and project analyst",
    "frontend": "Frontend specialist — React, TypeScript, UI",
    "ml-specialist": "ML and data pipeline specialist",
}

ROLE_PERMISSIONS = {
    "orchestrator":   {"edit": "deny",  "bash": "deny",  "read": "allow", "task": "allow"},
    "code-analyst":   {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
    "validator":      {"edit": "deny",  "bash": "deny",  "read": "allow", "task": "deny"},
    "bulk-processor": {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
    "subagent":       {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
    "summarizer":     {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
    "frontend":       {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
    "ml-specialist":  {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
}

ROLE_TEMPERATURES = {
    "orchestrator": 0.2, "code-analyst": 0.2, "validator": 0.1,
    "bulk-processor": 0.3, "subagent": 0.2, "summarizer": 0.3,
    "frontend": 0.3, "ml-specialist": 0.2,
}


def _parse_params(params_str: str) -> float:
    """Parse parameter string like '7B', '14B', '3.8B', '70B' into float billions."""
    if not params_str:
        return 0.0
    match = re.search(r'([\d.]+)\s*[Bb]', params_str)
    if match:
        return float(match.group(1))
    return 0.0


def check_lmstudio_running(timeout: int = 3) -> bool:
    """Check if LM Studio server is running and accessible."""
    try:
        req = urllib.request.Request(f"{LMSTUDIO_API_V0}/models", method="GET")
        urllib.request.urlopen(req, timeout=timeout)
        return True
    except Exception:
        return False


def list_models() -> List[Dict]:
    """
    Fetch models from LM Studio REST API v0.
    Returns list of LLM models with metadata, sorted by params (desc).
    """
    try:
        req = urllib.request.Request(f"{LMSTUDIO_API_V0}/models", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise ConnectionError(f"Cannot reach LM Studio at {LMSTUDIO_BASE}: {e}")

    raw_models = data.get("data", [])
    llm_models = []

    for m in raw_models:
        model_type = m.get("type", "")
        state = m.get("state", "not-loaded")

        # Skip embedding models
        if model_type == "embedding":
            continue

        params_str = m.get("paramsString", "")
        params = _parse_params(params_str)
        max_ctx = m.get("max_context_length", 0)
        arch = m.get("arch", "")
        quant = m.get("quantization", "")
        model_id = m.get("id", "")
        publisher = m.get("publisher", "")
        display = m.get("displayName", model_id)

        llm_models.append({
            "id": model_id,
            "display_name": display,
            "publisher": publisher,
            "arch": arch,
            "quantization": quant,
            "params_string": params_str,
            "params": params,
            "max_context_length": max_ctx,
            "state": state,
            "is_loaded": state == "loaded",
            "is_code": bool(re.search(r'code|coder|instruct', model_id, re.IGNORECASE)),
        })

    # Sort: params desc, then max_context_length desc, then display name
    llm_models.sort(key=lambda m: (m["params"], m["max_context_length"], m["display_name"]), reverse=True)
    return llm_models


def auto_assign_roles(models: List[Dict]) -> List[Tuple[str, Dict]]:
    """
    Assign roles to models based on size ranking.
    Largest model -> orchestrator, 2nd -> code-analyst, etc.
    Returns list of (role, model_info) tuples.
    """
    if not models:
        return []

    # Boost code models for code-analyst role
    scored = []
    for m in models:
        score = m["params"]
        if m["is_code"]:
            score += 0.5  # Small boost for code models
        scored.append((score, m))

    scored.sort(key=lambda x: x[0], reverse=True)
    ranked_models = [m for _, m in scored]

    assignments = []
    for i, role in enumerate(ROLE_NAMES):
        if i < len(ranked_models):
            assignments.append((role, ranked_models[i]))

    return assignments


def format_agent_md(role: str, model_info: Dict) -> str:
    """Generate agent .md file content for a given role and model."""
    perms = ROLE_PERMISSIONS[role]
    temp = ROLE_TEMPERATURES[role]
    desc = ROLE_DESCRIPTIONS[role]
    model_id = model_info["id"]

    return f"""---
name: {role}
description: {desc}
mode: {"primary" if role == "orchestrator" else "subagent"}
model: lmstudio/{model_id}
temperature: {temp}
permission:
  edit: {perms["edit"]}
  bash: {perms["bash"]}
  read: {perms["read"]}
  task: {perms["task"]}
---

{desc}. Running locally via LM Studio ({model_info['display_name']}, {model_info['params_string']}).
"""


def install_lmstudio_agents(project_root: Path, models: List[Dict], manual: bool = False) -> Dict:
    """
    Install LM Studio agents to .opencode/agents/.
    Backs up existing Go agents, creates new LM Studio agents.
    Returns dict with status info.
    """
    agents_dir = project_root / ".opencode" / "agents"
    backup_dir = project_root / ".opencode" / "agents-go-backup"

    # Backup existing Go agents
    if agents_dir.exists():
        if backup_dir.exists():
            import shutil
            shutil.rmtree(backup_dir)
        import shutil
        shutil.copytree(agents_dir, backup_dir)

    agents_dir.mkdir(parents=True, exist_ok=True)

    # Remove existing agent files
    for f in agents_dir.glob("*.md"):
        f.unlink()

    if manual:
        # Manual mode: let user assign roles
        assignments = _manual_assign(models)
    else:
        assignments = auto_assign_roles(models)

    installed = []
    for role, model_info in assignments:
        content = format_agent_md(role, model_info)
        file_path = agents_dir / f"{role}.md"
        file_path.write_text(content, encoding="utf-8")
        installed.append({
            "role": role,
            "model": model_info["id"],
            "display": model_info["display_name"],
            "params": model_info["params_string"],
        })

    # Save plan.json
    plan_path = project_root / ".opencode" / "plan.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump({"plan": "lmstudio"}, f)

    return {
        "installed": installed,
        "count": len(installed),
        "backup_dir": str(backup_dir),
    }


def _manual_assign(models: List[Dict]) -> List[Tuple[str, Dict]]:
    """
    Interactive manual role assignment.
    Returns list of (role, model_info) tuples.
    """
    import questionary

    assignments = []
    used_models = set()

    for role in ROLE_NAMES:
        available = [m for m in models if m["id"] not in used_models]
        if not available:
            break

        choices = []
        for m in available:
            label = f"{m['display_name']} ({m['params_string']}, ctx={m['max_context_length']})"
            choices.append({"name": label, "value": m["id"]})

        # Auto-select the first available (largest)
        default = choices[0]["value"] if choices else None

        selected_id = questionary.select(
            f"Select model for @{role} ({ROLE_DESCRIPTIONS[role]}):",
            choices=choices,
            default=default,
        ).ask()

        if selected_id is None:
            break

        model_info = next(m for m in models if m["id"] == selected_id)
        used_models.add(selected_id)
        assignments.append((role, model_info))

    return assignments


def reset_to_go(project_root: Path) -> Dict:
    """
    Restore Go agents from backup, remove LM Studio plan.
    Returns status dict.
    """
    agents_dir = project_root / ".opencode" / "agents"
    backup_dir = project_root / ".opencode" / "agents-go-backup"
    plan_path = project_root / ".opencode" / "plan.json"

    restored = 0

    if backup_dir.exists():
        import shutil
        # Clear current agents
        if agents_dir.exists():
            shutil.rmtree(agents_dir)
        # Restore from backup
        shutil.copytree(backup_dir, agents_dir)
        restored = len(list(agents_dir.glob("*.md")))
        # Remove backup
        shutil.rmtree(backup_dir)

    # Remove plan.json to revert to Go
    if plan_path.exists():
        plan_path.unlink()

    return {
        "restored": restored,
        "backup_existed": backup_dir.exists() if backup_dir else False,
    }


def get_status() -> Dict:
    """Get LM Studio status: running, models, assignments."""
    running = check_lmstudio_running()
    models = []
    error = None

    if running:
        try:
            models = list_models()
        except Exception as e:
            error = str(e)

    return {
        "running": running,
        "model_count": len(models),
        "models": models,
        "error": error,
    }
