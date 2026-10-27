"""Install reviewed, revision-pinned design skills into a project's Codex catalog.

Downloads text only. No upstream installer or other remote code is executed.
"""
import hashlib
import json
import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent


def _inside(root, relative):
    path = root / relative
    try:
        path.resolve().relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Skill path escapes project: {relative}") from exc
    if path.is_symlink():
        raise ValueError(f"Refusing a skill symlink: {relative}")
    return path


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".oma-skill-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def install_design_skills(project_root, dry_run=False):
    """Install only the two locked skills; preview does not download or write.

    Verify Git blob IDs of every fetched file before writing. A modified skill
    is a conflict. All previous files are backed up and rolled back on failure.
    """
    root = Path(project_root).resolve()
    lock = json.loads((ROOT / "design-skills.lock.json").read_text(encoding="utf-8"))
    manifest_rel = ".oh-my-agents/design-skills.json"
    manifest_path = _inside(root, manifest_rel)
    previous = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    if not isinstance(previous, dict) or not isinstance(previous.get("files", {}), dict):
        raise ValueError("Invalid design skill ownership manifest")
    contents, sources, files = {}, [], []
    for skill in lock["skills"]:
        if not re.fullmatch(r"[a-z0-9-]+", skill["name"]):
            raise ValueError("Invalid skill name in lock")
        if not re.fullmatch(r"[a-f0-9]{40}", skill["revision"]):
            raise ValueError("Skill revision must be a pinned commit")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", skill["repository"]):
            raise ValueError("Invalid skill repository")
        sources.append({k: skill[k] for k in ("name", "repository", "revision", "license")})
        for item in skill["files"]:
            if item["destination"] not in ("SKILL.md", "LICENSE.txt", "LICENSE", "LICENSE.md"):
                raise ValueError("Skill destination must be a skill or license basename")
            relative = f".agents/skills/{skill['name']}/{item['destination']}"
            path = _inside(root, relative)
            files.append({"path": relative, "action": "verify" if path.exists() else "install"})
            if dry_run:
                continue
            url = f"https://raw.githubusercontent.com/{skill['repository']}/{skill['revision']}/{item['path']}"
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            data = response.content
            blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
            if blob != item["git_blob_sha1"]:
                raise ValueError(f"Upstream skill checksum mismatch: {relative}")
            data.decode("utf-8")
            existing = path.read_bytes() if path.exists() else None
            if existing is not None and existing != data:
                expected = previous.get("files", {}).get(relative)
                if hashlib.sha256(existing).hexdigest() != expected:
                    raise ValueError(f"Preserved customized skill; resolve conflict first: {relative}")
            contents[relative] = data
            files[-1]["action"] = "unchanged" if existing == data else ("update" if existing else "install")
    report = {"dry_run": dry_run, "skills": sources, "files": files}
    if dry_run:
        return report
    contents[manifest_rel] = (json.dumps({"skills": sources, "files": {
        path: hashlib.sha256(data).hexdigest() for path, data in contents.items()
    }}, indent=2) + "\n").encode("utf-8")
    changes = {p: data for p, data in contents.items()
               if not _inside(root, p).exists() or _inside(root, p).read_bytes() != data}
    if not changes:
        return report
    before = {}
    backup = _inside(root, f".oh-my-agents/backups/design-skills/{uuid.uuid4().hex}")
    for relative in changes:
        path = _inside(root, relative)
        before[relative] = path.read_bytes() if path.exists() else None
        if path.exists():
            target = backup / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    try:
        for relative, data in changes.items():
            _write(_inside(root, relative), data)
    except Exception:
        for relative, data in before.items():
            path = _inside(root, relative)
            if data is None:
                if path.exists():
                    path.unlink()
            else:
                _write(path, data)
        raise
    if any(data is not None for data in before.values()):
        report["backup"] = str(backup)
    return report
