"""
session_manager.py — Session bitacora and continuity for oh-my-agents

Manages session logs, saves session summaries, and injects context
for continuity between OpenCode sessions.
"""
import re
from pathlib import Path
from typing import Optional

from utils import (
    get_sessions_dir,
    get_logs_dir,
    get_logs_dir_candidates,
    get_opencode_dir,
    generate_session_id,
    format_timestamp,
    safe_json_load,
    safe_json_save,
    truncate_text,
)

from project_db import ProjectDB


class SessionManager:
    """Manages session logs and continuity context."""

    def __init__(self, project_root: Optional[Path] = None, use_db: bool = False):
        self.project_root = project_root or Path(__file__).parent
        self.sessions_dir = get_sessions_dir(self.project_root)
        self.logs_dir = get_logs_dir(self.project_root)
        self.use_db = use_db
        self._db: Optional[ProjectDB] = None

    def _get_db(self) -> ProjectDB:
        """Lazy-load the project database."""
        if self._db is None:
            self._db = ProjectDB(self.project_root)
        return self._db

    def scan_logs(self) -> dict:
        """Scan OpenCode log directories for session data and extract key information.

        Searches all candidate log directories (project/.opencode/logs/,
        global ~/.opencode/logs/, APPDATA on Windows, etc.) and reads
        the single most recent *.log file found.

        Returns a dict with:
            - files_changed: list of file paths modified
            - errors: list of error messages found
            - warnings: list of warning messages found
            - commands_run: list of commands executed
            - raw_content: combined log text for summarization
            - log_source: path to the log file that was actually read
        """
        result = {
            "files_changed": [],
            "errors": [],
            "warnings": [],
            "commands_run": [],
            "raw_content": "",
            "log_source": "",
            "line_count": 0,
        }

        candidates = get_logs_dir_candidates(self.project_root)

        # Collect all *.log files from all candidate directories
        all_logs = []
        for candidate in candidates:
            all_logs.extend(
                (f, candidate) for f in candidate.glob("*.log")
            )

        if not all_logs:
            return result

        # Sort by modification time descending (most recent first)
        all_logs.sort(key=lambda item: item[0].stat().st_mtime, reverse=True)

        latest_log, _ = all_logs[0]
        try:
            with open(latest_log, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            return result

        result["raw_content"] = content
        result["log_source"] = str(latest_log)
        result["line_count"] = len(content.splitlines())

        for line in content.splitlines():
            if re.search(r"(error|exception|failed|failure)", line, re.IGNORECASE):
                result["errors"].append(line.strip())
            elif re.search(r"(warning|warn)", line, re.IGNORECASE):
                result["warnings"].append(line.strip())
            elif re.search(r"(modified|created|deleted|wrote|edited)", line, re.IGNORECASE):
                match = re.search(r"[\w./\\-]+\.\w+", line)
                if match:
                    result["files_changed"].append(match.group(0))
            elif re.match(r"\$\s+", line) or re.search(r"Running:\s+", line, re.IGNORECASE):
                result["commands_run"].append(line.strip())

        result["files_changed"] = list(set(result["files_changed"]))
        result["errors"] = result["errors"][:50]
        result["warnings"] = result["warnings"][:50]
        result["commands_run"] = result["commands_run"][:50]

        return result

    def save_session(
        self,
        agent: str = "unknown",
        summary: str = "",
        errors: Optional[list] = None,
        pending_tasks: Optional[list] = None,
        files_changed: Optional[list] = None,
        decisions: Optional[list] = None,
        log_data: Optional[dict] = None,
    ) -> str:
        """Save a session record to .opencode/sessions/.

        Returns the session ID.
        """
        session_id = generate_session_id()
        now = format_timestamp()

        if log_data is None:
            log_data = self.scan_logs()

        session = {
            "session_id": session_id,
            "timestamp": now,
            "agent": agent,
            "summary": summary,
            "errors": errors or log_data.get("errors", []),
            "pending_tasks": pending_tasks or [],
            "files_changed": files_changed or log_data.get("files_changed", []),
            "decisions": decisions or [],
            "commands_run": log_data.get("commands_run", []),
            "warnings": log_data.get("warnings", []),
        }

        filepath = self.sessions_dir / f"{session_id}.json"
        safe_json_save(filepath, session)

        # Also save to project database if enabled
        if self.use_db:
            db = self._get_db()
            db.ensure_project_meta()
            db_data = {
                "session_id": session_id,
                "timestamp": now,
                "agent": agent,
                "summary": summary,
                "pending_tasks": pending_tasks or [],
                "decisions": decisions or [],
                "files_changed": files_changed or log_data.get("files_changed", []),
                "errors": errors or log_data.get("errors", []),
                "commands": log_data.get("commands_run", []),
                "raw_log_preview": log_data.get("raw_content", "")[:2000] if log_data else "",
            }
            db.save_session(db_data)

        return session_id

    def save_session_db(self, session_data: dict) -> str:
        """Save a session directly to the project database. Returns session_id."""
        db = self._get_db()
        return db.save_session(session_data)

    def get_last_session(self) -> Optional[dict]:
        """Return the most recent session, or None."""
        sessions = self.list_sessions()
        if not sessions:
            return None
        return sessions[0]

    def get_session(self, session_id: str) -> Optional[dict]:
        """Return a specific session by ID."""
        filepath = self.sessions_dir / f"{session_id}.json"
        return safe_json_load(filepath)

    def list_sessions(self, limit: int = 20) -> list:
        """List sessions sorted by most recent first."""
        json_sessions = []
        if self.sessions_dir.exists():
            session_files = sorted(
                self.sessions_dir.glob("*.json"),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            for sf in session_files[:limit]:
                data = safe_json_load(sf)
                if data:
                    json_sessions.append(data)

        # If DB integration not enabled, return JSON sessions
        if not self.use_db:
            return json_sessions

        # Query DB and merge with JSON sessions
        db = self._get_db()
        db_sessions = db.list_sessions(limit=limit)

        # Merge: DB takes priority, deduplicate by session_id
        seen = set()
        merged = []

        for s in db_sessions:
            sid = s.get("session_id")
            if sid and sid not in seen:
                seen.add(sid)
                merged.append(s)

        for s in json_sessions:
            sid = s.get("session_id")
            if sid and sid not in seen:
                seen.add(sid)
                merged.append(s)

        return merged[:limit]

    def inject_context(self, max_sessions: int = 3) -> str:
        """Generate a context string for injection into context.md.

        Returns a markdown-formatted string with the last N sessions.
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
            errors = session.get("errors", [])
            pending = session.get("pending_tasks", [])

            lines.append(f"### Session {i} — {ts} (agent: @{agent})")
            lines.append("")
            if summary:
                lines.append(f"**Summary:** {summary}")
                lines.append("")
            if errors:
                lines.append(f"**Errors:** {len(errors)} issue(s)")
                for err in errors[:3]:
                    lines.append(f"- {truncate_text(err, 120)}")
                lines.append("")
            if pending:
                lines.append(f"**Pending tasks:**")
                for task in pending:
                    lines.append(f"- [ ] {truncate_text(task, 120)}")
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def update_context_md(self, max_sessions: int = 3):
        """Update .opencode/context.md with recent session history."""
        context_file = get_opencode_dir(self.project_root) / "context.md"
        if not context_file.exists():
            return

        try:
            with open(context_file, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            return

        session_context = self.inject_context(max_sessions)

        if not session_context:
            return

        marker = "## Recent Session History"
        if marker in content:
            content = re.sub(
                rf"{marker}.*?(?=---\n|$)",
                session_context.rstrip(),
                content,
                flags=re.DOTALL,
            )
        else:
            content = content.rstrip() + "\n\n" + session_context.rstrip()

        try:
            with open(context_file, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError:
            pass

    def close(self):
        """Close database connection if open."""
        if self._db is not None:
            self._db.close()
            self._db = None

    def delete_session(self, session_id: str) -> bool:
        """Delete a session file."""
        filepath = self.sessions_dir / f"{session_id}.json"
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def clear_old_sessions(self, keep: int = 10):
        """Delete all sessions except the most recent `keep`."""
        sessions = self.list_sessions()
        if len(sessions) <= keep:
            return
        for session in sessions[keep:]:
            self.delete_session(session["session_id"])
