# plan_manager.py
"""
Plan Manager — Go plan as the only standard. Other plans require explicit installation.
"""
import os
import json
from pathlib import Path
from typing import Dict, Optional


class PlanManager:
    # Plan-to-model mapping by role
    # Using registry IDs (provider/model-id) that OpenCode recognizes
    # Human-readable plan names for the dashboard
    PLAN_DISPLAY_NAMES = {
        "go": "OpenCode Go Plan",
        "lmstudio": "LM Studio",
        "copilot": "GitHub Copilot",
        "openrouter": "OpenRouter",
    }

    PLAN_DESCRIPTIONS = {
        "go": "Cloud hosted models — 5000 credits/day, no setup required",
        "lmstudio": "Run agents locally on your machine with local LLMs",
        "copilot": "Use your GitHub Copilot subscription models",
        "openrouter": "Bring your own API credits from multiple providers",
    }

    PLAN_MODELS = {
        "go": {
            "orchestrator": "opencode-go/deepseek-v4-pro",
            "code-analyst": "opencode-go/deepseek-v4-flash",
            "validator": "opencode-go/mimo-v2.5-pro",
            "bulk-processor": "opencode-go/minimax-m2.7",
            "subagent": "opencode-go/glm-5.1",
            "summarizer": "opencode-go/minimax-m2.5",
            "frontend": "opencode-go/qwen3.6-plus",
            "ml-specialist": "opencode-go/minimax-m2.7",
            "fallback": "opencode-go/minimax-m2.5",
            "all_available": [
                "opencode-go/glm-5", "opencode-go/glm-5.1",
                "opencode-go/kimi-k2.5", "opencode-go/kimi-k2.6",
                "opencode-go/mimo-v2-pro", "opencode-go/mimo-v2-omni",
                "opencode-go/mimo-v2.5-pro", "opencode-go/mimo-v2.5",
                "opencode-go/minimax-m2.5", "opencode-go/minimax-m2.7",
                "opencode-go/deepseek-v4-pro", "opencode-go/deepseek-v4-flash",
                "opencode-go/qwen3.5-plus", "opencode-go/qwen3.6-plus"
            ]
        },
        "lmstudio": {
            "orchestrator": "lmstudio/default-orchestrator",
            "code-analyst": "lmstudio/default-code-analyst",
            "validator": "lmstudio/default-validator",
            "bulk-processor": "lmstudio/default-bulk",
            "subagent": "lmstudio/default-subagent",
            "summarizer": "lmstudio/default-summarizer",
            "frontend": "lmstudio/default-frontend",
            "ml-specialist": "lmstudio/default-ml",
            "fallback": "lmstudio/default-fallback"
        },
        "copilot": {
            "orchestrator": "copilot/claude-sonnet-4",
            "code-analyst": "copilot/gpt-4o",
            "validator": "copilot/claude-3.5-haiku",
            "bulk-processor": "copilot/gemini-2.5-flash",
            "subagent": "copilot/claude-3.5-haiku",
            "summarizer": "copilot/claude-3.5-haiku",
            "frontend": "copilot/gpt-4o",
            "ml-specialist": "copilot/gemini-2.5-flash",
            "fallback": "copilot/claude-3.5-haiku",
            "all_available": [
                "copilot/claude-sonnet-4",
                "copilot/gpt-4o",
                "copilot/claude-3.5-haiku",
                "copilot/gemini-2.5-flash"
            ]
        },
        "openrouter": {
            "orchestrator": "openrouter/google/gemini-2.5-flash",
            "code-analyst": "openrouter/deepseek/deepseek-v3",
            "validator": "openrouter/google/gemini-2.5-flash",
            "bulk-processor": "openrouter/meta-llama/llama-3.3-70b",
            "subagent": "openrouter/google/gemini-2.5-flash",
            "summarizer": "openrouter/google/gemini-2.5-flash",
            "frontend": "openrouter/deepseek/deepseek-v3",
            "ml-specialist": "openrouter/google/gemini-2.5-flash",
            "fallback": "openrouter/google/gemini-2.5-flash",
            "all_available": [
                "openrouter/google/gemini-2.5-flash",
                "openrouter/deepseek/deepseek-v3",
                "openrouter/meta-llama/llama-3.3-70b",
                "openrouter/openai/gpt-4o",
                "openrouter/anthropic/claude-3.5-haiku",
                "openrouter/anthropic/claude-sonnet-4",
                "openrouter/deepseek/deepseek-v4-pro",
                "openrouter/deepseek/deepseek-v4-flash",
                "openrouter/qwen/qwen3.6-plus",
                "openrouter/qwen/qwen3.5-plus",
                "openrouter/glm/glm-5.1",
                "openrouter/minimax/m2.7",
                "openrouter/minimax/m2.5",
                "openrouter/kimi/kimi-k2.6"
            ]
        }
    }
    
    # Approximate limits per plan (for monitoring)
    PLAN_LIMITS = {
        "go": {"daily": 5000, "weekly": 25000, "monthly": 100000},
        "lmstudio": {"daily": "unlimited", "weekly": "unlimited", "monthly": "unlimited"},
        "copilot": {"daily": "copilot_limits", "weekly": "copilot_limits", "monthly": "copilot_limits"},
        "openrouter": {"daily": "pay_as_you_go", "weekly": "pay_as_you_go", "monthly": "pay_as_you_go"}
    }
    
    # Agent metadata for generating .md files
    ROLE_PERMISSIONS = {
        "orchestrator":   {"edit": "deny",  "bash": "deny",  "read": "allow", "task": "allow"},
        "code-analyst":   {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
        "validator":      {"edit": "deny",  "bash": "deny",  "read": "allow", "task": "deny"},
        "bulk-processor": {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
        "subagent":       {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
        "summarizer":     {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
        "frontend":       {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
        "ml-specialist":  {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
    }

    ROLE_DESCRIPTIONS = {
        "orchestrator": "Main coordinator that delegates tasks to specialized agents",
        "code-analyst": "Senior software engineer for clean code and architecture",
        "validator": "QA specialist for validation, linting, and quality review",
        "bulk-processor": "Bulk data processing agent for high-volume tasks",
        "subagent": "Debugger and fallback agent for auxiliary tasks",
        "summarizer": "Session analyst for log analysis and project continuity",
        "frontend": "UI specialist for React, TypeScript, and frontend development",
        "ml-specialist": "ML engineer for training, inference, and data pipelines",
    }

    ALL_ROLES = [
        "orchestrator", "code-analyst", "validator", "bulk-processor",
        "subagent", "summarizer", "frontend", "ml-specialist"
    ]

    def __init__(self, plan: Optional[str] = None, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent
        self.plan = plan or self._detect_plan()
        self.models = self.PLAN_MODELS.get(self.plan, self.PLAN_MODELS["go"])
        self.limits = self.PLAN_LIMITS.get(self.plan, self.PLAN_LIMITS["go"])
    
    def _detect_plan(self) -> str:
        """Returns 'go' as default, or 'lmstudio' if explicitly set in plan.json.
        Other plans require explicit installation via main.py or wizard.
        """
        config_path = self.project_root / ".opencode" / "plan.json"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    plan = json.load(f).get("plan", "go")
                    if plan in self.PLAN_MODELS:
                        return plan
            except (json.JSONDecodeError, OSError):
                pass
        return "go"

    def write_agent_files(self, working_root, plan_models=None):
        """Write or overwrite all 8 agent .md files with the plan's models.
        
        Args:
            working_root: Project root directory
            plan_models: Dict of {role: model_id}. If None, uses self.models.
        
        Returns:
            int: Number of agent files written
        """
        agent_dir = working_root / ".opencode" / "agents"
        agent_dir.mkdir(parents=True, exist_ok=True)

        models = plan_models or self.models
        plan_display = self.get_plan_display_name()

        for role in self.ALL_ROLES:
            model = models.get(role, models.get("fallback", ""))
            perms = self.ROLE_PERMISSIONS[role]
            desc = self.ROLE_DESCRIPTIONS[role]
            mode = "primary" if role == "orchestrator" else "subagent"

            content = (
                "---\n"
                f"name: {role}\n"
                f"description: {desc}\n"
                f"mode: {mode}\n"
                f"model: {model}\n"
                "temperature: 0.2\n"
                "permission:\n"
                f"  edit: {perms['edit']}\n"
                f"  bash: {perms['bash']}\n"
                f"  read: {perms['read']}\n"
                f"  task: {perms['task']}\n"
                "---\n"
                "\n"
                f"{desc}. Running on {plan_display} ({model}).\n"
            )
            file_path = agent_dir / f"{role}.md"
            file_path.write_text(content, encoding="utf-8")

        return len(self.ALL_ROLES)

    def get_available_models(self) -> list:
        """Returns a list of available model names for the current plan"""
        if "all_available" in self.models:
            return self.models["all_available"]
        return list(set(self.models.values()))

    def get_model(self, role: str) -> str:
        """Gets the model for a role, with fallback if not available"""
        return self.models.get(role, self.models.get("fallback"))
    
    def validate_models(self):
        """Validate that agent models in .opencode/agents/*.md exist in the registry.

        Returns:
            (valid, invalid): tuple of (list of valid agent names,
                              list of (name, model) tuples for invalid agents)
        """
        import yaml

        agent_dir = self.project_root / ".opencode" / "agents"
        if not agent_dir.exists():
            return [], []

        known_models = set()
        for plan_data in self.PLAN_MODELS.values():
            if "all_available" in plan_data:
                known_models.update(plan_data["all_available"])
            for key, val in plan_data.items():
                if key != "all_available" and isinstance(val, str):
                    known_models.add(val)

        valid = []
        invalid = []

        for md_file in agent_dir.glob("*.md"):
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()
                if content.startswith("---"):
                    parts = content.split("---")
                    if len(parts) >= 3:
                        metadata = yaml.safe_load(parts[1])
                        name = metadata.get("name", md_file.stem)
                        model = metadata.get("model", "")
                        if model and model in known_models:
                            valid.append(name)
                        else:
                            invalid.append((name, model))
            except (yaml.YAMLError, OSError):
                invalid.append((md_file.stem, "parse error"))

        return valid, invalid

    def generate_config_snippet(self) -> Dict:
        """Generates a configuration snippet for opencode.json"""
        return {
            "plan": self.plan,
            "models": {role: self.get_model(role) for role in 
             ["orchestrator", "code-analyst", "validator", "bulk-processor",
              "subagent", "summarizer", "frontend", "ml-specialist"]},
            "limits": self.limits,
            "requires_api_keys": self.plan == "api",
            "auto_fallback": True
        }

    def get_plan_display_name(self, plan: Optional[str] = None) -> str:
        """Get human-readable name for a plan key."""
        p = plan or self.plan
        return self.PLAN_DISPLAY_NAMES.get(p, p.capitalize())

    def get_plan_description(self, plan: Optional[str] = None) -> str:
        """Get human-readable description for a plan key."""
        p = plan or self.plan
        return self.PLAN_DESCRIPTIONS.get(p, "")

    def save_plan(self, plan: str):
        """Save current plan to .opencode/plan.json."""
        plan_path = self.project_root / ".opencode" / "plan.json"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump({"plan": plan}, f)
        self.plan = plan
        self.models = self.PLAN_MODELS.get(plan, self.PLAN_MODELS["go"])
        self.limits = self.PLAN_LIMITS.get(plan, self.PLAN_LIMITS["go"])


