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
LMSTUDIO_SETTINGS = Path.home() / ".lmstudio" / "settings.json"
LMSTUDIO_PER_MODEL_CONFIG = Path.home() / ".lmstudio" / ".internal" / "user-concrete-model-default-config"
TARGET_CONTEXT_LENGTH = 32768

GLOBAL_OPENCODE_CONFIG = Path.home() / ".config" / "opencode" / "opencode.jsonc"
GLOBAL_AGENTS_DIR = Path.home() / ".opencode" / "agents"
GLOBAL_BACKUP_DIR = Path.home() / ".opencode" / "agents-go-backup"

ROLE_NAMES = [
    "orchestrator", "python-engineer", "db-architect", "structured-engineer",
    "docs-writer", "bulk-processor", "validator", "researcher",
    "frontend-engineer", "devops", "ml-specialist", "security-reviewer",
    "git-manager", "test-engineer", "prompt-engineer"
]

ROLE_DESCRIPTIONS = {
    "orchestrator":         "Main coordinator — delegates tasks to sub-agents",
    "python-engineer":      "Backend engineer — Python, FastAPI, automation, APIs",
    "db-architect":         "PostgreSQL specialist — schemas, queries, performance",
    "structured-engineer":  "JSON, YAML, OpenAPI, Docker Compose specialist",
    "docs-writer":          "Technical documentation writer",
    "bulk-processor":       "Bulk data processing and repetitive tasks",
    "validator":            "QA specialist — validates and reviews code",
    "researcher":           "Technical researcher — explores technologies",
    "frontend-engineer":    "UI/UX specialist — React, Next.js, Tailwind",
    "devops":               "Infrastructure — Docker, CI/CD, deployment",
    "ml-specialist":        "ML and data pipeline specialist",
    "security-reviewer":    "Security specialist — audits code and APIs",
    "git-manager":          "Git specialist — commits, branches, changelogs",
    "test-engineer":        "Testing specialist — pytest, unit/integration tests",
    "prompt-engineer":      "Prompt designer — AI agent instructions",
}

