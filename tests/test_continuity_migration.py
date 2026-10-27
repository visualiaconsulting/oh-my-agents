"""Exercise legacy database recovery and honest multi-agent provenance."""

import json
import sqlite3
from unittest.mock import patch

import pytest

from continuity import ContinuityManager
from project_db import ProjectDB, SCHEMA_SQL, SCHEMA_VERSION


LEGACY_SESSIONS_SQL = """
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    timestamp TEXT NOT NULL,
    end_timestamp TEXT DEFAULT '',
    agent TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    log_file TEXT DEFAULT '',
    exit_code INTEGER DEFAULT -1,
    duration_seconds REAL DEFAULT 0.0,
    raw_log_preview TEXT DEFAULT '',
    pending_tasks TEXT DEFAULT '[]',
    decisions TEXT DEFAULT '[]',
    git_diff_summary TEXT DEFAULT ''
);
"""


def legacy_connection(root):
    """Keep committed data in a live WAL to exercise a consistent backup."""
    directory = root / ".opencode"
    directory.mkdir(parents=True)
    connection = sqlite3.connect(str(directory / "project.db"))
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA wal_autocheckpoint=0")
    connection.executescript(LEGACY_SESSIONS_SQL)
    connection.executescript(SCHEMA_SQL)
    with connection:
        connection.execute(
            "INSERT INTO sessions(session_id, timestamp, agent, summary, pending_tasks) VALUES (?, ?, ?, ?, ?)",
            ("legacy", "2026-07-19T10:00:00Z", "python-engineer", "Original session", '["Finish migration"]'),
        )
        connection.execute(
            "INSERT INTO files_changed(session_id, filepath, timestamp) VALUES (?, ?, ?)",
            ("legacy", "original.py", "2026-07-19T10:00:00Z"),
        )
    return connection


def test_migration_preserves_legacy_session_and_wal_backup(tmp_path):
    legacy = legacy_connection(tmp_path)
    try:
        with ProjectDB(tmp_path) as db:
            session = db.get_session("legacy")
            assert session["summary"] == "Original session"
            assert session["files_changed"][0]["filepath"] == "original.py"
            assert session["pending_tasks"] == ["Finish migration"]
            assert session["runtime"] == "opencode"
            assert session["role"] == "python-engineer"
            assert session["status"] == "partial"
            assert session["checks"] == []
            assert db.last_backup_path.is_file()
            with sqlite3.connect(str(db.last_backup_path)) as recovery:
                columns = {row[1] for row in recovery.execute("PRAGMA table_info(sessions)")}
                assert "runtime" not in columns
                assert recovery.execute("SELECT summary FROM sessions WHERE session_id='legacy'").fetchone()[0] == "Original session"
                assert recovery.execute("SELECT filepath FROM files_changed").fetchone()[0] == "original.py"
                assert recovery.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert db._conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
            db.initialize_schema()
            assert len(list(db.opencode_dir.glob("project.pre-codex-v2-*.db"))) == 1
    finally:
        legacy.close()
    with ProjectDB(tmp_path) as reopened:
        assert reopened.last_backup_path is None
        assert len(list(reopened.opencode_dir.glob("project.pre-codex-v2-*.db"))) == 1


def test_backup_is_restorable_to_another_project(tmp_path):
    original_root = tmp_path / "original"
    with legacy_connection(original_root):
        with ProjectDB(original_root) as db:
            recovery_path = db.last_backup_path
    restored_root = tmp_path / "restored"
    restored_dir = restored_root / ".opencode"
    restored_dir.mkdir(parents=True)
    with sqlite3.connect(str(recovery_path)) as source:
        with sqlite3.connect(str(restored_dir / "project.db")) as destination:
            source.backup(destination)
    with ProjectDB(restored_root) as restored:
        assert restored.get_session("legacy")["summary"] == "Original session"
        assert restored.get_session("legacy")["files_changed"][0]["filepath"] == "original.py"


def test_backup_failure_prevents_schema_migration(tmp_path):
    legacy = legacy_connection(tmp_path)
    connect = sqlite3.connect

    def refuse_backup(path, *args, **kwargs):
        if "pre-codex-v2" in str(path):
            raise OSError("Recovery directory unavailable")
        return connect(path, *args, **kwargs)

    try:
        with patch("project_db.sqlite3.connect", side_effect=refuse_backup):
            with pytest.raises(OSError, match="Recovery directory"):
                ProjectDB(tmp_path)
        assert "runtime" not in {row[1] for row in legacy.execute("PRAGMA table_info(sessions)")}
        assert legacy.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1
    finally:
        legacy.close()


