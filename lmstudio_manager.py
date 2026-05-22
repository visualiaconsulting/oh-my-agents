"""
lmstudio_manager.py — LM Studio integration for oh-my-agents

Detects LM Studio server, lists downloaded models, ranks them by size,
and assigns roles automatically or manually.
"""
import json
import os
import re
import shutil
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Dict, Optional, Tuple

LMSTUDIO_BASE = "http://localhost:1234"
LMSTUDIO_API_V0 = f"{LMSTUDIO_BASE}/api/v0"
LMSTUDIO_API_V1 = f"{LMSTUDIO_BASE}/api/v1"

GLOBAL_OPENCODE_CONFIG = Path.home() / ".config" / "opencode" / "opencode.jsonc"
GLOBAL_AGENTS_DIR = Path.home() / ".opencode" / "agents"
GLOBAL_BACKUP_DIR = Path.home() / ".opencode" / "agents-go-backup"

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
    """Check if LM Studio server is running and accessible via the OpenAI-compatible endpoint."""
    try:
        req = urllib.request.Request(f"{LMSTUDIO_BASE}/v1/models", method="GET")
        urllib.request.urlopen(req, timeout=timeout)
        return True
    except Exception:
        return False


def _model_id_to_display(model_id: str) -> str:
    """Convert a raw model ID to a human-readable display name."""
    name = model_id.replace("-", " ").replace("_", " ").strip()
    parts = name.split()
    cleaned = []
    for p in parts:
        if p.lower() in ("instruct", "gguf", "q4", "q5", "q8", "q2", "q3", "q6"):
            continue
        cleaned.append(p)
    return " ".join(cleaned).title() if cleaned else model_id


def list_models() -> List[Dict]:
    """
    Fetch models from the LM Studio OpenAI-compatible endpoint (/v1/models).
    Returns list of LLM models with metadata, sorted by params (desc).
    """
    try:
        req = urllib.request.Request(f"{LMSTUDIO_BASE}/v1/models", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise ConnectionError(f"Cannot reach LM Studio at {LMSTUDIO_BASE}: {e}")

    raw_models = data.get("data", [])
    llm_models = []

    for m in raw_models:
        model_id = m.get("id", "")
        if not model_id:
            continue

        params_str = ""
        params = _parse_params(model_id)
        if params > 0:
            params_str = f"{params}B"

        display = _model_id_to_display(model_id)

        llm_models.append({
            "id": model_id,
            "display_name": display,
            "publisher": m.get("owned_by", ""),
            "arch": "",
            "quantization": "",
            "params_string": params_str,
            "params": params,
            "max_context_length": 32768,
            "state": "loaded",
            "is_loaded": True,
            "is_code": bool(re.search(r'code|coder|instruct', model_id, re.IGNORECASE)),
        })

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


def _get_global_config_path() -> Path:
    """Resolve the global OpenCode config path dynamically."""
    return Path.home() / ".config" / "opencode" / "opencode.jsonc"


def ensure_global_lmstudio_config(installed: List[Dict]):
    """
    Add or update the LM Studio provider in ~/.config/opencode/opencode.jsonc
    so that OpenCode knows how to connect to the local LM Studio server and
    which models are available.
    """
    config_path = _get_global_config_path()
    config_dir = config_path.parent
    config_dir.mkdir(parents=True, exist_ok=True)

    config = {}
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError):
            config = {}

    provider_models = {}
    for entry in installed:
        model_id = entry["model"]
        display = entry["display"]
        params = entry.get("params", "")
        provider_models[model_id] = {
            "name": display,
            "limit": {
                "context": 32768,
                "output": 4096,
            },
        }

    lmstudio_config = {
        "npm": "@ai-sdk/openai-compatible",
        "name": "LM Studio (local)",
        "options": {
            "baseURL": "http://127.0.0.1:1234/v1"
        },
        "models": provider_models,
    }

    if "provider" not in config:
        config["provider"] = {}
    config["provider"]["lmstudio"] = lmstudio_config

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _rmtree(path: Path):
    """Remove a directory tree, handling Windows permission errors."""
    def handle_error(func, fpath, exc_info):
        os.chmod(fpath, 0o777)
        func(fpath)
    shutil.rmtree(path, onerror=handle_error)


def _install_agents_to_dir(target_dir: Path, assignments: List[Tuple[str, Dict]], backup_dir: Path) -> List[Dict]:
    """Backup existing agents in target_dir, then write LM Studio agents."""
    if target_dir.exists():
        if backup_dir.exists():
            _rmtree(backup_dir)
        shutil.copytree(target_dir, backup_dir)

    target_dir.mkdir(parents=True, exist_ok=True)
    for f in target_dir.glob("*.md"):
        f.unlink()

    installed = []
    for role, model_info in assignments:
        content = format_agent_md(role, model_info)
        file_path = target_dir / f"{role}.md"
        file_path.write_text(content, encoding="utf-8")
        installed.append({
            "role": role,
            "model": model_info["id"],
            "display": model_info["display_name"],
            "params": model_info["params_string"],
        })
    return installed


