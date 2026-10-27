"""Configure the five OpenCode roles from the shared catalog."""
from pathlib import Path

import questionary

from agent_catalog import ROLES, instructions_for
from cli.ui import console, print_step, print_success
from plan_manager import PlanManager


class SetupWizard:
    def __init__(self, project_root=None):
        self.project_root = Path(project_root).resolve() if project_root else Path(__file__).resolve().parent.parent
        self.agent_dir = self.project_root / ".opencode" / "agents"
        self.pm = PlanManager(project_root=self.project_root)
        self.agents = []

    def check_existing_config(self):
        return self.agent_dir.exists() and any(self.agent_dir.glob("*.md"))

    def run(self):
        print_step("Configure the five project agents")
        self.propose_defaults()
        choice = questionary.select("How would you like to proceed?", choices=[
            {"name": "Use the five recommended agents", "value": "default"},
            {"name": "Choose a model for each of the five roles", "value": "manual"},
        ]).ask()
        if choice is None:
            return
        self.setup_defaults()
        if choice == "manual":
            for agent in self.agents:
                model = questionary.select(f"Model for @{agent['name']}:",
                                           choices=self.pm.get_available_models(), default=agent["model"]).ask()
                if model is None:
                    return
                agent["model"] = model
        self.save_all()
        print_success("Five-agent configuration exported.")
        if questionary.confirm("Enable OpenCode wrapper session saving?", default=True).ask():
            from continuity import enable_auto_session
            if enable_auto_session(self.project_root):
                console.print("[dim]Session saving enabled for the OpenCode logger wrapper.[/dim]")

    def propose_defaults(self):
        from rich.table import Table
        table = Table(title=f"Five agents — {self.pm.get_plan_display_name()}", border_style="accent")
        table.add_column("Agent", style="cyan")
        table.add_column("Model")
        table.add_column("Responsibility")
        for role in ROLES:
            table.add_row(role, self.pm.get_model(role), self.pm.ROLE_DESCRIPTIONS[role])
        console.print(table)

    def setup_defaults(self):
        self.agents = [{"name": role, "description": self.pm.ROLE_DESCRIPTIONS[role],
                        "mode": "primary" if role == "orchestrator" else "subagent",
                        "model": self.pm.get_model(role), "permissions": dict(self.pm.ROLE_PERMISSIONS[role])}
                       for role in ROLES]

    def setup_agent(self, role="coder", is_primary=False):
        """Compatibility entry point restricted to an existing catalog role."""
        role = "orchestrator" if is_primary else role
        if role not in ROLES:
            raise ValueError(f"Choose a supported role: {', '.join(ROLES)}")
        model = questionary.select(f"Model for @{role}:", choices=self.pm.get_available_models(),
                                   default=self.pm.get_model(role)).ask()
        if model is None:
            return
        self.agents = [agent for agent in self.agents if agent["name"] != role]
        self.agents.append({"name": role, "description": self.pm.ROLE_DESCRIPTIONS[role],
                            "mode": "primary" if role == "orchestrator" else "subagent",
                            "model": model, "permissions": dict(self.pm.ROLE_PERMISSIONS[role])})

    def save_all(self):
        if {agent["name"] for agent in self.agents} != set(ROLES) or len(self.agents) != len(ROLES):
            raise ValueError("The setup must contain exactly the five supported roles")
        self.pm.write_agent_files(self.project_root, {a["name"]: a["model"] for a in self.agents})

    def _format_md(self, agent):
        from adapters.opencode import format_agent
        body = instructions_for(agent["name"]) if agent["name"] in ROLES else agent["description"] + ". Your goal is to fulfill user requests efficiently.\n"
        return format_agent(agent["name"], agent["model"], agent["description"], agent["permissions"], body=body)