ROLE_PERMISSIONS = {
    "orchestrator":         {"edit": "deny",  "bash": "deny",  "read": "allow", "task": "allow"},
    "python-engineer":      {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
    "db-architect":         {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
    "structured-engineer":  {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
    "docs-writer":          {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
    "bulk-processor":       {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
    "validator":            {"edit": "deny",  "bash": "deny",  "read": "allow", "task": "deny"},
    "researcher":           {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
    "frontend-engineer":    {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
    "devops":               {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
    "ml-specialist":        {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
    "security-reviewer":    {"edit": "deny",  "bash": "deny",  "read": "allow", "task": "deny"},
    "git-manager":          {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
    "test-engineer":        {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
    "prompt-engineer":      {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
}

ROLE_TEMPERATURES = {
    "orchestrator": 0.2, "python-engineer": 0.2, "db-architect": 0.2,
    "structured-engineer": 0.2, "docs-writer": 0.3, "bulk-processor": 0.3,
    "validator": 0.1, "researcher": 0.3, "frontend-engineer": 0.3,
    "devops": 0.2, "ml-specialist": 0.2, "security-reviewer": 0.1,
    "git-manager": 0.2, "test-engineer": 0.2, "prompt-engineer": 0.3,
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


def _fetch_v0_models() -> List[Dict]:
    """Fetch models from LM Studio v0 API, which includes loaded_context_length."""
    try:
        req = urllib.request.Request(f"{LMSTUDIO_API_V0}/models", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []

    raw = data.get("data", [])
    models = []
    for m in raw:
        if m.get("type") == "embeddings":
            continue
        model_id = m.get("id", "")
        if not model_id:
            continue
        loaded = m.get("state") == "loaded"
        loaded_ctx = m.get("loaded_context_length", 0) if loaded else 0
        max_ctx = m.get("max_context_length", 0)
        models.append({
            "id": model_id,
            "display_name": _model_id_to_display(model_id),
            "publisher": m.get("publisher", ""),
            "arch": m.get("arch", ""),
            "quantization": m.get("quantization", ""),
            "loaded_context_length": loaded_ctx,
            "max_context_length": max_ctx,
            "state": m.get("state", "not-loaded"),
            "is_loaded": loaded,
            "capabilities": m.get("capabilities", []),
        })
    return models


def list_models() -> List[Dict]:
    """
    Fetch models from LM Studio API. Prefers v0 for loaded_context_length,
    falls back to v1 OpenAI-compatible endpoint.
    Returns list of LLM models with metadata, sorted by params (desc).
    """
    v0_models = _fetch_v0_models()

    if v0_models:
        raw_models = v0_models
    else:
        # Fallback: fetch from v1 endpoint (OpenAI-compatible)
        try:
            req = urllib.request.Request(f"{LMSTUDIO_BASE}/v1/models", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            raise ConnectionError(f"Cannot reach LM Studio at {LMSTUDIO_BASE}: {e}")

        raw_models = []
        for m in data.get("data", []):
            model_id = m.get("id", "")
            if not model_id:
                continue
            raw_models.append({
                "id": model_id,
                "display_name": _model_id_to_display(model_id),
                "publisher": m.get("owned_by", ""),
                "arch": "",
                "quantization": "",
                "loaded_context_length": 0,
                "max_context_length": 32768,
                "state": "unknown",
                "is_loaded": True,
                "capabilities": [],
            })

    llm_models = []
    for m in raw_models:
        model_id = m["id"]
        params_str = ""
        params = _parse_params(model_id)
        if params > 0:
            params_str = f"{params}B"

        ctx = m["loaded_context_length"] or m["max_context_length"] or 32768

        llm_models.append({
            "id": model_id,
            "display_name": m["display_name"],
            "publisher": m["publisher"],
            "arch": m["arch"],
            "quantization": m["quantization"],
            "params_string": params_str,
            "params": params,
            "max_context_length": ctx,
            "state": m["state"],
            "is_loaded": m["is_loaded"],
            "is_code": bool(re.search(r'code|coder|instruct', model_id, re.IGNORECASE)),
        })

    llm_models.sort(key=lambda m: (m["params"], m["max_context_length"], m["display_name"]), reverse=True)
    return llm_models


def auto_assign_roles(models: List[Dict]) -> List[Tuple[str, Dict]]:
    """
    Assign roles to models based on size ranking.
    Largest model -> orchestrator, 2nd -> python-engineer, etc.
    Returns list of (role, model_info) tuples.
    """
    if not models:
        return []

    # Boost code models for python-engineer role
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


def _update_per_model_configs() -> List[str]:
    """
    Update per-model context configs in user-concrete-model-default-config/.
    Returns list of files that were changed.
    """
    changed = []
    if not LMSTUDIO_PER_MODEL_CONFIG.exists():
        return changed

    for config_file in LMSTUDIO_PER_MODEL_CONFIG.rglob("*.json"):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        fields = cfg.get("load", {}).get("fields", [])
        updated = False
        for field in fields:
            if field.get("key") == "llm.load.contextLength":
                val = field.get("value", 0)
                if val < TARGET_CONTEXT_LENGTH:
                    field["value"] = TARGET_CONTEXT_LENGTH
                    updated = True
                break
        else:
            key = "llm.load.contextLength"
            if not any(f.get("key") == key for f in fields):
                fields.append({"key": key, "value": TARGET_CONTEXT_LENGTH})
                if "load" not in cfg:
                    cfg["load"] = {}
                cfg["load"]["fields"] = fields
                updated = True

        if updated:
            try:
                with open(config_file, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2, ensure_ascii=False)
                    f.write("\n")
                changed.append(config_file.name)
            except OSError:
                continue

    return changed


def ensure_lmstudio_context_length() -> Dict:
    """
    Update LM Studio's defaultContextLength (global + per-model) to 32768
    so models load with sufficient context for OpenCode prompts.
    Returns status dict with 'changed' (bool), 'message' (str), and 'updated_models' (list).
    """
    changed_global = False
    messages = []

    # 1. Update global settings.json
    if LMSTUDIO_SETTINGS.exists():
        try:
            with open(LMSTUDIO_SETTINGS, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            return {"changed": False, "message": f"Cannot read LM Studio settings: {e}", "updated_models": []}

        current = settings.get("defaultContextLength", {}).get("value", 0)
        if current < TARGET_CONTEXT_LENGTH:
            settings["defaultContextLength"] = {
                "type": "custom",
                "value": TARGET_CONTEXT_LENGTH,
            }
            try:
                with open(LMSTUDIO_SETTINGS, "w", encoding="utf-8") as f:
                    json.dump(settings, f, indent=2, ensure_ascii=False)
                    f.write("\n")
                messages.append(f"Global defaultContextLength: {current} -> {TARGET_CONTEXT_LENGTH}")
                changed_global = True
            except OSError as e:
                messages.append(f"Cannot write settings.json: {e}")
        else:
            messages.append(f"Global context already {current}")

    # 2. Update per-model configs
    changed_models = _update_per_model_configs()
    if changed_models:
        changed_global = True
        messages.append(f"Per-model configs updated: {', '.join(changed_models)}")

    if not changed_global:
        return {
            "changed": False,
            "message": "; ".join(messages),
            "updated_models": [],
        }

    return {
        "changed": True,
        "message": "; ".join(messages),
        "updated_models": changed_models,
    }


def _rmtree(path: Path):
    """Remove a directory tree, handling Windows permission errors."""
    def handle_error(func, fpath, exc_info):
        os.chmod(fpath, 0o777)
        func(fpath)
    shutil.rmtree(path, onerror=handle_error)


def _install_agents_to_dir(target_dir: Path, assignments: List[Tuple[str, Dict]], backup_dir: Path) -> List[Dict]:
    """Backup existing agents in target_dir, then write LM Studio agents."""
    if target_dir.exists() and not backup_dir.exists():
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
    2. Rank usable LLMs by size with code model boost for python-engineer
    3. Assign to priority roles in order, duplicating models if needed

    Priority order: orchestrator > python-engineer > db-architect > validator > ...
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

    # Assign in priority order (least critical roles at the end)
    least_critical = ["prompt-engineer", "git-manager", "docs-writer"]
    priority_roles = [r for r in ROLE_NAMES if r not in least_critical] + least_critical

    assignments = []
    used_models = {}  # role -> model

    for i, role in enumerate(priority_roles):
        if i < len(ranked):
            model = ranked[i]
        else:
            model = ranked[-1]  # duplicate the smallest usable model
        assignments.append((role, model))

    # Assign broken models (like Nemotron) to least critical roles
    if broken:
        for i in range(len(assignments) - 1, -1, -1):
            role, _ = assignments[i]
            if role in least_critical:
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

    # Ensure LM Studio loads models with sufficient context
    ctx_result = ensure_lmstudio_context_length()

    result = {
        "installed": installed,
        "count": len(installed),
        "backup_dir": str(proj_backup),
        "context": ctx_result,
    }
    return result


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

    # Clean up LM Studio provider from global OpenCode config
    config_path = _get_global_config_path()
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            modified = False
            if "provider" in config and "lmstudio" in config["provider"]:
                del config["provider"]["lmstudio"]
                modified = True
                if not config["provider"]:
                    del config["provider"]
            if modified:
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                    f.write("\n")
        except (json.JSONDecodeError, OSError):
            pass

    return {
        "restored": restored,
        "proj_restored": proj_restored,
        "global_restored": global_restored,
        "backup_existed": proj_backup.exists(),
    }


def get_status() -> Dict:
    """Get LM Studio status: running, models, assignments, context."""
    running = check_lmstudio_running()
    models = []
    error = None

    if running:
        try:
            models = list_models()
        except Exception as e:
            error = str(e)

    ctx = ensure_lmstudio_context_length()

    return {
        "running": running,
        "model_count": len(models),
        "models": models,
        "error": error,
        "context": ctx,
    }
