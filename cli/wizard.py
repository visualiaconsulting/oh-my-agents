import os
import questionary
from pathlib import Path
from cli.ui import console, print_step, print_success, print_error
from plan_manager import PlanManager


class SetupWizard:
    def __init__(self, project_root=None):
        self.agents = []
        # Use project_root if provided, otherwise derive from this file's location (cli/wizard.py -> project root)
        self.project_root = Path(project_root).resolve() if project_root else Path(__file__).resolve().parent.parent
        self.agent_dir = self.project_root / ".opencode" / "agents"
        self.pm = PlanManager(project_root=self.project_root)

    def check_existing_config(self):
        if not self.agent_dir.exists():
            return False
        return len(list(self.agent_dir.glob("*.md"))) > 0

    def run(self):
        print_step("Welcome to the Agent Setup Wizard")
        
        # Propose default configuration
        self.propose_defaults()
        
        accept = questionary.select(
            "How would you like to proceed?",
            choices=[
                {"name": "Accept default configuration", "value": "default"},
                {"name": "Configure each agent manually", "value": "manual"}
            ]
        ).ask()

        if accept == "default":
            self.setup_defaults()
        else:
            # Reset just in case
            self.agents = []
            # 1. Define Orchestrator
            self.setup_agent(role="orchestrator", is_primary=True)
            
            # 2. Define Subagents
            add_more = True
            while add_more:
                self.setup_agent(role="subagent")
                add_more = questionary.confirm("Do you want to add another subagent?", default=True).ask()
        
        self.save_all()
        print_success("Configuration completed successfully.")

    def propose_defaults(self):
        """Show the table of what will be configured by default"""
        from rich.table import Table
        table = Table(title="Suggested Configuration (Go Plan)", border_style="accent")
        table.add_column("Agent", style="cyan")
        table.add_column("Model", style="white")
        table.add_column("Role", style="dim")

        table.add_row("orchestrator", "opencode-go/deepseek-v4-pro", "Primary")
        table.add_row("code-analyst", "opencode-go/deepseek-v4-flash", "Subagent")
        table.add_row("validator", "opencode-go/mimo-v2.5-pro", "Subagent")
        table.add_row("bulk-processor", "opencode-go/minimax-m2.7", "Subagent")
        table.add_row("subagent", "opencode-go/glm-5.1", "Fallback")
        table.add_row("summarizer", "opencode-go/minimax-m2.5", "Session Summary")
        table.add_row("frontend", "opencode-go/qwen3.6-plus", "UI Specialist")
        table.add_row("ml-specialist", "opencode-go/minimax-m2.7", "ML Specialist")
        table.add_row("fallback", "opencode-go/minimax-m2.5", "Speed/Recovery")

        console.print(table)

    def setup_defaults(self):
        """Automatically configure the recommended agents"""
        self.agents = [] # Reset
        defaults = [
            {"name": "orchestrator", "role": "primary", "model": "opencode-go/deepseek-v4-pro", "desc": "Central system orchestrator"},
            {"name": "code-analyst", "role": "subagent", "model": "opencode-go/deepseek-v4-flash", "desc": "Senior software engineer"},
            {"name": "validator", "role": "subagent", "model": "opencode-go/qwen3.6-plus", "desc": "QA and code validator"},
            {"name": "bulk-processor", "role": "subagent", "model": "opencode-go/qwen3.5-plus", "desc": "Bulk data processing"},
            {"name": "subagent", "role": "subagent", "model": "opencode-go/glm-5.1", "desc": "Fallback agent and generic tasks"},
            {"name": "summarizer", "role": "subagent", "model": "opencode-go/minimax-m2.5", "desc": "Session summarizer and project analyst"},
            {"name": "frontend", "role": "subagent", "model": "opencode-go/qwen3.6-plus", "desc": "Frontend specialist — React, TypeScript, UI"},
            {"name": "ml-specialist", "role": "subagent", "model": "opencode-go/minimax-m2.7", "desc": "ML and data pipeline specialist"}
        ]

        permissions_map = {
            "orchestrator":     {"edit": "deny",  "bash": "deny",  "read": "allow", "task": "allow"},
            "code-analyst":     {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
            "validator":        {"edit": "deny",  "bash": "deny",  "read": "allow", "task": "deny"},
            "bulk-processor":   {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
            "subagent":         {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
            "summarizer":       {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
            "frontend":         {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
            "ml-specialist":    {"edit": "allow", "bash": "allow", "read": "allow", "task": "deny"},
        }

        for d in defaults:
            agent_config = {
                "name": d["name"],
                "description": d["desc"],
                "mode": d["role"],
                "model": d["model"],
                "permissions": permissions_map.get(d["name"], {
                    "edit": "allow", "bash": "allow", "read": "allow", "task": "deny"
                })
            }
            self.agents.append(agent_config)

    def setup_agent(self, role="subagent", is_primary=False):
        console.print(f"\n[bold accent]Configuring {'Orchestrator' if is_primary else 'Subagent'}[/bold accent]")
        
        default_name = "@orchestrator" if is_primary else "@subagent"
        name = questionary.text("Agent name:", default=default_name).ask()
        
        description = questionary.text("Short role description:").ask()
        
        # Model selection with arrows
        available_models = self.pm.get_available_models()
        default_model = self.pm.get_model("orchestrator" if is_primary else "code-analyst")
        
        model = questionary.select(
            f"Select a model for plan '{self.pm.plan}':",
            choices=available_models,
            default=default_model
        ).ask()
        
        # Permissions with elegant confirmation
        allow_edit = questionary.confirm("Allow file editing?", default=True).ask()
        allow_bash = questionary.confirm("Allow bash command execution?", default=True).ask()
        
        agent_config = {
            "name": name.replace("@", ""),
            "description": description,
            "mode": "primary" if is_primary else "subagent",
            "model": model,
            "permissions": {
                "edit": "allow" if allow_edit else "deny",
                "bash": "allow" if allow_bash else "deny",
                "read": "allow",
                "task": "allow" if is_primary else "deny"
            }
        }
        self.agents.append(agent_config)

    def save_all(self):
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        from utils import validate_agent_directory

        # Check for existing conflicts before writing
        existing_issues = validate_agent_directory(self.agent_dir)
        existing_names = set()
        for f in self.agent_dir.glob("*.md"):
            if f.stem not in [a["name"] for a in self.agents]:
                c = f.read_text(encoding="utf-8").strip()
                if c.startswith("---"):
                    parts = c.split("---")
                    if len(parts) >= 3:
                        import yaml
                        try:
                            meta = yaml.safe_load(parts[1])
                            if isinstance(meta, dict) and meta.get("name"):
                                existing_names.add(meta["name"])
                        except yaml.YAMLError:
                            pass

        for agent in self.agents:
            agent_name = agent["name"]
            if agent_name in existing_names:
                console.print(f"  [yellow]⚠[/yellow] Agent \"{agent_name}\" already exists — overwriting")

            file_path = self.agent_dir / f"{agent_name}.md"
            content = self._format_md(agent)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

    def _format_md(self, agent):
        return f"""---
name: {agent['name']}
description: {agent['description']}
mode: {agent['mode']}
model: {agent['model']}
temperature: 0.2
permission:
  edit: {agent['permissions']['edit']}
  bash: {agent['permissions']['bash']}
  read: {agent['permissions']['read']}
  task: {agent['permissions']['task']}
---

{agent['description']}. Your goal is to fulfill user requests efficiently.
"""
