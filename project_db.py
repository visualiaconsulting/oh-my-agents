"""
project_db.py — SQLite-based project database manager for oh-my-agents

Manages session continuity across OpenCode multi-agent sessions using a
SQLite database stored at .opencode/project.db within each project directory.

Provides structured storage for session records, file change tracking,
error logging, command history, and project-level metadata to enable
continuity between agent invocations.
"""
import json
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from utils import generate_session_id, format_timestamp, truncate_text


# ── ISO timestamp helper ────────────────────────────────────────────────────

def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 timestamp string."""
    return datetime.now(timezone.utc).isoformat()


# ── SQL schema ──────────────────────────────────────────────────────────────

SCHEMA_SQL = """
-- Project identity and aggregate state
CREATE TABLE IF NOT EXISTS project_meta (
    id              INTEGER PRIMARY KEY,
    project_hash    TEXT UNIQUE NOT NULL,
    project_path    TEXT NOT NULL,
    project_name    TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    last_active_at  TEXT NOT NULL,
    total_sessions  INTEGER DEFAULT 0,
    total_files_changed INTEGER DEFAULT 0,
    total_errors    INTEGER DEFAULT 0,
    current_branch  TEXT DEFAULT '',
    state_snapshot  TEXT DEFAULT '{}'
);

-- Individual session records
CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT UNIQUE NOT NULL,
    timestamp       TEXT NOT NULL,
    end_timestamp   TEXT DEFAULT '',
    agent           TEXT DEFAULT '',
    summary         TEXT DEFAULT '',
    log_file        TEXT DEFAULT '',
    exit_code       INTEGER DEFAULT -1,
    duration_seconds REAL DEFAULT 0.0,
    raw_log_preview TEXT DEFAULT '',
    pending_tasks   TEXT DEFAULT '[]',
    decisions       TEXT DEFAULT '[]',
    git_diff_summary TEXT DEFAULT ''
);

