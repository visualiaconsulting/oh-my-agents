"""Export the shared catalog to native, project-scoped agent configuration."""
import hashlib
import json
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from agent_catalog import ROOT, ROLES, load_catalog, load_profile


def _digest(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _safe_path(root: Path, relative: str) -> Path:
    path = root / relative
    try:
        path.resolve().relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Export path escapes project: {relative}") from exc
    if path.is_symlink():
        raise ValueError(f"Export refuses symlink: {relative}")
    return path


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _atomic_write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".oma-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def export_runtime(project_root, runtime, profile=None, dry_run=False,
                   available_models=None, model_overrides=None, codex_compat=None):
    """Plan or apply a native export, preserving custom files and configuration.

    Returns a JSON-serializable report. Dry runs never create directories. Models
    are checked against an explicitly supplied inventory only; no API is called.
    Modified managed specialist files are conflicts, never silently overwritten.
    """
    if runtime not in ("codex", "opencode"):
        raise ValueError(f"Unsupported runtime: {runtime}")
    if codex_compat is not None and runtime != "codex":
        raise ValueError("codex_compat is only supported for the Codex runtime")
    if codex_compat is not None and codex_compat not in ("modern", "legacy"):
        raise ValueError("codex_compat must be modern or legacy")
    profile = profile or ("chatgpt" if runtime == "codex" else "go")
    settings = load_profile(profile)
    if settings["runtime"] != runtime:
        raise ValueError(f"Profile {profile} requires runtime {settings['runtime']}")
    if model_overrides:
        if set(model_overrides) - set(ROLES):
            raise ValueError("Model overrides contain unsupported roles")
        for role, model in model_overrides.items():
            if not isinstance(model, str) or not model:
                raise ValueError(f"Invalid model override for {role}")
            settings["models"][role]["model"] = model
    # Saved selections may replace every shipped default (notably LM Studio).
    # Validate the effective export after applying overrides, before any writes.
    if available_models is not None:
        missing = sorted({item["model"] for item in settings["models"].values()} - set(available_models))
        if missing:
            raise ValueError("Models absent from supplied inventory: " + ", ".join(missing))
    root = Path(project_root).resolve()
    manifest_rel = f".oh-my-agents/exports/{runtime}.json"
    manifest_path = _safe_path(root, manifest_rel)
    previous = json.loads(_read(manifest_path) or "{}")
    if not isinstance(previous, dict) or not isinstance(previous.get("files", {}), dict):
        raise ValueError("Invalid export ownership manifest")
    if runtime == "codex":
        effective_compat = codex_compat or previous.get("codex_compat", "modern")
        if effective_compat not in ("modern", "legacy"):
            raise ValueError("Invalid codex_compat in export ownership manifest")
        settings["codex_compat"] = effective_compat
        settings["previous_codex_compat"] = previous.get("codex_compat")
    # Validate paths before renderers read existing shared configuration.
    _safe_path(root, f".{runtime}/config.toml" if runtime == "codex" else ".opencode/plan.json")
    for path in root.glob("*"):
        if path.name.lower() == "agents.md":
            _safe_path(root, path.name)
    renderer = __import__(f"adapters.{runtime}", fromlist=["render_files"])
    contents = renderer.render_files(root, load_catalog(), settings)
    legacy = json.loads((ROOT / "agents" / "legacy-fingerprints.json").read_text(encoding="utf-8"))
    changes, warnings, conflicts = [], [], []
    if hasattr(renderer, "configuration_warnings"):
        warnings.extend(renderer.configuration_warnings(root))
    agent_prefix = ".codex/agents/" if runtime == "codex" else ".opencode/agents/"
    owned = previous.get("files", {})
    for relative, content in contents.items():
        existing = _read(_safe_path(root, relative))
        is_agent = relative.startswith(agent_prefix)
        original_hash = owned.get(relative)
        recognized_legacy = runtime == "opencode" and _digest(existing) == legacy.get(relative)
        if is_agent and existing and existing != content:
            if _digest(existing) != original_hash and not recognized_legacy:
                conflicts.append(relative)
        action = "unchanged" if existing == content else ("update" if existing else "create")
        changes.append({"path": relative, "action": action})
    archives = []
    agent_directory = _safe_path(root, agent_prefix)
    if agent_directory.exists():
        extension = "*.toml" if runtime == "codex" else "*.md"
        for path in sorted(agent_directory.glob(extension)):
            relative = path.relative_to(root).as_posix()
            if relative in contents:
                continue
            existing = _read(_safe_path(root, relative))
            known_hash = owned.get(relative) or (legacy.get(relative) if runtime == "opencode" else None)
            if known_hash and _digest(existing) == known_hash:
                archives.append(relative)
                changes.append({"path": relative, "action": "archive"})
            else:
                warnings.append(f"Preserved custom agent outside the five-role catalog: {relative}")
    if conflicts:
        raise ValueError("Custom or modified agent files would be overwritten: " + ", ".join(conflicts))
    report = {"runtime": runtime, "profile": profile, "dry_run": dry_run,
              "files": changes, "warnings": warnings,
              "changed": sum(c["action"] != "unchanged" for c in changes),
              "model_validation": "supplied_inventory" if available_models is not None else "configuration_only"}
    if runtime == "codex":
        report["codex_compat"] = effective_compat
    if dry_run:
        return report
    modified = [c["path"] for c in changes if c["action"] != "unchanged"]
    manifest_data = {"schema_version": 1, "runtime": runtime, "profile": profile,
                     "files": {p: _digest(c) for p, c in contents.items()}}
    if runtime == "codex":
        manifest_data["codex_compat"] = effective_compat
    new_manifest = json.dumps(manifest_data, indent=2) + "\n"
    if not modified and _read(manifest_path) == new_manifest:
        return report
    backup_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
    backup = _safe_path(root, f".oh-my-agents/backups/{runtime}/{backup_id}")
    before = {}
    for relative in modified + [manifest_rel]:
        path = _safe_path(root, relative)
        before[relative] = path.read_bytes() if path.exists() else None
        if path.exists():
            destination = backup / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
    try:
        for relative in modified:
            path = _safe_path(root, relative)
            if relative in archives:
                path.unlink()
            else:
                _atomic_write(path, contents[relative])
        _atomic_write(manifest_path, new_manifest)
    except Exception:
        for relative, original in before.items():
            path = _safe_path(root, relative)
            if original is None:
                if path.exists():
                    path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(original)
        raise
    if any(value is not None for value in before.values()):
        report["backup"] = str(backup)
    return report
