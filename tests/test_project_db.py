"""
Tests for project_db.py, continuity.py, and auto-session features.

Covers:
- ProjectDB: SQLite-backed session database with schema init, CRUD, queries
- ContinuityManager: Project re-entry, status banners, health reports
- Utils: Hash generation, log parsing, auto-session flags, git branch
"""
import os
import sys
import json
import shutil
import tempfile
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from project_db import ProjectDB
from continuity import ContinuityManager
from utils import (
    generate_project_hash,
    get_project_db_path,
    parse_openCode_log_content,
    get_auto_session_flag_path,
    is_auto_session_enabled,
    get_current_git_branch,
)


# ---------------------------------------------------------------------------
# Module-level fixture — clean temp directory for this module
# (overrides conftest.py temp_project so we get a truly clean slate)
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_project():
    """Create an empty temporary directory for isolated testing.

    Unlike conftest.py's ``temp_project``, this does NOT pre-create
    any agents or context files — the tests themselves set up whatever
    structure they need.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# ===================================================================
# TestProjectDB
# ===================================================================

class TestProjectDB:
    """Tests for the SQLite project database manager."""

    @pytest.fixture
    def db(self, temp_project):
        """Create a *fully initialised* ProjectDB instance.

        Calls ``initialize_schema()`` and ``ensure_project_meta()`` so
        that all tables and the project_meta row exist before any test
        method runs.
        """
        _db = ProjectDB(temp_project)
        _db.initialize_schema()
        _db.ensure_project_meta()
        yield _db
        _db.close()

    # ── Initialisation & meta ────────────────────────────────────────

    def test_init_creates_db_file(self, temp_project):
        """``__init__`` should create ``.opencode/project.db``."""
        db_path = temp_project / ".opencode" / "project.db"
        assert not db_path.exists()
        db = ProjectDB(temp_project)
        try:
            assert db_path.exists()
            assert db_path.is_file()
            assert db_path.stat().st_size > 0
        finally:
            db.close()

    def test_init_creates_opencode_dir(self, temp_project):
        """``__init__`` should create the ``.opencode`` parent directory."""
        opencode_dir = temp_project / ".opencode"
        assert not opencode_dir.exists()
        db = ProjectDB(temp_project)
        try:
            assert opencode_dir.is_dir()
        finally:
            db.close()

    def test_initialize_schema_creates_tables(self, temp_project):
        """All five tables and indexes should exist after schema init."""
        db = ProjectDB(temp_project)
        try:
            db.initialize_schema()
            # Query sqlite_master for each expected table
            tables = [
                "project_meta",
                "sessions",
                "files_changed",
                "errors",
                "commands",
            ]
            for table in tables:
                row = db._conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                ).fetchone()
                assert row is not None, f"Table '{table}' was not created"
        finally:
            db.close()

    def test_initialize_schema_idempotent(self, temp_project):
        """Calling ``initialize_schema`` multiple times should not error."""
        db = ProjectDB(temp_project)
        try:
            db.initialize_schema()
            db.initialize_schema()  # second call
            db.initialize_schema()  # third call
        finally:
            db.close()

    def test_ensure_project_meta(self, db, temp_project):
        """``ensure_project_meta`` creates a row with the correct hash."""
        state = db.get_project_state()
        assert state is not None, "get_project_state() returned None"
        assert state["project_name"] == temp_project.name
        expected_hash = generate_project_hash(temp_project)
        assert state["project_hash"] == expected_hash
        assert "created_at" in state
        assert "last_active_at" in state
        assert state["total_sessions"] == 0

    def test_project_hash_stable_across_instances(self, temp_project):
        """Two different ``ProjectDB`` instances should agree on the hash."""
        db1 = ProjectDB(temp_project)
        db1.initialize_schema()
        db1.ensure_project_meta()
        hash1 = db1._compute_project_hash()
        db1.close()

        db2 = ProjectDB(temp_project)
        db2.initialize_schema()
        db2.ensure_project_meta()
        hash2 = db2._compute_project_hash()
        db2.close()

        assert hash1 == hash2

    # ── Session CRUD ─────────────────────────────────────────────────

    def test_save_and_retrieve_session(self, db):
        """Saving a session with all fields and retrieving it."""
        session_data = {
            "session_id": "test1234",
            "timestamp": "2026-05-13 10:00:00",
            "agent": "orchestrator",
            "summary": "Test session summary",
            "log_file": "/tmp/test.log",
            "exit_code": 0,
            "duration_seconds": 120.5,
            "raw_log_preview": "Test log content",
            "pending_tasks": ["task1", "task2"],
            "decisions": ["decision1"],
            "files_changed": [
                {"filepath": "src/main.py", "change_type": "modified"},
                {"filepath": "tests/test.py", "change_type": "created"},
            ],
            "errors": [
                {"error_message": "Test error", "severity": "error"},
            ],
            "commands": [
                {"command": "pytest", "exit_code": 0, "duration_ms": 500},
            ],
        }

        session_id = db.save_session(session_data)
        assert session_id == "test1234"

        # Verify project_meta was updated
        state = db.get_project_state()
        assert state["total_sessions"] == 1
        assert state["total_errors"] == 1
        assert state["total_files_changed"] == 2

        # Retrieve and verify
        retrieved = db.get_session("test1234")
        assert retrieved is not None
        assert retrieved["agent"] == "orchestrator"
        assert retrieved["summary"] == "Test session summary"
        assert len(retrieved["files_changed"]) == 2
        assert len(retrieved["errors"]) == 1
        assert len(retrieved["pending_tasks"]) == 2
        assert retrieved["pending_tasks"] == ["task1", "task2"]

    def test_save_session_generates_id(self, db):
        """If no ``session_id`` is provided, one should be auto-generated."""
        sid = db.save_session({
            "timestamp": "2026-05-13 10:00:00",
            "agent": "test",
            "summary": "Auto-ID test",
            "log_file": "",
            "exit_code": 0,
            "duration_seconds": 0,
            "raw_log_preview": "",
            "pending_tasks": [],
            "decisions": [],
            "files_changed": [],
            "errors": [],
            "commands": [],
        })
        assert sid is not None
        assert len(sid) == 8  # generate_session_id produces 8-char IDs

    def test_save_session_string_lists(self, db):
        """Sub-records can be plain strings (not just dicts)."""
        sid = db.save_session({
            "session_id": "strlist01",
            "timestamp": "2026-05-13 10:00:00",
            "agent": "test",
            "summary": "String list test",
            "log_file": "",
            "exit_code": 0,
            "duration_seconds": 0,
            "raw_log_preview": "",
            "pending_tasks": [],
            "decisions": [],
            "files_changed": [
                "src/plain.txt",
                "data/raw.csv",
            ],
            "errors": [
                "Something went wrong",
                "Another error",
            ],
            "commands": [
                "npm test",
                "python run.py",
            ],
        })
        assert sid == "strlist01"

        retrieved = db.get_session("strlist01")
        assert retrieved is not None
        assert len(retrieved["files_changed"]) == 2
        assert len(retrieved["errors"]) == 2
        assert len(retrieved["commands"]) == 2

    def test_get_session_not_found(self, db):
        """``get_session`` should return ``None`` for a non-existent ID."""
        assert db.get_session("nonexistent") is None

    def test_get_last_session_empty(self, db):
        """``get_last_session`` should return ``None`` when no sessions."""
        # Remove any auto-created sessions — the db fixture only has meta
        last = db.get_last_session()
        assert last is None

    # ── Session listing ───────────────────────────────────────────────

    def test_list_sessions(self, db):
        """Sessions should be listed most-recent-first."""
        for i in range(5):
            db.save_session({
                "session_id": f"sess{i:04d}",
                "timestamp": f"2026-05-13 1{i}:00:00",
                "agent": "orchestrator",
                "summary": f"Session {i}",
                "log_file": f"/tmp/test{i}.log",
                "exit_code": 0,
                "duration_seconds": 60.0,
                "raw_log_preview": f"Log {i}",
                "pending_tasks": [],
                "decisions": [],
                "files_changed": [],
                "errors": [],
                "commands": [],
            })

        sessions = db.list_sessions(limit=3)
        assert len(sessions) == 3
        assert sessions[0]["session_id"] == "sess0004"
        assert sessions[1]["session_id"] == "sess0003"
        assert sessions[2]["session_id"] == "sess0002"

    def test_list_sessions_respects_limit(self, db):
        """``limit`` should cap the number of returned sessions."""
        for i in range(10):
            db.save_session({
                "session_id": f"lim{i:03d}",
                "timestamp": f"2026-05-13 1{i}:00:00",
                "agent": "test",
                "summary": "",
                "log_file": "",
                "exit_code": 0,
                "duration_seconds": 0,
                "raw_log_preview": "",
                "pending_tasks": [],
                "decisions": [],
                "files_changed": [],
                "errors": [],
                "commands": [],
            })

        assert len(db.list_sessions(limit=5)) == 5
        assert len(db.list_sessions(limit=20)) == 10

    def test_list_sessions_empty(self, db):
        """``list_sessions`` on an empty db should return an empty list."""
        assert db.list_sessions() == []

    # ── Session ordering ──────────────────────────────────────────────

    def test_get_last_session(self, db):
        """``get_last_session`` should return the most recent session."""
        db.save_session({
            "session_id": "older001",
            "timestamp": "2026-05-13 10:00:00",
            "agent": "orchestrator",
            "summary": "Older session",
            "log_file": "/tmp/old.log",
            "exit_code": 0,
            "duration_seconds": 60.0,
            "raw_log_preview": "old",
            "pending_tasks": [],
            "decisions": [],
            "files_changed": [],
            "errors": [],
            "commands": [],
        })
        db.save_session({
            "session_id": "newer001",
            "timestamp": "2026-05-13 11:00:00",
            "agent": "python-engineer",
            "summary": "Newer session",
            "log_file": "/tmp/new.log",
            "exit_code": 0,
            "duration_seconds": 60.0,
            "raw_log_preview": "new",
            "pending_tasks": [],
            "decisions": [],
            "files_changed": [],
            "errors": [],
            "commands": [],
        })

        last = db.get_last_session()
        assert last is not None
        assert last["agent"] == "python-engineer"
        assert last["summary"] == "Newer session"
        assert last["session_id"] == "newer001"

    # ── Pending tasks ─────────────────────────────────────────────────

    def test_pending_tasks(self, db):
        """Tasks should be retrievable and individually completable."""
        db.save_session({
            "session_id": "tasktest1",
            "timestamp": "2026-05-13 10:00:00",
            "agent": "orchestrator",
            "summary": "Task test",
            "log_file": "/tmp/task.log",
            "exit_code": 0,
            "duration_seconds": 60.0,
            "raw_log_preview": "tasks",
            "pending_tasks": ["Fix bug #1", "Add feature X", "Update docs"],
            "decisions": [],
            "files_changed": [],
            "errors": [],
            "commands": [],
        })

        tasks = db.get_pending_tasks()
        assert len(tasks) == 3
        assert "Fix bug #1" in tasks

        # Mark a task complete
        assert db.mark_task_complete(0) is True

        tasks = db.get_pending_tasks()
        assert len(tasks) == 2
        assert "Fix bug #1" not in tasks

    def test_mark_task_complete_invalid_index(self, db):
        """``mark_task_complete`` with an out-of-range index returns False."""
        db.save_session({
            "session_id": "invtest",
            "timestamp": "2026-05-13 10:00:00",
            "agent": "test",
            "summary": "Invalid index test",
            "log_file": "",
            "exit_code": 0,
            "duration_seconds": 0,
            "raw_log_preview": "",
            "pending_tasks": ["Only task"],
            "decisions": [],
            "files_changed": [],
            "errors": [],
            "commands": [],
        })
        assert db.mark_task_complete(-1) is False
        assert db.mark_task_complete(5) is False

    def test_get_pending_tasks_no_session(self, db):
        """Getting pending tasks without any session returns empty list."""
        # db fixture created meta but no sessions yet
        assert db.get_pending_tasks() == []

    # ── Files changed ─────────────────────────────────────────────────

    def test_files_changed_since(self, db):
        """``get_files_changed_since`` returns distinct files after a ref
        session."""
        db.save_session({
            "session_id": "base_sess",
            "timestamp": "2026-05-13 10:00:00",
            "agent": "orchestrator",
            "summary": "Base session",
            "log_file": "/tmp/base.log",
            "exit_code": 0,
            "duration_seconds": 60.0,
            "raw_log_preview": "base",
            "pending_tasks": [],
            "decisions": [],
            "files_changed": [
                {"filepath": "src/base.py", "change_type": "created"},
            ],
            "errors": [],
            "commands": [],
        })
        db.save_session({
            "session_id": "next_sess",
            "timestamp": "2026-05-13 11:00:00",
            "agent": "python-engineer",
            "summary": "Next session",
            "log_file": "/tmp/next.log",
            "exit_code": 0,
            "duration_seconds": 60.0,
            "raw_log_preview": "next",
            "pending_tasks": [],
            "decisions": [],
            "files_changed": [
                {"filepath": "src/next.py", "change_type": "modified"},
                {"filepath": "src/base.py", "change_type": "modified"},
            ],
            "errors": [],
            "commands": [],
        })

        files = db.get_files_changed_since("base_sess")
        # Should include files from sessions after base_sess
        assert len(files) >= 1
        assert "src/next.py" in files
        # base.py was also modified in next_sess
        assert "src/base.py" in files

    def test_files_changed_since_nonexistent(self, db):
        """Passing a non-existent session ID returns an empty list."""
        assert db.get_files_changed_since("ghost_sess") == []

    # ── Context & continuity prompts ──────────────────────────────────

    def test_inject_context(self, db):
        """``inject_context`` should produce markdown with session details."""
        db.save_session({
            "session_id": "ctx_test1",
            "timestamp": "2026-05-13 10:00:00",
            "agent": "orchestrator",
            "summary": "Context test session",
            "log_file": "/tmp/ctx.log",
            "exit_code": 0,
            "duration_seconds": 60.0,
            "raw_log_preview": "context",
            "pending_tasks": ["Important pending task"],
            "decisions": ["Key decision made"],
            "files_changed": [
                {"filepath": "src/main.py", "change_type": "modified"},
            ],
            "errors": [{"error_message": "Minor issue", "severity": "warning"}],
            "commands": [],
        })

        context = db.inject_context(max_sessions=1)
        assert "Context test session" in context
        assert "Important pending task" in context
        assert "## Recent Session History" in context
        assert "@orchestrator" in context

    def test_inject_context_empty(self, db):
        """``inject_context`` with no sessions returns empty string."""
        assert db.inject_context() == ""

    def test_get_continuity_prompt(self, db):
        """``get_continuity_prompt`` includes tasks, files, and errors."""
        db.save_session({
            "session_id": "cont_test",
            "timestamp": "2026-05-13 10:00:00",
            "agent": "orchestrator",
            "summary": "Continuity test",
            "log_file": "/tmp/cont.log",
            "exit_code": 0,
            "duration_seconds": 60.0,
            "raw_log_preview": "continuity",
            "pending_tasks": ["Task A", "Task B"],
            "decisions": [],
            "files_changed": [
                {"filepath": "src/feature.py", "change_type": "created"},
            ],
            "errors": [],
            "commands": [],
        })

        prompt = db.get_continuity_prompt()
        assert "Task A" in prompt
        assert "Task B" in prompt
        assert "feature.py" in prompt
        assert "## Session Continuity" in prompt

    def test_get_continuity_prompt_empty(self, db):
        """``get_continuity_prompt`` with no sessions returns empty string."""
        assert db.get_continuity_prompt() == ""

    # ── Edge cases ────────────────────────────────────────────────────

    def test_save_empty_session(self, db):
        """Saving a session with only mandatory fields should not error."""
        sid = db.save_session({
            "session_id": "empty001",
            "timestamp": "2026-05-13 10:00:00",
            "agent": "",
            "summary": "",
            "log_file": "",
            "exit_code": -1,
            "duration_seconds": 0.0,
            "raw_log_preview": "",
            "pending_tasks": [],
            "decisions": [],
            "files_changed": [],
            "errors": [],
            "commands": [],
        })
        assert sid == "empty001"

        retrieved = db.get_session("empty001")
        assert retrieved is not None
        assert retrieved["files_changed"] == []
        assert retrieved["errors"] == []
        assert retrieved["commands"] == []

    def test_vacuum_does_not_error(self, db):
        """``vacuum`` should run without raising."""
        # Even on an empty database vacuum must succeed
        db.vacuum()

    def test_close_twice(self, db):
        """Calling ``close()`` twice should be safe."""
        db.close()
        db.close()  # second call — should be a no-op

    def test_context_manager(self, temp_project):
        """``with ProjectDB(...) as db:`` should work and auto-close."""
        with ProjectDB(temp_project) as db:
            db.initialize_schema()
            db.ensure_project_meta()
            assert db.db_path.exists()
        # After exit the connection should be closed
        assert db._conn is None


# ===================================================================
# TestContinuityManager
# ===================================================================

class TestContinuityManager:
    """Tests for the ContinuityManager."""

    def test_new_project_has_no_history(self, temp_project):
        """A project with no sessions has no history."""
        cm = ContinuityManager(temp_project)
        try:
            assert cm.is_new_project() is True
            assert cm.has_history() is False
        finally:
            cm.close()

    def test_new_project_last_session_is_none(self, temp_project):
        """``get_last_session`` returns None for a new project."""
        cm = ContinuityManager(temp_project)
        try:
            assert cm.get_last_session() is None
        finally:
            cm.close()

    def test_reentry_prompt_empty_for_new_project(self, temp_project):
        """``get_reentry_prompt`` returns '' for a new project."""
        cm = ContinuityManager(temp_project)
        try:
            assert cm.get_reentry_prompt() == ""
        finally:
            cm.close()

    def test_status_banner_empty_for_new_project(self, temp_project):
        """``get_status_banner`` returns '' for a new project."""
        cm = ContinuityManager(temp_project)
        try:
            banner = cm.get_status_banner()
            assert banner == ""
        finally:
            cm.close()

    def test_enable_disable_auto_session(self, temp_project):
        """Enabling then disabling the auto-session flag."""
        cm = ContinuityManager(temp_project)

        # Initially disabled
        assert is_auto_session_enabled(temp_project) is False

        # Enable
        assert cm.enable_auto_session() is True
        assert is_auto_session_enabled(temp_project) is True

        flag_path = get_auto_session_flag_path(temp_project)
        assert flag_path.exists()
        content = flag_path.read_text()
        assert "Auto-session saving enabled" in content

        # Disable
        assert cm.disable_auto_session() is True
        assert is_auto_session_enabled(temp_project) is False
        assert not flag_path.exists()

        cm.close()

    def test_enable_twice_is_idempotent(self, temp_project):
        """Calling ``enable_auto_session`` twice should not error."""
        cm = ContinuityManager(temp_project)
        try:
            assert cm.enable_auto_session() is True
            assert cm.enable_auto_session() is True
            assert is_auto_session_enabled(temp_project) is True
        finally:
            cm.close()

    def test_disable_when_not_enabled(self, temp_project):
        """Disabling auto-session when not enabled returns True."""
        cm = ContinuityManager(temp_project)
        try:
            assert cm.disable_auto_session() is True
        finally:
            cm.close()

    def test_project_health_new_project(self, temp_project):
        """Health report for a brand-new project."""
        cm = ContinuityManager(temp_project)
        try:
            health = cm.get_project_health()
            assert health["health_status"] == "new_project"
            assert health["total_sessions"] == 0
            assert health["total_errors"] == 0
            assert health["total_files_changed"] == 0
            assert health["last_active"] == "never"
            assert health["pending_tasks"] == 0
            assert health["open_errors"] == 0
        finally:
            cm.close()

    def test_project_health_with_sessions(self, temp_project):
        """Health report after sessions have been recorded."""
        # Save a session via a direct ProjectDB (must init schema)
        db = ProjectDB(temp_project)
        db.initialize_schema()
        db.ensure_project_meta()
        db.save_session({
            "session_id": "health001",
            "timestamp": "2026-05-13 10:00:00",
            "agent": "orchestrator",
            "summary": "Health test",
            "log_file": "/tmp/health.log",
            "exit_code": 0,
            "duration_seconds": 60.0,
            "raw_log_preview": "health",
            "pending_tasks": ["task1"],
            "decisions": [],
            "files_changed": [{"filepath": "src/x.py", "change_type": "modified"}],
            "errors": [{"error_message": "e1", "severity": "error"}],
            "commands": [],
        })
        db.close()

        cm = ContinuityManager(temp_project)
        try:
            assert cm.has_history() is True
            assert cm.is_new_project() is False

            health = cm.get_project_health()
            assert health["total_sessions"] == 1
            assert health["total_errors"] >= 1
            assert health["total_files_changed"] >= 1
            assert health["pending_tasks"] == 1
            assert health["open_errors"] == 1
            assert health["health_status"] in ("healthy", "has_warnings", "needs_attention")
        finally:
            cm.close()

    def test_get_reentry_prompt(self, temp_project):
        """Re-entry prompt should contain pending tasks and file changes."""
        db = ProjectDB(temp_project)
        db.initialize_schema()
        db.ensure_project_meta()
        db.save_session({
            "session_id": "reentry01",
            "timestamp": "2026-05-13 10:00:00",
            "agent": "orchestrator",
            "summary": "Re-entry test session",
            "log_file": "/tmp/reentry.log",
            "exit_code": 0,
            "duration_seconds": 60.0,
            "raw_log_preview": "reentry",
            "pending_tasks": ["Critical task"],
            "decisions": [],
            "files_changed": [{"filepath": "src/main.py", "change_type": "modified"}],
            "errors": [],
            "commands": [],
        })
        db.close()

        cm = ContinuityManager(temp_project)
        try:
            prompt = cm.get_reentry_prompt()
            assert "Critical task" in prompt
            assert "main.py" in prompt
            assert "## Session Continuity" in prompt
        finally:
            cm.close()

    def test_get_reentry_prompt_with_errors(self, temp_project):
        """Re-entry prompt should include error details."""
        db = ProjectDB(temp_project)
        db.initialize_schema()
        db.ensure_project_meta()
        db.save_session({
            "session_id": "err_reentry",
            "timestamp": "2026-05-13 10:00:00",
            "agent": "python-engineer",
            "summary": "Session with errors",
            "log_file": "/tmp/err.log",
            "exit_code": 1,
            "duration_seconds": 30.0,
            "raw_log_preview": "ERROR: crash occurred",
            "pending_tasks": ["Fix critical bug"],
            "decisions": [],
            "files_changed": [],
            "errors": [
                {"error_message": "Crash in module X", "severity": "error"},
                {"error_message": "Deprecated API used", "severity": "warning"},
            ],
            "commands": [],
        })
        db.close()

        cm = ContinuityManager(temp_project)
        try:
            prompt = cm.get_reentry_prompt()
            assert "Crash in module X" in prompt
            assert "Deprecated API used" in prompt
        finally:
            cm.close()

    def test_get_status_banner(self, temp_project):
        """Status banner should show project name and summary stats."""
        db = ProjectDB(temp_project)
        db.initialize_schema()
        db.ensure_project_meta()
        db.save_session({
            "session_id": "banner001",
            "timestamp": "2026-05-13 10:00:00",
            "agent": "orchestrator",
            "summary": "Banner test",
            "log_file": "/tmp/banner.log",
            "exit_code": 0,
            "duration_seconds": 60.0,
            "raw_log_preview": "banner",
            "pending_tasks": ["task"],
            "decisions": [],
            "files_changed": [{"filepath": "src/app.py", "change_type": "modified"}],
            "errors": [],
            "commands": [],
        })
        db.close()

        cm = ContinuityManager(temp_project)
        try:
            banner = cm.get_status_banner()
            assert temp_project.name in banner
            assert "Sessions:" in banner
            assert "╔" in banner  # box-drawing character
            assert "╝" in banner
        finally:
            cm.close()

    def test_inject_context_to_file_no_history(self, temp_project):
        """``inject_context_to_file`` returns False when no history."""
        cm = ContinuityManager(temp_project)
        try:
            assert cm.inject_context_to_file() is False
        finally:
            cm.close()

    def test_inject_context_to_file_no_context_md(self, temp_project):
        """Returns False when ``context.md`` does not exist."""
        db = ProjectDB(temp_project)
        db.initialize_schema()
        db.ensure_project_meta()
        db.save_session({
            "session_id": "noctx001",
            "timestamp": "2026-05-13 10:00:00",
            "agent": "orchestrator",
            "summary": "Session without context.md",
            "log_file": "",
            "exit_code": 0,
            "duration_seconds": 0,
            "raw_log_preview": "",
            "pending_tasks": [],
            "decisions": [],
            "files_changed": [],
            "errors": [],
            "commands": [],
        })
        db.close()

        cm = ContinuityManager(temp_project)
        try:
            # context.md doesn't exist in this temp project
            assert cm.inject_context_to_file() is False
        finally:
            cm.close()

    def test_context_manager(self, temp_project):
        """``with ContinuityManager(...) as cm:`` should work."""
        with ContinuityManager(temp_project) as cm:
            assert cm.is_new_project() is True
        # After exit the db connection should be closed
        assert cm._db is None


# ===================================================================
# TestUtilsNew
# ===================================================================

class TestUtilsNew:
    """Tests for utility functions added for the project DB feature."""

    def test_get_project_db_path(self):
        """``get_project_db_path`` returns a ``.opencode/project.db`` path."""
        project_root = Path(tempfile.gettempdir()) / "test_proj_utils"
        project_root.mkdir(exist_ok=True)
        try:
            db_path = get_project_db_path(project_root)
            assert db_path.name == "project.db"
            assert ".opencode" in str(db_path)
            assert db_path.parent == project_root / ".opencode"
            assert db_path.parent.exists()  # creates the directory
        finally:
            shutil.rmtree(project_root, ignore_errors=True)

    def test_get_project_db_path_creates_opencode(self):
        """The ``.opencode`` parent directory should be created if missing."""
        project_root = Path(tempfile.gettempdir()) / "test_db_path_create"
        try:
            opencode_dir = project_root / ".opencode"
            assert not opencode_dir.exists()
            db_path = get_project_db_path(project_root)
            assert opencode_dir.is_dir()
            assert db_path.parent == opencode_dir
        finally:
            shutil.rmtree(project_root, ignore_errors=True)

    def test_generate_project_hash_deterministic(self):
        """Identical paths produce identical hashes."""
        project_root = Path(tempfile.gettempdir()) / "test_proj_hash"
        project_root.mkdir(exist_ok=True)
        try:
            hash1 = generate_project_hash(project_root)
            hash2 = generate_project_hash(project_root)
            assert hash1 == hash2
        finally:
            shutil.rmtree(project_root, ignore_errors=True)

    def test_generate_project_hash_length(self):
        """Hash should be exactly 12 characters long."""
        project_root = Path(tempfile.gettempdir()) / "test_proj_hash_len"
        project_root.mkdir(exist_ok=True)
        try:
            h = generate_project_hash(project_root)
            assert len(h) == 12
        finally:
            shutil.rmtree(project_root, ignore_errors=True)

    def test_generate_project_hash_different_paths(self):
        """Different paths should produce different hashes."""
        base = Path(tempfile.gettempdir())
        p1 = base / "proj_alpha"
        p2 = base / "proj_beta"
        p1.mkdir(exist_ok=True)
        p2.mkdir(exist_ok=True)
        try:
            h1 = generate_project_hash(p1)
            h2 = generate_project_hash(p2)
            assert h1 != h2
        finally:
            shutil.rmtree(p1, ignore_errors=True)
            shutil.rmtree(p2, ignore_errors=True)

    def test_parse_openCode_log_content_errors(self):
        """Log lines containing error/failure keywords are extracted."""
        import textwrap
        log = textwrap.dedent("""\
            Running: pytest tests/
            ERROR: test_failure in test_main.py
            WARNING: deprecated function used
            Modified: src/main.py
            Created: src/new_file.py
            $ npm install
            Summary: All tasks completed successfully.
        """)
        parsed = parse_openCode_log_content(log)
        assert len(parsed["errors"]) >= 1
        assert any("ERROR" in e for e in parsed["errors"])
        assert len(parsed["warnings"]) >= 1
        assert len(parsed["commands_run"]) >= 2
        # npm install and Running: pytest should both be detected
        commands_text = " ".join(parsed["commands_run"])
        assert "npm install" in commands_text
        assert "Running:" in commands_text

    def test_parse_openCode_log_content_files(self):
        """File change lines are detected and file paths extracted."""
        log = """
        Modified: src/services/api.py
        Created: tests/test_api.py
        Deleted: old/deprecated.py
        Wrote: docs/README.md
        """
        parsed = parse_openCode_log_content(log)
        assert len(parsed["files_changed"]) >= 3
        assert any("api.py" in f for f in parsed["files_changed"])
        assert any("test_api.py" in f for f in parsed["files_changed"])
        assert any("README.md" in f for f in parsed["files_changed"])

    def test_parse_openCode_log_content_deduplicates(self):
        """Duplicate file paths should be removed."""
        log = """
        Modified: src/main.py
        Modified: src/main.py
        Modified: src/main.py
        """
        parsed = parse_openCode_log_content(log)
        assert len(parsed["files_changed"]) == 1

    def test_parse_openCode_log_content_summary_hint(self):
        """The last 20 lines should be captured as summary_hint."""
        lines = [f"Line {i}" for i in range(30)]
        log = "\n".join(lines)
        parsed = parse_openCode_log_content(log)
        # summary_hint should have the last 20 lines
        assert "Line 10" in parsed["summary_hint"]
        assert "Line 29" in parsed["summary_hint"]

    def test_parse_openCode_log_content_empty(self):
        """Empty log content should return empty lists."""
        parsed = parse_openCode_log_content("")
        assert parsed["errors"] == []
        assert parsed["warnings"] == []
        assert parsed["files_changed"] == []
        assert parsed["commands_run"] == []
        assert parsed["summary_hint"] == ""

    def test_auto_session_flag_path(self, temp_project):
        """``get_auto_session_flag_path`` returns the correct flag path."""
        flag_path = get_auto_session_flag_path(temp_project)
        assert ".auto_session_enabled" in str(flag_path)
        assert flag_path.parent == temp_project / ".opencode"
        # Directory should not be created just by calling the path function
        assert not flag_path.parent.exists()

    def test_is_auto_session_enabled_false_by_default(self, temp_project):
        """A project without the flag should report disabled."""
        assert is_auto_session_enabled(temp_project) is False

    def test_is_auto_session_enabled_true_when_flag_exists(self, temp_project):
        """After creating the flag file, auto-session is enabled."""
        flag_path = get_auto_session_flag_path(temp_project)
        flag_path.parent.mkdir(parents=True, exist_ok=True)
        flag_path.write_text("enabled")
        assert is_auto_session_enabled(temp_project) is True

    def test_is_auto_session_enabled_after_flag_deleted(self, temp_project):
        """After deleting the flag file, auto-session is disabled again."""
        flag_path = get_auto_session_flag_path(temp_project)
        flag_path.parent.mkdir(parents=True, exist_ok=True)
        flag_path.write_text("enabled")
        assert is_auto_session_enabled(temp_project) is True
        flag_path.unlink()
        assert is_auto_session_enabled(temp_project) is False

    def test_get_current_git_branch(self):
        """``get_current_git_branch`` returns a non-empty branch name
        when run inside a git repository."""
        branch = get_current_git_branch()
        # This test runs inside the oh-my-agents repo (which has a .git)
        assert isinstance(branch, str)
        assert len(branch) > 0, (
            "Expected a git branch name but got empty string. "
            "Is the working directory inside a git repository?"
        )

    def test_get_current_git_branch_outside_repo(self, temp_project):
        """Outside a git repository the function returns empty string."""
        branch = get_current_git_branch(temp_project)
        assert branch == ""

    def test_get_current_git_branch_type(self):
        """Branch name should always be a string."""
        branch = get_current_git_branch()
        assert isinstance(branch, str)