def _restore_agents_from_backup(target_dir: Path, backup_dir: Path) -> int:
    """Restore agents from backup dir into target dir. Returns count restored."""
    restored = 0
    if backup_dir.exists():
        if target_dir.exists():
            _rmtree(target_dir)
        shutil.copytree(backup_dir, target_dir)
        restored = len(list(target_dir.glob("*.md")))
        _rmtree(backup_dir)
    return restored


def safe_assign_roles(models: List[Dict]) -> List[Tuple[str, Dict]]:
    """
    Assign roles to models, avoiding known-broken models for key roles.
    Currently avoids Nemotron models which have a broken Jinja2 prompt template
    (error: \"Cannot apply filter 'string' to type: NullValue\").

    Strategy:
    1. Filter out embedding models (params <= 0) and broken models
    2. Rank usable LLMs by size with code model boost for code-analyst
    3. Assign to priority roles in order, duplicating models if needed

    Priority order: orchestrator > code-analyst > validator > bulk-processor > subagent
    """
    broken_keywords = ["nemotron"]

    # Filter to usable models only (non-embedding, non-broken)
    usable = []
    broken = []
    for m in models:
        mid = m["id"].lower()
        if m["params"] <= 0:
            continue  # skip embeddings
        if any(kw in mid for kw in broken_keywords):
            broken.append(m)
        else:
            usable.append(m)

    if not usable:
        return auto_assign_roles(models)  # fallback

    # Rank usable models by size with code model boost
    scorer = []
    for m in usable:
        score = m["params"]
        if m["is_code"]:
            score += 0.5
        scorer.append((score, m))
    scorer.sort(key=lambda x: x[0], reverse=True)
    ranked = [m for _, m in scorer]

    # Assign in priority order
    priority_roles = [r for r in ROLE_NAMES if r != "subagent"] + ["subagent"]

    assignments = []
    used_models = {}  # role -> model

    for i, role in enumerate(priority_roles):
        if i < len(ranked):
            model = ranked[i]
        else:
            model = ranked[-1]  # duplicate the smallest usable model
        assignments.append((role, model))

    # Assign broken models (like Nemotron) to subagent if possible
    if broken:
        for i in range(len(assignments) - 1, -1, -1):
            role, _ = assignments[i]
            if role in ("subagent", "bulk-processor"):
                assignments[i] = (role, broken[0])
                break

    return assignments


def install_lmstudio_agents(project_root: Path, models: List[Dict], manual: bool = False,
                            assignments: Optional[List[Tuple[str, Dict]]] = None) -> Dict:
    """
    Install LM Studio agents to .opencode/agents/ and ~/.opencode/agents/.
    Backs up existing Go agents in both locations, creates new LM Studio agents.
    Also updates global opencode.jsonc with the LM Studio provider.
    Returns dict with status info.
    """
    # Determine assignments
    if assignments is not None:
        pass  # use the provided assignments
    elif manual:
        assignments = _manual_assign(models)
    else:
        assignments = safe_assign_roles(models)

    if not assignments:
        return {"installed": [], "count": 0, "backup_dir": ""}

    # Install to project agents (for main.py detection)
    proj_agents = project_root / ".opencode" / "agents"
    proj_backup = project_root / ".opencode" / "agents-go-backup"
    proj_installed = _install_agents_to_dir(proj_agents, assignments, proj_backup)

    # Also install to global agents (for opencode --agent resolution)
    global_installed = _install_agents_to_dir(GLOBAL_AGENTS_DIR, assignments, GLOBAL_BACKUP_DIR)

    installed = proj_installed or global_installed

    # Save plan.json in project
    plan_path = project_root / ".opencode" / "plan.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump({"plan": "lmstudio"}, f)

    # Update global OpenCode config with LM Studio provider
    ensure_global_lmstudio_config(installed)

    return {
        "installed": installed,
        "count": len(installed),
        "backup_dir": str(proj_backup),
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
    Restore Go agents from backup in both project and global dirs.
    Removes LM Studio plan.json. Returns status dict.
    """
    proj_agents = project_root / ".opencode" / "agents"
    proj_backup = project_root / ".opencode" / "agents-go-backup"
    plan_path = project_root / ".opencode" / "plan.json"

    proj_restored = _restore_agents_from_backup(proj_agents, proj_backup)
    global_restored = _restore_agents_from_backup(GLOBAL_AGENTS_DIR, GLOBAL_BACKUP_DIR)

    restored = proj_restored or global_restored

    if plan_path.exists():
        plan_path.unlink()

    return {
        "restored": restored,
        "proj_restored": proj_restored,
        "global_restored": global_restored,
        "backup_existed": proj_backup.exists(),
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