def test_new_database_has_no_migration_backup(tmp_path):
    with ProjectDB(tmp_path) as db:
        assert db.last_backup_path is None
        assert not list(db.opencode_dir.glob("project.pre-codex-v2-*.db"))
        db.ensure_project_meta()
        session_id = db.save_session({"summary": "Legacy caller still works"})
        assert db.get_session(session_id)["status"] == "partial"


def test_newer_database_schema_is_not_downgraded(tmp_path):
    with ProjectDB(tmp_path) as db:
        db._conn.execute(f"PRAGMA user_version={SCHEMA_VERSION + 1}")
    with pytest.raises(ValueError, match="newer than supported"):
        ProjectDB(tmp_path)


def test_metadata_round_trip_and_partial_verification(tmp_path):
    with ProjectDB(tmp_path) as db:
        db.ensure_project_meta()
        sid = db.save_session({
            "runtime": "codex",
            "profile": "chatgpt",
            "model": "gpt-6.1-sol",
            "role": "coder",
            "task_id": "implementation",
            "parent_task_id": "feature",
            "summary": "Implementation saved; tests remain pending",
            "decisions": ["Retain Go compatibility"],
            "evidence": ["src/example.py", {"path": "tests/example.py", "kind": "regression"}],
            "checks": [{"command": "pytest tests/example.py"}],
        })
        saved = db.get_session(sid)
        assert saved["agent"] == "coder"
        assert saved["role"] == "coder"
        assert saved["model"] == "gpt-6.1-sol"
        assert saved["parent_task_id"] == "feature"
        assert saved["status"] == "partial"
        assert saved["checks"][0]["status"] == "not_run"
        assert db.list_sessions()[0]["evidence"] == saved["evidence"]
        for context in (db.get_continuity_prompt(), db.inject_context()):
            assert "gpt-6.1-sol" in context
            assert "chatgpt" in context
            assert "partial" in context
            assert "not_run" in context
            assert "tests/example.py" in context
            assert "Parent task" in context
        assert "Retain Go compatibility" in db.get_continuity_prompt()


@pytest.mark.parametrize("metadata", [
    {"runtime": "unknown"},
    {"model": None},
    {"status": "verified_by_assumption"},
    {"evidence": "not a list"},
    {"evidence": [{"not_json": float("nan")}]},
    {"checks": ["pytest"]},
    {"checks": [{"status": "passed"}]},
    {"checks": [{"name": "tests", "status": "unknown"}]},
    {"checks": [{"name": "tests", "status": []}]},
])
def test_invalid_metadata_is_rejected_before_writing(tmp_path, metadata):
    with ProjectDB(tmp_path) as db:
        with pytest.raises(ValueError):
            db.save_session(metadata)
        assert db.list_sessions() == []


def test_resaving_session_replaces_snapshot_without_foreign_key_loss(tmp_path):
    with ProjectDB(tmp_path) as db:
        db.ensure_project_meta()
        db.save_session({
            "session_id": "stable",
            "files_changed": ["old.py"],
            "errors": ["Earlier failure"],
            "commands": ["pytest old.py"],
        })
        original_id = db.get_session("stable")["id"]
        db.save_session({
            "session_id": "stable",
            "runtime": "codex",
            "role": "coder",
            "status": "completed",
            "files_changed": ["new.py"],
            "checks": [{"name": "Regression", "status": "passed"}],
        })
        saved = db.get_session("stable")
        assert saved["id"] == original_id
        assert [entry["filepath"] for entry in saved["files_changed"]] == ["new.py"]
        assert saved["errors"] == []
        assert saved["commands"] == []
        assert db.get_project_state()["total_sessions"] == 1
        assert db.get_project_state()["total_files_changed"] == 1
        assert db.get_project_state()["total_errors"] == 0


def test_continuity_reopens_legacy_database_and_marks_missing_checks_unknown(tmp_path):
    legacy = legacy_connection(tmp_path)
    legacy.close()
    with ContinuityManager(tmp_path) as continuity:
        prompt = continuity.get_reentry_prompt()
        assert "Original session" in prompt
        assert "verification is unknown" in prompt
        assert continuity.db.last_backup_path.is_file()


def test_continuity_bounds_evidence_and_checks(tmp_path):
    with ProjectDB(tmp_path) as db:
        db.save_session({
            "evidence": [f"evidence-{number}" for number in range(20)],
            "checks": [{"name": f"check-{number}", "status": "not_run"} for number in range(20)],
        })
        prompt = db.get_continuity_prompt()
        assert "evidence-4" in prompt
        assert "evidence-5" not in prompt
        assert "check-7" in prompt
        assert "check-8" not in prompt
        assert "15 more recorded items" in prompt
        assert "12 more recorded items" in prompt
        assert json.loads(db._conn.execute("SELECT checks FROM sessions").fetchone()[0])[19]["name"] == "check-19"
