"""
plan_fallback.py - Simplified fallback system for oh-my-agents

Go plan is the only standard. No automatic fallback.
To switch plans, reinstall oh-my-agents globally or per-project.
"""
import os, json
from pathlib import Path
from datetime import datetime
from typing import Optional

class FallbackManager:
    """Minimal fallback manager — only supports manual reset to Go."""
    def __init__(self, project_root=None):
        self.project_root = project_root or Path.cwd().resolve()
        self.fallback_dir = self.project_root / ".opencode" / "fallback"
        self.fallback_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.fallback_dir / "state.json"
        self.log_file = self.fallback_dir / "fallback.log"

    def is_fallback_active(self):
        return self._load_state().get("active", False)

    def get_active_plan(self):
        return "go"

    def reset_fallback(self):
        state = self._load_state()
        event = {"timestamp": datetime.now().isoformat(),
                 "action": "reset", "to_plan": "go"}
        state["active"] = False
        state["current_fallback"] = None
        state["original_plan"] = "go"
        state["history"].append(event)
        self._save_state(state)
        self._log_event(event)
        return event

    def get_status(self):
        state = self._load_state()
        return {"active": state.get("active", False),
                "current_plan": "go",
                "original_plan": "go",
                "fallback_count": state.get("fallback_count", 0),
                "last_fallback_at": state.get("last_fallback_at")}

    def _load_state(self):
        if self.state_file.exists():
            try:
                return json.loads(open(self.state_file, encoding="utf-8").read())
            except Exception:
                pass
        return {"active": False, "current_fallback": None,
                "original_plan": "go", "history": [], "fallback_count": 0}

    def _save_state(self, state):
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def _log_event(self, event):
        ts = event.get("timestamp", datetime.now().isoformat())
        action = event.get("action", "reset")
        tp = event.get("to_plan", "go")
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write("[%s] %s -> %s\n" % (ts, action, tp))
        except Exception:
            pass


def get_fallback_status(project_root=None):
    return FallbackManager(project_root).get_status()
