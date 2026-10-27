"""Pinned skill installation with fake downloads and no external network."""

import hashlib
import json
from unittest.mock import MagicMock

import pytest
import requests

import design_skills


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


@pytest.fixture
def locked_skills(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    blobs = {"SKILL.md": b"# A reviewed design skill\n", "LICENSE.txt": b"Example license\n"}
    lock = {"schema_version": 1, "skills": [{
        "name": "example-design",
        "repository": "example/skills",
        "revision": "a" * 40,
        "license": "Example",
        "files": [{"path": f"skills/example-design/{name}", "destination": name,
                   "git_blob_sha1": git_blob(data)} for name, data in blobs.items()],
    }]}
    filename = source / "design-skills.lock.json"
    filename.write_text(json.dumps(lock), encoding="utf-8")
    monkeypatch.setattr(design_skills, "ROOT", source)

    def fetch(url, **kwargs):
        assert url.startswith("https://raw.githubusercontent.com/example/skills/" + "a" * 40 + "/")
        response = MagicMock()
        response.content = blobs[url.rsplit("/", 1)[-1]]
        return response

    request = MagicMock(side_effect=fetch)
    monkeypatch.setattr(design_skills.requests, "get", request)
    return filename, lock, blobs, request


def test_preview_writes_nothing_and_does_not_download(tmp_path, locked_skills):
    _, _, _, request = locked_skills
    root = tmp_path / "project"
    report = design_skills.install_design_skills(root, dry_run=True)
    assert report["dry_run"] is True
    assert not root.exists()
    request.assert_not_called()


def test_install_checks_git_blobs_and_is_idempotent(tmp_path, locked_skills):
    _, _, blobs, request = locked_skills
    root = tmp_path / "project"
    report = design_skills.install_design_skills(root)
    assert all(item["action"] == "install" for item in report["files"])
    for filename, data in blobs.items():
        assert (root / ".agents/skills/example-design" / filename).read_bytes() == data
    manifest = root / ".oh-my-agents/design-skills.json"
    assert json.loads(manifest.read_text())["files"][".agents/skills/example-design/SKILL.md"] == hashlib.sha256(blobs["SKILL.md"]).hexdigest()
    before = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    report = design_skills.install_design_skills(root)
    assert all(item["action"] == "unchanged" for item in report["files"])
    assert before == {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    assert not (root / ".oh-my-agents/backups").exists()
    assert request.call_count == 4


def test_checksum_mismatch_prevents_any_project_write(tmp_path, locked_skills):
    _, _, blobs, _ = locked_skills
    blobs["LICENSE.txt"] = b"Tampered content\n"
    root = tmp_path / "project"
    with pytest.raises(ValueError, match="checksum mismatch"):
        design_skills.install_design_skills(root)
    assert not root.exists()


def test_all_downloads_finish_before_any_write(tmp_path, locked_skills):
    _, _, _, request = locked_skills
    request.side_effect = [MagicMock(content=b"# A reviewed design skill\n"), requests.Timeout("Second download failed")]
    root = tmp_path / "project"
    with pytest.raises(requests.Timeout):
        design_skills.install_design_skills(root)
    assert not root.exists()


def test_customized_skill_is_preserved_without_partial_update(tmp_path, locked_skills):
    filename, lock, blobs, _ = locked_skills
    root = tmp_path / "project"
    design_skills.install_design_skills(root)
    customized = root / ".agents/skills/example-design/LICENSE.txt"
    customized.write_bytes(b"My customized license note\n")
    skill = root / ".agents/skills/example-design/SKILL.md"
    before = skill.read_bytes()
    blobs["SKILL.md"] = b"# Updated upstream skill\n"
    lock["skills"][0]["files"][0]["git_blob_sha1"] = git_blob(blobs["SKILL.md"])
    filename.write_text(json.dumps(lock), encoding="utf-8")
    with pytest.raises(ValueError, match="customized skill"):
        design_skills.install_design_skills(root)
    assert customized.read_bytes() == b"My customized license note\n"
    assert skill.read_bytes() == before


@pytest.mark.parametrize("destination", [
    "../../../../outside.txt", "../../../README.md", "/absolute.txt", "C:\\absolute.txt",
])
def test_invalid_skill_destination_rejected_in_preview(tmp_path, locked_skills, destination):
    filename, lock, _, request = locked_skills
    lock["skills"][0]["files"][0]["destination"] = destination
    filename.write_text(json.dumps(lock), encoding="utf-8")
    root = tmp_path / "project"
    with pytest.raises(ValueError):
        design_skills.install_design_skills(root, dry_run=True)
    assert not root.exists()
    request.assert_not_called()


def test_write_failure_restores_previous_skill_files(tmp_path, locked_skills, monkeypatch):
    filename, lock, blobs, _ = locked_skills
    root = tmp_path / "project"
    design_skills.install_design_skills(root)
    skill = root / ".agents/skills/example-design/SKILL.md"
    manifest = root / ".oh-my-agents/design-skills.json"
    old_skill, old_manifest = skill.read_bytes(), manifest.read_bytes()
    blobs["SKILL.md"] = b"# New pinned revision\n"
    lock["skills"][0]["files"][0]["git_blob_sha1"] = git_blob(blobs["SKILL.md"])
    filename.write_text(json.dumps(lock), encoding="utf-8")
    original = design_skills._write
    calls = 0

    def fail_second(path, data):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("Disk unavailable")
        return original(path, data)

    monkeypatch.setattr(design_skills, "_write", fail_second)
    with pytest.raises(OSError, match="Disk unavailable"):
        design_skills.install_design_skills(root)
    assert skill.read_bytes() == old_skill
    assert manifest.read_bytes() == old_manifest


def test_malformed_ownership_manifest_is_rejected_before_download(tmp_path, locked_skills):
    _, _, _, request = locked_skills
    root = tmp_path / "project"
    directory = root / ".oh-my-agents"
    directory.mkdir(parents=True)
    (directory / "design-skills.json").write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        design_skills.install_design_skills(root)
    request.assert_not_called()
    assert not (root / ".agents").exists()
