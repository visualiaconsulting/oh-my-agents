"""
plan_fallback.py - Automatic fallback system for oh-my-agents

Detects credit/balance errors from OpenCode and automatically switches
to the Zen free plan to maintain project continuity.

Fallback chain: Go -> Zen Free -> OpenRouter -> Free
"""
import os, json, re
from pathlib import Path
from datetime import datetime
from typing import Optional

CREDIT_ERROR_PATTERNS = [
    r"insufficient\s+credits?",
    r"credit\s+limit\s+exceeded",
    r"payment\s+required",
    r"quota\s+exceeded",
]
CREDIT_ERROR_REGEX = re.compile("|".join(CREDIT_ERROR_PATTERNS), re.IGNORECASE)

FALLBACK_CHAIN = {
    "go": "zen",
    "openrouter": "zen",
    "zen": "free",
    "ollama": None,
    "free": None,
}

ZEN_FREE_MODELS = {
    "orchestrator": "opencode/hy3-preview-free",
    "code-analyst": "opencode/ling-2.6-flash-free",
    "validator": "opencode/ling-2.6-flash-free",
    "bulk-processor": "opencode/nemotron-3-super-free",
    "subagent": "opencode/nemotron-3-super-free",
    "summarizer": "opencode/minimax-m2.5-free",
    "frontend": "opencode/minimax-m2.5-free",
    "ml-specialist": "opencode/minimax-m2.5",
    "fallback": "opencode/nemotron-3-super-free",
}

class FallbackManager:
    def __init__(self, project_root=None):
        self.project_root = project_root or Path.cwd().resolve()
        self.fallback_dir = self.project_root / ".opencode" / "fallback"
        self.fallback_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.fallback_dir / "state.json"
        self.log_file = self.fallback_dir / "fallback.log"

    def detect_credit_error(self, text):
        if not text: return False
        return bool(CREDIT_ERROR_REGEX.search(text))

    def get_next_fallback_plan(self, current_plan):
        return FALLBACK_CHAIN.get(current_plan)

    def trigger_fallback(self, from_plan, reason=""):
        next_plan = self.get_next_fallback_plan(from_plan)
        if not next_plan: return None
        state = self._load_state()
        event = {"timestamp": datetime.now().isoformat(),
                 "from_plan": from_plan, "to_plan": next_plan,
                 "reason": reason[:500] if reason else "credit exhausted",
                 "active": True}
        state["history"].append(event)
        state["current_fallback"] = next_plan
        state["original_plan"] = state.get("original_plan", from_plan)
        state["last_fallback_at"] = event["timestamp"]
        state["fallback_count"] = state.get("fallback_count", 0) + 1
        state["active"] = True
        self._save_state(state)
        self._log_event(event)
        return event

    def is_fallback_active(self):
        return self._load_state().get("active", False)

    def get_active_plan(self):
        state = self._load_state()
        if state.get("active") and state.get("current_fallback"):
            return state["current_fallback"]
        return os.getenv("OPENCODE_PLAN", "go")

    def reset_fallback(self):
        state = self._load_state()
        original = state.get("original_plan", "go")
        event = {"timestamp": datetime.now().isoformat(),
                 "action": "reset",
                 "from_fallback": state.get("current_fallback", "unknown"),
                 "to_plan": original}
        state["active"] = False
        state["current_fallback"] = None
        state["history"].append(event)
        self._save_state(state)
        self._log_event(event)
        return event

    def force_fallback(self, target_plan="zen"):
        state = self._load_state()
        current = self.get_active_plan()
        event = {"timestamp": datetime.now().isoformat(),
                 "from_plan": current, "to_plan": target_plan,
                 "reason": "manual force", "active": True}
        state["history"].append(event)
        state["current_fallback"] = target_plan
        state["original_plan"] = state.get("original_plan", current)
        state["last_fallback_at"] = event["timestamp"]
        state["fallback_count"] = state.get("fallback_count", 0) + 1
        state["active"] = True
        self._save_state(state)
        self._log_event(event)
        return event

    def get_status(self):
        state = self._load_state()
        return {"active": state.get("active", False),
                "current_plan": state.get("current_fallback") or os.getenv("OPENCODE_PLAN", "go"),
                "original_plan": state.get("original_plan", "go"),
                "fallback_count": state.get("fallback_count", 0),
                "last_fallback_at": state.get("last_fallback_at")}

    def get_env_overrides(self):
        state = self._load_state()
        active_plan = state.get("current_fallback") if state.get("active") else None
        if not active_plan: return {}
        return {"OPENCODE_PLAN": active_plan}

    def _load_state(self):
        if self.state_file.exists():
            try: return json.loads(open(self.state_file, encoding="utf-8").read())
            except: pass
        return {"active": False, "current_fallback": None,
                "original_plan": None, "history": [], "fallback_count": 0}

    def _save_state(self, state):
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def _log_event(self, event):
        ts = event.get("timestamp", datetime.now().isoformat())
        action = event.get("action", "fallback")
        fp = event.get("from_plan", event.get("from_fallback", "?"))
        tp = event.get("to_plan", "?")
        reason = event.get("reason", "")
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write("[%s] %s: %s -> %s | %s\n" % (ts, action, fp, tp, reason))
        except: pass


def check_credit_error(text):
    return FallbackManager().detect_credit_error(text)

def trigger_fallback(from_plan, project_root=None):
    fm = FallbackManager(project_root)
    return fm.trigger_fallback(from_plan)

def get_fallback_status(project_root=None):
    return FallbackManager(project_root).get_status()

# Write it