-- Per-session file change tracking
CREATE TABLE IF NOT EXISTS files_changed (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    filepath        TEXT NOT NULL,
    change_type     TEXT NOT NULL DEFAULT 'modified',
    timestamp       TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- Per-session error records
CREATE TABLE IF NOT EXISTS errors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    error_message   TEXT NOT NULL,
    severity        TEXT NOT NULL DEFAULT 'error',
    line_number     INTEGER DEFAULT -1,
    timestamp       TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- Per-session command execution log
CREATE TABLE IF NOT EXISTS commands (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    command         TEXT NOT NULL,
    exit_code       INTEGER DEFAULT -1,
    duration_ms     INTEGER DEFAULT 0,
    timestamp       TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_sessions_timestamp ON sessions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_files_changed_session ON files_changed(session_id);
CREATE INDEX IF NOT EXISTS idx_errors_session ON errors(session_id);
CREATE INDEX IF NOT EXISTS idx_commands_session ON commands(session_id);
"""


# ── ProjectDB class ─────────────────────────────────────────────────────────

class ProjectDB:
    """SQLite-backed database manager for project-level session continuity.

    The database is stored at ``.opencode/project.db`` under the given
    *project_root*.  All methods use parameterized queries and proper
    connection management (``with`` context for cursors, WAL journal mode).

    Usage::

        db = ProjectDB(Path("/path/to/project"))
        db.initialize_schema()
        db.ensure_project_meta()
        session_id = db.save_session({...})
        last = db.get_last_session()
        context = db.inject_context()
        continuity = db.get_continuity_prompt()
        db.close()
    """

    def __init__(self, project_root: Path):
        """Open (or create) the SQLite database.

        Creates the ``.opencode`` directory under *project_root* if it does
        not already exist, then opens a connection to ``project.db`` within it.
        WAL journal mode is enabled for better concurrent read/write behaviour.
        """
        self.project_root = project_root.resolve()
        self.opencode_dir = self.project_root / ".opencode"
        self.opencode_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.opencode_dir / "project.db"
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row

        # Enable WAL mode for better concurrent access
        self._conn.execute("PRAGMA journal_mode=WAL;")
        # Enable foreign key enforcement
        self._conn.execute("PRAGMA foreign_keys=ON;")

    # ── Schema ──────────────────────────────────────────────────────────

    def initialize_schema(self):
        """Create all tables and indexes if they do not already exist.

        Safe to call multiple times — uses ``CREATE TABLE IF NOT EXISTS``
        and ``CREATE INDEX IF NOT EXISTS`` throughout.
        """
        with self._conn:
            self._conn.executescript(SCHEMA_SQL)

    # ── Project metadata ────────────────────────────────────────────────

    def _compute_project_hash(self) -> str:
        """Return a 12-character SHA-256 hash of the absolute project path."""
        raw = str(self.project_root).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:12]

    def ensure_project_meta(self):
        """Ensure a ``project_meta`` row exists for this project.

        Creates the row on first invocation; updates ``last_active_at`` on
        subsequent calls so it stays current.
        """
        project_hash = self._compute_project_hash()
        now = _now_iso()

        with self._conn:
            row = self._conn.execute(
                "SELECT id FROM project_meta WHERE project_hash = ?",
                (project_hash,),
            ).fetchone()

            if row is None:
                # Detect current git branch (best-effort)
                branch = ""
                try:
                    import subprocess
                    result = subprocess.run(
                        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                        capture_output=True,
                        text=True,
                        cwd=self.project_root,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        branch = result.stdout.strip()
                except Exception:
                    branch = ""

                self._conn.execute(
                    """INSERT INTO project_meta
                       (project_hash, project_path, project_name,
                        created_at, last_active_at, current_branch)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        project_hash,
                        str(self.project_root),
                        self.project_root.name,
                        now,
                        now,
                        branch,
                    ),
                )
            else:
                self._conn.execute(
                    "UPDATE project_meta SET last_active_at = ? WHERE project_hash = ?",
                    (now, project_hash),
                )

    # ── Session CRUD ────────────────────────────────────────────────────

    def save_session(self, session_data: dict) -> str:
        """Persist a session record and all related sub-records.

        Expected keys in *session_data*:

        ==================  =============================================
        Key                 Description
        ==================  =============================================
        ``session_id``      8-char UUID (auto-generated if missing)
        ``timestamp``        ISO-format start time
        ``agent``            Agent name (e.g. ``"orchestrator"``)
        ``summary``          Free-text summary
        ``log_file``         Path to raw log file
        ``exit_code``        Process exit code
        ``duration_seconds`` Wall-clock duration
        ``raw_log_preview``  First 2000 chars of log output
        ``pending_tasks``    List of task strings
        ``decisions``        List of decision strings
        ``end_timestamp``    ISO-format end time
        ``git_diff_summary`` Brief git diff description
        ``files_changed``    List of dicts with keys ``filepath``,
                             ``change_type``
        ``errors``           List of dicts with keys ``error_message``,
                             ``severity``, ``line_number``
        ``commands``         List of dicts with keys ``command``,
                             ``exit_code``, ``duration_ms``
        ==================  =============================================

        Returns the ``session_id`` used.
        """
        sid = session_data.get("session_id") or generate_session_id()
        ts = session_data.get("timestamp") or _now_iso()
        end_ts = session_data.get("end_timestamp", "")
        agent = session_data.get("agent", "")
        summary = session_data.get("summary", "")
        log_file = session_data.get("log_file", "")
        exit_code = session_data.get("exit_code", -1)
        duration = session_data.get("duration_seconds", 0.0)
        raw_preview = session_data.get("raw_log_preview", "")[:2000]

        pending = json.dumps(session_data.get("pending_tasks", []))
        decisions = json.dumps(session_data.get("decisions", []))
        git_diff = session_data.get("git_diff_summary", "")

        files_changed = session_data.get("files_changed", [])
        errors_in = session_data.get("errors", [])
        commands_in = session_data.get("commands", [])

        with self._conn:
            # Insert or replace the session row
            self._conn.execute(
                """INSERT OR REPLACE INTO sessions
                   (session_id, timestamp, end_timestamp, agent, summary,
                    log_file, exit_code, duration_seconds, raw_log_preview,
                    pending_tasks, decisions, git_diff_summary)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    sid, ts, end_ts, agent, summary,
                    log_file, exit_code, duration, raw_preview,
                    pending, decisions, git_diff,
                ),
            )

            # Insert associated file changes
            for fc in files_changed:
                if isinstance(fc, dict):
                    self._conn.execute(
                        """INSERT INTO files_changed
                           (session_id, filepath, change_type, timestamp)
                           VALUES (?, ?, ?, ?)""",
                        (
                            sid,
                            fc.get("filepath", ""),
                            fc.get("change_type", "modified"),
                            fc.get("timestamp", ts),
                        ),
                    )
                elif isinstance(fc, str):
                    # Accept plain strings as filepaths with default change_type
                    self._conn.execute(
                        """INSERT INTO files_changed
                           (session_id, filepath, change_type, timestamp)
                           VALUES (?, ?, ?, ?)""",
                        (sid, fc, "modified", ts),
                    )

            # Insert associated errors
            for err in errors_in:
                if isinstance(err, dict):
                    self._conn.execute(
                        """INSERT INTO errors
                           (session_id, error_message, severity, line_number, timestamp)
                           VALUES (?, ?, ?, ?, ?)""",
                        (
                            sid,
                            err.get("error_message", str(err)),
                            err.get("severity", "error"),
                            err.get("line_number", -1),
                            err.get("timestamp", ts),
                        ),
                    )
                elif isinstance(err, str):
                    self._conn.execute(
                        """INSERT INTO errors
                           (session_id, error_message, severity, line_number, timestamp)
                           VALUES (?, ?, ?, ?, ?)""",
                        (sid, err, "error", -1, ts),
                    )

            # Insert associated commands
            for cmd in commands_in:
                if isinstance(cmd, dict):
                    self._conn.execute(
                        """INSERT INTO commands
                           (session_id, command, exit_code, duration_ms, timestamp)
                           VALUES (?, ?, ?, ?, ?)""",
                        (
                            sid,
                            cmd.get("command", ""),
                            cmd.get("exit_code", -1),
                            cmd.get("duration_ms", 0),
                            cmd.get("timestamp", ts),
                        ),
                    )
                elif isinstance(cmd, str):
                    self._conn.execute(
                        """INSERT INTO commands
                           (session_id, command, exit_code, duration_ms, timestamp)
                           VALUES (?, ?, ?, ?, ?)""",
                        (sid, cmd, -1, 0, ts),
                    )

            # Update project meta aggregate counts
            self._update_project_counts()

        return sid

    def _update_project_counts(self):
        """Recalculate and persist aggregate counts from the sessions table.

        Called internally after saving a session.
        """
        project_hash = self._compute_project_hash()
        row = self._conn.execute(
            """SELECT COUNT(*) AS total_sessions,
                      COALESCE(SUM(files_cnt), 0) AS total_files_changed,
                      COALESCE(SUM(errors_cnt), 0) AS total_errors
               FROM (
                   SELECT s.session_id,
                          (SELECT COUNT(*) FROM files_changed f WHERE f.session_id = s.session_id) AS files_cnt,
                          (SELECT COUNT(*) FROM errors e WHERE e.session_id = s.session_id) AS errors_cnt
                   FROM sessions s
               )""",
        ).fetchone()

        self._conn.execute(
            """UPDATE project_meta
               SET total_sessions = ?,
                   total_files_changed = ?,
                   total_errors = ?
               WHERE project_hash = ?""",
            (
                row["total_sessions"] if row else 0,
                row["total_files_changed"] if row else 0,
                row["total_errors"] if row else 0,
                project_hash,
            ),
        )

    # ── Session queries ─────────────────────────────────────────────────

    def _row_to_session_dict(self, row: sqlite3.Row) -> dict:
        """Convert a ``sessions`` row (with sub-records) to a rich dictionary.

        Deserialises JSON columns and attaches ``files_changed``, ``errors``,
        and ``commands`` lists.
        """
        if row is None:
            return {}

        sid = row["session_id"]
        result = dict(row)

        # Deserialise JSON fields
        for json_col in ("pending_tasks", "decisions"):
            try:
                result[json_col] = json.loads(result.get(json_col) or "[]")
            except (json.JSONDecodeError, TypeError):
                result[json_col] = []

        # Attach sub-records
        with self._conn:
            result["files_changed"] = [
                dict(r) for r in self._conn.execute(
                    "SELECT * FROM files_changed WHERE session_id = ? ORDER BY id",
                    (sid,),
                ).fetchall()
            ]
            result["errors"] = [
                dict(r) for r in self._conn.execute(
                    "SELECT * FROM errors WHERE session_id = ? ORDER BY id",
                    (sid,),
                ).fetchall()
            ]
            result["commands"] = [
                dict(r) for r in self._conn.execute(
                    "SELECT * FROM commands WHERE session_id = ? ORDER BY id",
                    (sid,),
                ).fetchall()
            ]

        return result

    def get_last_session(self) -> Optional[dict]:
        """Return the most recent session with all related data.

        Returns ``None`` if no sessions exist.
        """
        with self._conn:
            row = self._conn.execute(
                "SELECT * FROM sessions ORDER BY timestamp DESC LIMIT 1",
            ).fetchone()
        return self._row_to_session_dict(row) if row else None

    def get_session(self, session_id: str) -> Optional[dict]:
        """Return a specific session (including files/errors/commands) by ID.

        Returns ``None`` if the session is not found.
        """
        with self._conn:
            row = self._conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return self._row_to_session_dict(row) if row else None

    def list_sessions(self, limit: int = 20) -> list[dict]:
        """Return recent sessions ordered by most recent first.

        Each entry includes aggregate counts for files, errors, and commands
        rather than the full sub-record lists.
        """
        with self._conn:
            rows = self._conn.execute(
                """SELECT s.*,
                          (SELECT COUNT(*) FROM files_changed f WHERE f.session_id = s.session_id) AS files_count,
                          (SELECT COUNT(*) FROM errors e WHERE e.session_id = s.session_id) AS errors_count,
                          (SELECT COUNT(*) FROM commands c WHERE c.session_id = s.session_id) AS commands_count
                   FROM sessions s
                   ORDER BY s.timestamp DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()

        sessions = []
        for row in rows:
            entry = dict(row)
            for json_col in ("pending_tasks", "decisions"):
                try:
                    entry[json_col] = json.loads(entry.get(json_col) or "[]")
                except (json.JSONDecodeError, TypeError):
                    entry[json_col] = []
            sessions.append(entry)

        return sessions

    # ── Project state ───────────────────────────────────────────────────

    def get_project_state(self) -> dict:
        """Return the ``project_meta`` row with all aggregate statistics.

        Returns a dict with keys: ``project_hash``, ``project_path``,
        ``project_name``, ``created_at``, ``last_active_at``,
        ``total_sessions``, ``total_files_changed``, ``total_errors``,
        ``current_branch``, ``state_snapshot``.
        """
        project_hash = self._compute_project_hash()
        with self._conn:
            row = self._conn.execute(
                "SELECT * FROM project_meta WHERE project_hash = ?",
                (project_hash,),
            ).fetchone()

        if row is None:
            return {}

        result = dict(row)
        try:
            result["state_snapshot"] = json.loads(result.get("state_snapshot") or "{}")
        except (json.JSONDecodeError, TypeError):
            result["state_snapshot"] = {}

        return result

    # ── File tracking ───────────────────────────────────────────────────

    def get_files_changed_since(self, since_session_id: str) -> list[str]:
        """Return all distinct file paths changed since *since_session_id*.

        "Since" means sessions whose timestamp is strictly later than the
        timestamp of the reference session.  Returns relative file paths.
        """
        with self._conn:
            ref = self._conn.execute(
                "SELECT timestamp FROM sessions WHERE session_id = ?",
                (since_session_id,),
            ).fetchone()

        if ref is None:
            return []

        with self._conn:
            rows = self._conn.execute(
                """SELECT DISTINCT f.filepath
                   FROM files_changed f
                   JOIN sessions s ON s.session_id = f.session_id
                   WHERE s.timestamp > ?
                   ORDER BY f.filepath""",
                (ref["timestamp"],),
            ).fetchall()

        return [r["filepath"] for r in rows]

    # ── Task management ─────────────────────────────────────────────────

    def get_pending_tasks(self) -> list[str]:
        """Return all pending tasks from the most recent session.

        Returns an empty list if there is no session or no pending tasks.
        """
        last = self.get_last_session()
        if not last:
            return []
        return last.get("pending_tasks", [])

    def mark_task_complete(self, task_index: int) -> bool:
        """Remove the task at *task_index* (0-based) from the last session.

        Persists the change back to the database.

        Returns ``True`` if the task was removed, ``False`` if the index is
        out of range or no session exists.
        """
        last = self.get_last_session()
        if not last:
            return False

        tasks = last.get("pending_tasks", [])
        if task_index < 0 or task_index >= len(tasks):
            return False

        removed = tasks.pop(task_index)

        with self._conn:
            self._conn.execute(
                "UPDATE sessions SET pending_tasks = ? WHERE session_id = ?",
                (json.dumps(tasks), last["session_id"]),
            )

        return True

    # ── Context & continuity ────────────────────────────────────────────

    def inject_context(self, max_sessions: int = 3) -> str:
        """Generate a markdown-formatted context string from recent sessions.

        This is designed for injection into ``context.md``.  Includes
        session summaries, file/error counts, and pending tasks for the
        *max_sessions* most recent sessions.
        """
        sessions = self.list_sessions(limit=max_sessions)
        if not sessions:
            return ""

        lines = []
        lines.append("## Recent Session History")
        lines.append("")

        for i, session in enumerate(sessions, 1):
            ts = session.get("timestamp", "unknown")
            agent = session.get("agent", "unknown")
            summary = truncate_text(session.get("summary", ""), 300)
            errors_count = session.get("errors_count", 0)
            files_count = session.get("files_count", 0)
            pending = session.get("pending_tasks", [])

            lines.append(f"### Session {i} — {ts} (agent: @{agent})")
            lines.append("")
            if summary:
                lines.append(f"**Summary:** {summary}")
                lines.append("")
            if errors_count:
                lines.append(f"**Errors:** {errors_count} issue(s)")
                lines.append("")
            if files_count:
                lines.append(f"**Files changed:** {files_count}")
                lines.append("")
            if pending:
                lines.append("**Pending tasks:**")
                for task in pending:
                    lines.append(f"- [ ] {truncate_text(task, 120)}")
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def get_continuity_prompt(self) -> str:
        """Generate a concise continuity prompt describing the last session.

        Includes:
        * Project name and current branch
        * Last session summary
        * Pending tasks
        * Files changed in the last session
        * Errors encountered

        Returns an empty string if there are no sessions.
        """
        state = self.get_project_state()
        last = self.get_last_session()

        if not last:
            return ""

        lines = []
        lines.append("## Session Continuity")
        lines.append("")
        lines.append(
            f"- **Project:** {state.get('project_name', 'unknown')}"
        )
        branch = state.get("current_branch", "")
        if branch:
            lines.append(f"- **Branch:** `{branch}`")
        lines.append(
            f"- **Last session:** {last.get('timestamp', 'unknown')}"
        )
        lines.append(
            f"- **Agent:** @{last.get('agent', 'unknown')}"
        )

        summary = last.get("summary", "")
        if summary:
            lines.append(f"- **Summary:** {truncate_text(summary, 300)}")
            lines.append("")

        pending = last.get("pending_tasks", [])
        if pending:
            lines.append("**Pending tasks:**")
            for task in pending:
                lines.append(f"- [ ] {truncate_text(task, 120)}")
            lines.append("")

        files_changed = last.get("files_changed", [])
        if files_changed:
            lines.append("**Files changed in last session:**")
            for fc in files_changed[:10]:
                fp = fc.get("filepath", "") if isinstance(fc, dict) else str(fc)
                ct = fc.get("change_type", "") if isinstance(fc, dict) else ""
                marker = ct or "modified"
                lines.append(f"- `{fp}` ({marker})")
            if len(files_changed) > 10:
                lines.append(f"  *...and {len(files_changed) - 10} more*")
            lines.append("")

        errors_list = last.get("errors", [])
        if errors_list:
            lines.append("**Errors from last session:**")
            for err in errors_list[:5]:
                msg = (
                    err.get("error_message", str(err))
                    if isinstance(err, dict)
                    else str(err)
                )
                lines.append(f"- {truncate_text(msg, 200)}")
            if len(errors_list) > 5:
                lines.append(f"  *...and {len(errors_list) - 5} more*")
            lines.append("")

        lines.append("---")
        lines.append("")

        return "\n".join(lines)

    # ── Maintenance ─────────────────────────────────────────────────────

    def vacuum(self):
        """Optimise the database by reclaiming unused space.

        Should be called periodically (e.g. after many session deletions or
        bulk updates) to keep the database file compact and query-performant.
        """
        with self._conn:
            self._conn.execute("VACUUM;")

    def close(self):
        """Close the database connection.

        Always call this when you are done with the database to ensure
        pending writes are flushed and the connection is released.
        """
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── Context manager support ─────────────────────────────────────────

    def __enter__(self):
        """Support ``with ProjectDB(...) as db:`` usage."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure the connection is closed on context exit."""
        self.close()
        return False
