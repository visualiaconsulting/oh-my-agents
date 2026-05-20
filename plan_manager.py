# plan_manager.py
"""
Plan Manager — Detects the active OpenCode plan and adapts agent configuration
"""
import os
import json
from pathlib import Path
from typing import Dict, Optional
from plan_fallback import FallbackManager, ZEN_FREE_MODELS


class PlanManager:
    # Plan-to-model mapping by role
    # Using registry IDs (provider/model-id) that OpenCode recognizes
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
        "zen": {
            "orchestrator": "opencode/claude-sonnet-4.5",
            "code-analyst": "opencode/gpt-5.1-codex",
            "validator": "opencode/claude-haiku-4.5",
            "bulk-processor": "opencode/gemini-3-flash",
            "subagent": "opencode/gpt-5.4-mini",
            "summarizer": "opencode/minimax-m2.5-free",
            "frontend": "opencode/minimax-m2.5-free",
            "ml-specialist": "opencode/minimax-m2.5",
            "fallback": "opencode/gpt-5.4-mini",
            "all_available": [
                "opencode/big-pickle",
                "opencode/minimax-m2.5-free", "opencode/minimax-m2.5",
                "opencode/claude-haiku-4.5", "opencode/claude-opus-4.5",
                "opencode/claude-sonnet-4.5",
                "opencode/gpt-5.1-codex", "opencode/gpt-5.4-mini",
                "opencode/gemini-3-flash",
                "opencode-go/glm-5", "opencode-go/glm-5.1",
                "opencode/hy3-preview-free",
                "opencode-go/kimi-k2.5", "opencode-go/kimi-k2.6",
                "opencode/ling-2.6-flash-free",
                "opencode/nemotron-3-super-free"
            ]
        },
        "api": {
            "orchestrator": os.getenv("ORCHESTRATOR_MODEL", "anthropic/claude-sonnet-4"),
            "code-analyst": os.getenv("CODE_ANALYST_MODEL", "deepseek/DeepSeek-V4-Pro"),
            "validator": os.getenv("VALIDATOR_MODEL", "anthropic/claude-haiku-3"),
            "bulk-processor": os.getenv("BULK_MODEL", "deepseek/DeepSeek-V4-Flash"),
            "subagent": os.getenv("SUBAGENT_MODEL", "openai/gpt-4o-mini"),
            "summarizer": os.getenv("SUMMARIZER_MODEL", "openai/gpt-4o-mini"),
            "frontend": os.getenv("FRONTEND_MODEL", "openai/gpt-4o-mini"),
            "ml-specialist": os.getenv("ML_MODEL", "openai/gpt-4o-mini"),
            "fallback": os.getenv("FALLBACK_MODEL", "openai/gpt-4o-mini")
        },
        "enterprise": {
            "orchestrator": os.getenv("ENT_ORCHESTRATOR", "opencode-go/deepseek-v4-pro"),
            "code-analyst": os.getenv("ENT_ANALYST", "opencode-go/deepseek-v4-flash"),
            "validator": os.getenv("ENT_VALIDATOR", "opencode-go/mimo-v2.5-pro"),
            "bulk-processor": os.getenv("ENT_BULK", "opencode-go/minimax-m2.7"),
            "subagent": os.getenv("ENT_SUBAGENT", "opencode-go/glm-5.1"),
            "summarizer": os.getenv("ENT_SUMMARIZER", "opencode-go/minimax-m2.5"),
            "frontend": os.getenv("ENT_FRONTEND", "opencode-go/qwen3.6-plus"),
            "ml-specialist": os.getenv("ENT_ML", "opencode-go/minimax-m2.7"),
            "fallback": os.getenv("ENT_FALLBACK", "opencode-go/minimax-m2.5")
        },
        "openrouter": {
            # Optimized for $2 USD budget - cheapest models with best performance/token ratio
            # DeepSeek V3 ($0.008 in / $0.032 out per 1M) - used by 5/8 agents
            # Mistral Small ($0.020 in / $0.030 out per 1M) - cheapest output for bulk
            # Qwen3.5-Flash ($0.065 in / $0.260 out per 1M) - 1M context for validation
            "orchestrator": os.getenv("OR_OPENROUTER", "openrouter/deepseek/deepseek-v3"),
            "code-analyst": os.getenv("OR_ANALYST", "openrouter/deepseek/deepseek-v3"),
            "validator": os.getenv("OR_VALIDATOR", "openrouter/qwen/qwen3.5-flash"),
            "bulk-processor": os.getenv("OR_BULK", "openrouter/mistralai/mistral-small"),
            "subagent": os.getenv("OR_SUBAGENT", "openrouter/meta-llama/llama-3.1-8b-instruct"),
            "summarizer": os.getenv("OR_SUMMARIZER", "openrouter/deepseek/deepseek-v3"),
            "frontend": os.getenv("OR_FRONTEND", "openrouter/deepseek/deepseek-v3"),
            "ml-specialist": os.getenv("OR_ML", "openrouter/deepseek/deepseek-v3"),
            "fallback": os.getenv("OR_FALLBACK", "openrouter/deepseek/deepseek-v3"),
            # Free model alternatives (no balance needed)
            "free_orchestrator": "openrouter/google/gemma-2-9b-it:free",
            "free_analyst": "openrouter/qwen/qwen2.5-7b-instruct:free",
            "free_validator": "openrouter/meta-llama/llama-3.1-8b-instruct:free",
            "free_bulk": "openrouter/mistralai/mistral-small-3.1-24b-instruct:free",
            "free_subagent": "openrouter/meta-llama/llama-3.1-8b-instruct:free",
            "free_summarizer": "openrouter/google/gemma-2-9b-it:free",
            "free_frontend": "openrouter/qwen/qwen2.5-7b-instruct:free",
            "free_ml": "openrouter/qwen/qwen2.5-7b-instruct:free",
            "free_fallback": "openrouter/google/gemma-2-9b-it:free",
            "all_available": [
                "openrouter/deepseek/deepseek-v3",
                "openrouter/qwen/qwen3.5-flash",
                "openrouter/mistralai/mistral-small",
                "openrouter/meta-llama/llama-3.1-8b-instruct",
                "openrouter/google/gemma-2-9b-it:free",
                "openrouter/qwen/qwen2.5-7b-instruct:free",
                "openrouter/meta-llama/llama-3.1-8b-instruct:free",
                "openrouter/mistralai/mistral-small-3.1-24b-instruct:free",
                "openrouter/google/gemma-3-12b-it:free",
                "openrouter/nvidia/llama-3.1-nemotron-ultra-253b-v1:free",
            ]
        },
        "copilot": {
            "orchestrator": "copilot/claude-sonnet-4",
            "code-analyst": "copilot/gpt-4.1",
            "validator": "copilot/claude-haiku-4",
            "bulk-processor": "copilot/gpt-4.1-mini",
            "subagent": "copilot/claude-haiku-4",
            "summarizer": "copilot/gpt-4.1-nano",
            "frontend": "copilot/gpt-4.1-nano",
            "ml-specialist": "copilot/gpt-4.1-nano",
            "fallback": "copilot/gpt-4.1-nano"
        },
        "ollama": {
            "orchestrator": os.getenv("OLLAMA_ORCH", "ollama/llama3.3:70b"),
            "code-analyst": os.getenv("OLLAMA_ANALYST", "ollama/qwen2.5-coder:32b"),
            "validator": os.getenv("OLLAMA_VALIDATOR", "ollama/llama3.2:3b"),
            "bulk-processor": os.getenv("OLLAMA_BULK", "ollama/qwen2.5-coder:7b"),
            "subagent": os.getenv("OLLAMA_SUB", "ollama/llama3.1:8b"),
            "summarizer": os.getenv("OLLAMA_SUMMARIZER", "ollama/phi3:3.8b"),
            "frontend": os.getenv("OLLAMA_FRONTEND", "ollama/qwen2.5-coder:7b"),
            "ml-specialist": os.getenv("OLLAMA_ML", "ollama/qwen2.5-coder:7b"),
            "fallback": os.getenv("OLLAMA_FALLBACK", "ollama/phi3:3.8b")
        },
        "lmstudio": {
            "orquestador": os.getenv("LMSTUDIO_ORCH", "lmstudio/qwen2.5-coder-3b-instruct"),
            "proptech_expert": os.getenv("LMSTUDIO_PROPTECH", "lmstudio/nemotron-3-nano-4b"),
            "prompt_crafter": os.getenv("LMSTUDIO_CRAFTER", "lmstudio/gemma-4-e4b"),
            "python_architect": os.getenv("LMSTUDIO_ARCHITECT", "lmstudio/deepseek-r1-0528"),
            "qa_reviewer": os.getenv("LMSTUDIO_QA", "lmstudio/deepseek-r1-0528"),
            "fallback": os.getenv("LMSTUDIO_FALLBACK", "lmstudio/qwen2.5-coder-3b-instruct")
        },
        "free": {
            # 100% free models - no API key or balance needed
            # Uses OpenRouter free tier (25+ models, rate-limited but functional)
            "orchestrator": os.getenv("FREE_ORCH", "openrouter/google/gemma-2-9b-it:free"),
            "code-analyst": os.getenv("FREE_ANALYST", "openrouter/qwen/qwen2.5-7b-instruct:free"),
            "validator": os.getenv("FREE_VALIDATOR", "openrouter/meta-llama/llama-3.1-8b-instruct:free"),
            "bulk-processor": os.getenv("FREE_BULK", "openrouter/mistralai/mistral-small-3.1-24b-instruct:free"),
            "subagent": os.getenv("FREE_SUB", "openrouter/meta-llama/llama-3.1-8b-instruct:free"),
            "summarizer": os.getenv("FREE_SUMMARIZER", "openrouter/google/gemma-2-9b-it:free"),
            "frontend": os.getenv("FREE_FRONTEND", "openrouter/qwen/qwen2.5-7b-instruct:free"),
            "ml-specialist": os.getenv("FREE_ML", "openrouter/qwen/qwen2.5-7b-instruct:free"),
            "fallback": os.getenv("FREE_FALLBACK", "openrouter/google/gemma-2-9b-it:free"),
            "all_available": [
                "openrouter/google/gemma-2-9b-it:free",
                "openrouter/qwen/qwen2.5-7b-instruct:free",
                "openrouter/meta-llama/llama-3.1-8b-instruct:free",
                "openrouter/mistralai/mistral-small-3.1-24b-instruct:free",
                "openrouter/google/gemma-3-12b-it:free",
                "openrouter/nvidia/llama-3.1-nemotron-ultra-253b-v1:free",
            ]
        }
    }
    
    # Approximate limits per plan (for monitoring)
    PLAN_LIMITS = {
        "go": {"daily": 5000, "weekly": 25000, "monthly": 100000},
        "zen": {"daily": 2000, "weekly": 10000, "monthly": 40000},
        "api": {"daily": "variable", "weekly": "variable", "monthly": "variable"},
        "enterprise": {"daily": "custom", "weekly": "custom", "monthly": "custom"},
        "openrouter": {"daily": "$2 budget ~50M tokens", "weekly": "$2 budget ~50M tokens", "monthly": "$2 budget ~50M tokens"},
        "copilot": {"daily": "included", "weekly": "included", "monthly": "included"},
        "ollama": {"daily": "unlimited", "weekly": "unlimited", "monthly": "unlimited"},
        "lmstudio": {"daily": "unlimited", "weekly": "unlimited", "monthly": "unlimited"},
        "free": {"daily": "100 req/60s limit", "weekly": "unlimited", "monthly": "unlimited"}
    }
    
    def __init__(self, plan: Optional[str] = None, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent
        self.plan = plan or self._detect_plan()
        self.models = self.PLAN_MODELS.get(self.plan, self.PLAN_MODELS["go"])
        self.limits = self.PLAN_LIMITS.get(self.plan, self.PLAN_LIMITS["go"])
    
    def _detect_plan(self) -> str:
        """Automatically detects the plan based on environment/config"""
        # 1. Explicit environment variable
        if env_plan := os.getenv("OPENCODE_PLAN"):
            return env_plan.lower()
        
        # 2. Local configuration file
        config_path = self.project_root / ".opencode" / "plan.json"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    return json.load(f).get("plan", "go")
            except (json.JSONDecodeError, OSError):
                pass
        
        # 3. Detect by API key variables (Go uses OPENCODE_API_KEY)
        if os.getenv("ANTHROPIC_API_KEY"):
            return "api"
        
        # 4. Detect GitHub Copilot (Zen)
        if os.getenv("GITHUB_TOKEN") or os.getenv("COPILOT_TOKEN"):
            return "zen"
        
        # 5. Detect OpenRouter
        if os.getenv("OPENROUTER_API_KEY"):
            return "openrouter"

        # 6. Detect Ollama (local)
        if os.getenv("OLLAMA_HOST"):
            return "ollama"
        
        # 7. Detect LM Studio (local) - check env var or API availability
        if os.getenv("LMSTUDIO_HOST"):
            return "lmstudio"
        if self._check_lmstudio_available():
            return "lmstudio"
        
        # 8. Detect free plan (no balance needed)
        if os.getenv("OPENCODE_PLAN", "").lower() == "free":
            return "free"
        if os.getenv("FREE_MODE"):
            return "free"
        
        return "go"

    def _check_lmstudio_available(self) -> bool:
        """Check if LM Studio is running with API server enabled"""
        import urllib.request
        try:
            req = urllib.request.Request(
                "http://localhost:1234/v1/models",
                method="GET"
            )
            urllib.request.urlopen(req, timeout=2)
            return True
        except Exception:
            return False

    def get_available_models(self) -> list:
        """Returns a list of available model names for the current plan"""
        if "all_available" in self.models:
            return self.models["all_available"]
        return list(set(self.models.values()))

    def get_model(self, role: str) -> str:
        """Gets the model for a role, with fallback if not available"""
        return self.models.get(role, self.models.get("fallback"))
    
    def get_free_model(self, role: str) -> str:
        """Get the free model for a role (no balance needed).
        
        Falls back to free_fallback if the role is not found.
        Works with any plan - always returns the free alternative.
        """
        role_map = {
            "code-analyst": "free_analyst",
            "bulk-processor": "free_bulk",
            "ml-specialist": "free_ml",
        }
        free_key = role_map.get(role, "free_" + role.replace("-", "_"))
        return (self.PLAN_MODELS.get("openrouter", {}).get(free_key) or
                self.PLAN_MODELS.get("free", {}).get(free_key) or
                self.get_model(role))
    
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


    def get_fallback_plan(self) -> Optional[str]:
        """Get the fallback plan if current plan runs out of credits."""
        from plan_fallback import FALLBACK_CHAIN
        return FALLBACK_CHAIN.get(self.plan)

    def switch_to_fallback(self, reason: str = "") -> Optional[dict]:
        """Switch to the fallback plan."""
        fm = FallbackManager(self.project_root)
        event = fm.trigger_fallback(self.plan, reason)
        if event:
            self.plan = event["to_plan"]
            self.models = self.PLAN_MODELS.get(self.plan, self.PLAN_MODELS["go"])
            self.limits = self.PLAN_LIMITS.get(self.plan, self.PLAN_LIMITS["go"])
        return event

    def get_active_plan_name(self) -> str:
        """Get the currently active plan name."""
        fm = FallbackManager(self.project_root)
        return fm.get_active_plan() or os.getenv("OPENCODE_PLAN") or self.plan

    def is_using_fallback(self) -> bool:
        """Check if the system is using a fallback plan."""
        fm = FallbackManager(self.project_root)
        return fm.is_fallback_active()