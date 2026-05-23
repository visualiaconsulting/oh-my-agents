"""
continuity.py — Project continuity manager for oh-my-agents

Provides the re-entry experience: when returning to a project,
loads the last session state and generates context for the AI
to understand what was happening and what needs to be done next.
"""
import sys
from pathlib import Path
from typing import Optional

from utils import (
    generate_project_hash,
    get_project_db_path,
    get_current_git_branch,
    is_auto_session_enabled,
    truncate_text,
    format_timestamp,
)
from project_db import ProjectDB


class ContinuityManager:
    """Manages project continuity across sessions.
    
    Usage:
        cm = ContinuityManager(project_root)
        
        # Get a re-entry prompt for the AI
        prompt = cm.get_reentry_prompt()
        
        # Check if this is a known project with history
        if cm.has_history():
            print(cm.get_status_banner())
        
        # Enable auto-session saving
        cm.enable_auto_session()
        
        # Get project health status
        health = cm.get_project_health()
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd().resolve()
        self.db_path = get_project_db_path(self.project_root)
        self._db: Optional[ProjectDB] = None

    @property
    def db(self) -> ProjectDB:
        """Lazy-load the project database."""
        if self._db is None:
            self._db = ProjectDB(self.project_root)
        return self._db

    def has_history(self) -> bool:
        """Check if the project has any recorded session history."""
        if not self.db_path.exists():
            return False
        try:
            sessions = self.db.list_sessions(limit=1)
            return len(sessions) > 0
        except Exception:
            return False

    def is_new_project(self) -> bool:
        """Check if this project has no recorded sessions."""
        return not self.has_history()

    def get_last_session(self) -> Optional[dict]:
        """Get the most recent session."""
        if not self.has_history():
            return None
        return self.db.get_last_session()

    def get_reentry_prompt(self) -> str:
        """Generate a re-entry prompt for the AI agent.
        
        This is the main function for project continuity. It returns
        a markdown-formatted summary of where the project was left off,
        including pending tasks, recent changes, and error state.
        
        Returns empty string if no history exists.
        """
        if not self.has_history():
            return ""

        try:
            return self.db.get_continuity_prompt()
        except Exception:
            return ""

    def get_status_banner(self) -> str:
        """Get a user-friendly project status banner for the terminal."""
        try:
            state = self.db.get_project_state()
            last = self.get_last_session()
        except Exception:
            return ""

        if not state:
            return ""

        lines = []
        lines.append("╔══════════════════════════════════════════╗")
        lines.append(f"║  Project: {state.get('project_name', 'unknown'):<30} ║")
        
        branch = state.get('current_branch', '')
        if branch:
            lines.append(f"║  Branch:  {branch:<30} ║")
        
        lines.append(f"║  Sessions: {state.get('total_sessions', 0):<3}  │  Errors: {state.get('total_errors', 0):<3}       ║")
        
        last_active = state.get('last_active_at', 'never')
        lines.append(f"║  Last active: {last_active:<25} ║")
        
        if last:
            pending = last.get('pending_tasks', [])
            if pending:
                lines.append(f"║  Pending tasks: {len(pending):<2}                      ║")
                for task in pending[:2]:
                    lines.append(f"║    • {truncate_text(str(task), 32):<32} ║")
            
            files = last.get('files_changed', [])
            if files:
                lines.append(f"║  Recent files ({len(files)}):               ║")
                for f in files[:3]:
                    fname = f.get('filepath', str(f)) if isinstance(f, dict) else str(f)
                    lines.append(f"║    • {truncate_text(fname, 32):<32} ║")
        
        lines.append("╚══════════════════════════════════════════╝")
        return "\n".join(lines)

    def get_project_health(self) -> dict:
        """Get a project health report.
        
        Returns:
            dict with keys:
            - total_sessions: int
            - total_errors: int  
            - total_files_changed: int
            - last_active: str (ISO timestamp or "never")
            - pending_tasks: int
            - open_errors: int (errors from last session)
            - health_status: str ("healthy", "needs_attention", "new_project")
        """
        if self.is_new_project():
            return {
                "total_sessions": 0,
                "total_errors": 0,
                "total_files_changed": 0,
                "last_active": "never",
                "pending_tasks": 0,
                "open_errors": 0,
                "health_status": "new_project",
            }

        try:
            state = self.db.get_project_state()
            last = self.get_last_session()
        except Exception:
            return {"health_status": "error"}

        pending_count = len(last.get('pending_tasks', [])) if last else 0
        error_count = len(last.get('errors', [])) if last else 0
        
        # Determine health
        if error_count > 5 or pending_count > 5:
            health = "needs_attention"
        elif error_count > 0:
            health = "has_warnings"
        else:
            health = "healthy"

        return {
            "total_sessions": state.get('total_sessions', 0),
            "total_errors": state.get('total_errors', 0),
            "total_files_changed": state.get('total_files_changed', 0),
            "last_active": state.get('last_active_at', 'never'),
            "pending_tasks": pending_count,
            "open_errors": error_count,
            "health_status": health,
        }

    def enable_auto_session(self) -> bool:
        """Enable automatic session saving for this project.
        
        Creates the .opencode/.auto_session_enabled flag file.
        """
        try:
            flag_path = self.project_root / ".opencode" / ".auto_session_enabled"
            flag_path.parent.mkdir(parents=True, exist_ok=True)
            flag_path.write_text(
                f"# Auto-session saving enabled for {self.project_root.name}\n"
                f"# Created: {format_timestamp()}\n"
                f"# Project hash: {generate_project_hash(self.project_root)}\n"
            )
            return True
        except OSError:
            return False

    def disable_auto_session(self) -> bool:
        """Disable automatic session saving for this project."""
        try:
            flag_path = self.project_root / ".opencode" / ".auto_session_enabled"
            if flag_path.exists():
                flag_path.unlink()
            return True
        except OSError:
            return False

    def inject_context_to_file(self) -> bool:
        """Inject session continuity context into .opencode/context.md.
        
        Returns True if context.md was updated, False otherwise.
        """
        if not self.has_history():
            return False

        context_file = self.project_root / ".opencode" / "context.md"
        if not context_file.exists():
            return False

        try:
            content = context_file.read_text(encoding="utf-8")
        except OSError:
            return False

        try:
            session_context = self.db.inject_context(max_sessions=3)
        except Exception:
            return False

        if not session_context:
            return False

        from utils import inject_markdown_section
        updated = inject_markdown_section(content, "## Recent Session History", session_context)

        if updated != content:
            try:
                context_file.write_text(updated, encoding="utf-8")
                return True
            except OSError:
                pass

        return False

    def close(self):
        """Close the database connection."""
        if self._db is not None:
            self._db.close()
            self._db = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# Module-level convenience functions

def get_reentry_prompt(project_root: Optional[Path] = None) -> str:
    """Quick one-liner to get the re-entry prompt for a project."""
    with ContinuityManager(project_root) as cm:
        return cm.get_reentry_prompt()


def enable_auto_session(project_root: Optional[Path] = None) -> bool:
    """Quick one-liner to enable auto-session for a project."""
    with ContinuityManager(project_root) as cm:
        return cm.enable_auto_session()


if __name__ == "__main__":
    # Quick test when run directly
    cm = ContinuityManager()
    if cm.has_history():
        print(cm.get_status_banner())
        print()
        print("--- Re-entry Prompt ---")
        print(cm.get_reentry_prompt()[:500])
    else:
        print("New project — no session history yet.")
        print("Enable auto-session from the dashboard: python main.py -> Sessions & continuity")
