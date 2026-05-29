import sys
import argparse
import shutil
from pathlib import Path

from update_manager import check_for_updates, run_update

SYSTEM_ROOT = Path(__file__).parent.resolve()
from plan_fallback import FallbackManager
import json


def check_dependencies():
    """Check that dependencies are installed"""
    missing = []
    try:
        import yaml
    except ImportError:
        missing.append("PyYAML")
    try:
        import questionary
    except ImportError:
        missing.append("questionary")
    try:
        import rich
    except ImportError:
        missing.append("rich")
    try:
        import requests
    except ImportError:
        missing.append("requests")
    return missing


def check_opencode_cli():
    """Check that OpenCode CLI is available"""
    return shutil.which("opencode") is not None


def run_doctor(working_root=None):
    """Diagnose environment issues"""
    import platform
    from cli.ui import console
    from utils import resolve_working_root, find_agent_source

    if working_root is None:
        working_root = resolve_working_root()

    console.print("\n[bold cyan]=== System Diagnostics ===[/bold cyan]\n")

    py_ver = platform.python_version()
    major, minor = map(int, py_ver.split(".")[:2])
    if major >= 3 and minor >= 8:
        console.print(f"  [green]OK[/green] Python {py_ver}")
    else:
        console.print(f"  [red]X[/red] Python {py_ver} (requires 3.8+)")

    missing = check_dependencies()
    if missing:
        console.print(f"  [red]X[/red] Missing dependencies: {', '.join(missing)}")
        console.print(f"    Run: [bold]pip install -r requirements.txt[/bold]")
    else:
        console.print(f"  [green]OK[/green] Dependencies installed (PyYAML, questionary, rich)")

    if check_opencode_cli():
        console.print(f"  [green]OK[/green] OpenCode CLI available")
    else:
        console.print(f"  [yellow]![/yellow] OpenCode CLI not found")
        console.print(f"    Install from: [bold]https://opencode.ai[/bold]")

    from plan_manager import PlanManager
    from utils import validate_agent_directory
    agent_dir = find_agent_source(working_root)
    if agent_dir:
        agent_count = len(list(agent_dir.glob("*.md")))
        console.print(f"  [green]OK[/green] Agents configured: {agent_count}")

        pm = PlanManager(project_root=working_root)
        valid, invalid = pm.validate_models()
        if invalid:
            console.print(f"  [red]X[/red] Invalid model IDs detected:")
            for name, model in invalid:
                console.print(f"      @{name} -> [red]{model}[/red] (not in registry)")
            console.print(f"    [dim]Run 'python main.py --setup' to reconfigure.[/dim]")
        elif valid:
            console.print(f"  [green]OK[/green] All agent model IDs valid ({len(valid)} models)")

        issues = validate_agent_directory(agent_dir)
        if issues:
            console.print()
            for issue in issues:
                icon = "[red]X[/red]" if issue["severity"] == "error" else "[yellow]![/yellow]"
                console.print(f"  {icon} {issue['message']}")
            console.print()
    else:
        console.print(f"  [yellow]![/yellow] No agent configuration found")

    from session_manager import SessionManager
    sm = SessionManager(project_root=working_root)
    sessions = sm.list_sessions(limit=1)
    if sessions:
        console.print(f"  [green]OK[/green] Session history active ({len(sm.list_sessions())} sessions)")
    else:
        console.print(f"  [dim]i[/dim] No sessions recorded yet")

    from skill_registry import SkillRegistry
    sr = SkillRegistry(project_root=working_root)
    skills = sr.list_skills()
    if skills:
        console.print(f"  [green]OK[/green] Skills installed: {len(skills)}")
    else:
        console.print(f"  [dim]i[/dim] No skills installed")

    console.print("\n[bold cyan]==============================[/bold cyan]\n")


def load_agents(working_root=None):
    """Load agent definitions from the best available source."""
    import yaml
    from utils import find_agent_source, validate_agent_directory, resolve_working_root

    if working_root is None:
        working_root = resolve_working_root()

    agent_dir = find_agent_source(working_root)
    agents = []
    if not agent_dir:
        return agents

    issues = validate_agent_directory(agent_dir)
    errors = [i for i in issues if i["severity"] == "error"]
    if errors:
        print("[WARNING] Agent directory validation errors:", file=sys.stderr)
        for e in errors:
            print(f"  {e['message']}", file=sys.stderr)

    for md_file in agent_dir.glob("*.md"):
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.startswith('---'):
                    parts = content.split('---')
                    if len(parts) >= 3:
                        metadata = yaml.safe_load(parts[1])
                        name = metadata.get('name', md_file.stem)
                        agents.append({
                            'name': f"@{name}",
                            'role': metadata.get('mode', 'subagent').capitalize(),
                            'model': metadata.get('model', 'unknown'),
                        })
        except (yaml.YAMLError, OSError):
            continue
    return agents


def install_global():
    """Copy agent .md files from repo .opencode/agents/ to ~/.opencode/agents/"""
    from cli.ui import console, print_success, print_error

    source_dir = SYSTEM_ROOT / ".opencode" / "agents"
    target_dir = Path.home() / ".opencode" / "agents"

    if not source_dir.exists():
        print_error(f"Source agent directory not found: {source_dir}")
        console.print("[dim]Run the setup wizard first with: python main.py --setup[/dim]")
        return False

    md_files = list(source_dir.glob("*.md"))
    if not md_files:
        print_error("No agent .md files found in source directory.")
        return False

    target_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    for md_file in md_files:
        target_file = target_dir / md_file.name
        shutil.copy2(md_file, target_file)
        copied += 1
        console.print(f"  [green]OK[/green] {md_file.name}")

    print_success(f"Installed {copied} agent(s) globally to {target_dir}")
    console.print("[dim]Now opencode --agent orchestrator works from ANY folder on your system.[/dim]")
    return True


def run_sessions_list(working_root=None):
    """List all recorded sessions"""
    from cli.ui import console, print_session_list
    from session_manager import SessionManager
    from utils import resolve_working_root

    if working_root is None:
        working_root = resolve_working_root()

    sm = SessionManager(project_root=working_root)
    sessions = sm.list_sessions()

    if not sessions:
        console.print("[yellow]No sessions recorded yet.[/yellow]")
        return

    print_session_list(sessions)


def run_session_detail(session_id: str, working_root=None):
    """Show details of a specific session"""
    from cli.ui import console, print_session_detail
    from session_manager import SessionManager
    from utils import resolve_working_root

    if working_root is None:
        working_root = resolve_working_root()

    sm = SessionManager(project_root=working_root)
    session = sm.get_session(session_id)

    if not session:
        console.print(f"[red]Session '{session_id}' not found.[/red]")
        return

    print_session_detail(session)


def run_session_status(working_root=None):
    """Show summary of the last session"""
    from cli.ui import console, print_session_detail
    from session_manager import SessionManager
    from utils import resolve_working_root

    if working_root is None:
        working_root = resolve_working_root()

    sm = SessionManager(project_root=working_root)
    session = sm.get_last_session()

    if not session:
        console.print("[yellow]No sessions recorded yet.[/yellow]")
        return

    console.print("[bold cyan]=== Last Session ===[/bold cyan]\n")
    print_session_detail(session)


def run_summarize(working_root=None):
    """Run the summarizer: scan logs and save session record"""
    from cli.ui import console, print_success, print_error
    from session_manager import SessionManager
    from utils import resolve_working_root, get_logs_dir_candidates

    if working_root is None:
        working_root = resolve_working_root()

    sm = SessionManager(project_root=working_root)
    log_data = sm.scan_logs()

    if not log_data["raw_content"]:
        console.print("[yellow]No logs found.[/yellow]")
        console.print("[dim]Searched in:[/dim]")
        for p in get_logs_dir_candidates(working_root):
            console.print(f"  [dim]- {p}[/dim]")
        console.print("[dim]Make sure OpenCode has been run in this project first.[/dim]")
        return

    session_id = sm.save_session(
        agent="system",
        summary=f"Auto-summarized session. {len(log_data.get('files_changed', []))} files changed, {len(log_data.get('errors', []))} errors found.",
        errors=log_data.get("errors", []),
        files_changed=log_data.get("files_changed", []),
        log_data=log_data,
    )

    sm.update_context_md()

    print_success(f"Session saved: {session_id}")
    console.print(f"  [dim]Files changed: {len(log_data.get('files_changed', []))}[/dim]")
    console.print(f"  [dim]Errors found: {len(log_data.get('errors', []))}[/dim]")
    console.print(f"  [dim]Context updated in .opencode/context.md[/dim]")


def run_skills_list(working_root=None):
    """List installed skills"""
    from cli.ui import console, print_skills_list
    from skill_registry import SkillRegistry
    from utils import resolve_working_root

    if working_root is None:
        working_root = resolve_working_root()

    sr = SkillRegistry(project_root=working_root)
    skills = sr.list_skills()

    if not skills:
        console.print("[yellow]No skills installed.[/yellow]")
        return

    print_skills_list(skills)


def run_skills_search(query: str, working_root=None):
    """Search for skills on skills.sh"""
    from cli.ui import console, print_skills_search
    from skill_registry import SkillRegistry
    from utils import resolve_working_root

    if working_root is None:
        working_root = resolve_working_root()

    sr = SkillRegistry(project_root=working_root)
    results = sr.search_skills(query)

    if not results:
        console.print(f"[yellow]No skills found for '{query}'.[/yellow]")
        return

    print_skills_search(results, query)


def run_skills_install(identifier: str, working_root=None):
    """Install a skill from skills.sh or local file"""
    from cli.ui import console, print_success, print_error
    from skill_registry import SkillRegistry
    from utils import resolve_working_root

    if working_root is None:
        working_root = resolve_working_root()

    sr = SkillRegistry(project_root=working_root)
    success = sr.install_skill(identifier)

    if success:
        name = identifier.split("/")[-1]
        print_success(f"Skill '{name}' installed to .opencode/skills/")
    else:
        print_error(f"Failed to install skill '{identifier}'. Check the identifier format.")


def run_skills_remove(name: str, working_root=None):
    """Remove an installed skill"""
    from cli.ui import console, print_success, print_error
    from skill_registry import SkillRegistry
    from utils import resolve_working_root

    if working_root is None:
        working_root = resolve_working_root()

    sr = SkillRegistry(project_root=working_root)
    success = sr.remove_skill(name)

    if success:
        print_success(f"Skill '{name}' removed.")
    else:
        print_error(f"Skill '{name}' not found.")


def run_skills_recommend(working_root=None, auto_install=False):
    """Analyze project and recommend skills."""
    from cli.ui import console, print_success
    from utils import resolve_working_root
    import questionary

    if working_root is None:
        working_root = resolve_working_root()

    recommender = SkillRecommender(project_root=working_root)
    recommendations = recommender.get_installable_recommendations()

    if not recommendations:
        console.print("[yellow]No new skill recommendations for this project.[/yellow]")
        return

    console.print("\n[bold cyan]=== Recommended Skills ===[/bold cyan]\n")
    for i, skill in enumerate(recommendations, 1):
        console.print(f"  {i}. [bold]{skill['name']}[/bold] -- {skill['description']}")
        console.print(f"     Tags: {', '.join(skill.get('tags', []))}")

    if auto_install:
        results = recommender.install_recommendations(recommendations)
        for skill_id, success in results:
            if success:
                console.print(f"  [green]OK Installed {skill_id}[/green]")
            else:
                console.print(f"  [red]X Failed {skill_id}[/red]")
        return

    console.print("")
    install = questionary.confirm("Install recommended skills?", default=True).ask()
    if install:
        results = recommender.install_recommendations(recommendations)
        installed = sum(1 for _, s in results if s)
        print_success(f"Installed {installed}/{len(results)} skill(s).")


def run_mcp_status(working_root=None):
    """Show MCP server status and available tools."""
    from cli.ui import console
    from utils import resolve_working_root

    if working_root is None:
        working_root = resolve_working_root()

    from mcp_config import MCPConfig, MCP_SERVER_TEMPLATES
    config = MCPConfig(project_root=working_root)
    servers = config.get_servers()

    if not servers:
        console.print("[yellow]No MCP servers configured.[/yellow]")
        console.print(f"[dim]Available templates: {', '.join(MCP_SERVER_TEMPLATES.keys())}[/dim]")
        return

    from mcp_client import MCPClient
    console.print("\n[bold cyan]=== MCP Servers ===[/bold cyan]\n")
    client = MCPClient(project_root=working_root)
    for server_config in servers:
        name = server_config.get("name", "unknown")
        desc = server_config.get("description", "")
        console.print(f"  [bold]{name}[/bold] -- {desc}")
        ok, msg = client.connect_server(server_config)
        if ok:
            tools = client.connections[name].tools
            console.print(f"    [green]OK Connected[/green] ({len(tools)} tool(s))")
            for tool in tools:
                console.print(f"      . {tool.get('name', '?')}: {tool.get('description', '')[:60]}")
            client.disconnect_server(name)
        else:
            console.print(f"    [red]X {msg}[/red]")
    console.print("")


def run_uninstall():
    """Remove global installation and optionally clean up data."""
    from cli.ui import console, print_success, print_error
    import questionary

    global_dir = Path.home() / ".opencode"
    agents_dir = global_dir / "agents"
    sessions_dir = global_dir / "sessions"
    skills_dir = global_dir / "skills"
    config_file = global_dir / "config.json"

    console.print("\n[bold red]=== Uninstall oh-my-agents ===[/bold red]\n")

    items_to_remove = []

    if agents_dir.exists():
        items_to_remove.append(("Global agents", agents_dir))
    if sessions_dir.exists():
        items_to_remove.append(("Global sessions", sessions_dir))
    if skills_dir.exists():
        items_to_remove.append(("Global skills", skills_dir))
    if config_file.exists():
        items_to_remove.append(("Global config", config_file))

    if not items_to_remove:
        console.print("[yellow]No global installation found.[/yellow]")
        console.print("[dim]Nothing to uninstall.[/dim]")
        return

    console.print("The following will be removed:")
    for label, path in items_to_remove:
        console.print(f"  [red]X[/red] {label}: {path}")

    remove_all = questionary.confirm(
        "Remove ALL of the above (agents, sessions, skills, config)?",
        default=True
    ).ask()

    if not remove_all:
        for label, path in list(items_to_remove):
            if not questionary.confirm(f"Remove {label}?", default=True).ask():
                items_to_remove = [x for x in items_to_remove if x[1] != path]

    if not items_to_remove:
        console.print("[dim]Uninstall cancelled.[/dim]")
        return

    confirmed = questionary.confirm(
        "This action cannot be undone. Continue?",
        default=False
    ).ask()

    if not confirmed:
        console.print("[dim]Uninstall cancelled.[/dim]")
        return

    removed = 0
    for label, path in items_to_remove:
        try:
            if path.is_file():
                path.unlink()
            else:
                shutil.rmtree(path)
            console.print(f"  [green]OK[/green] Removed {label}")
            removed += 1
        except OSError as e:
            print_error(f"Failed to remove {label}: {e}")

    if sys.platform != "win32":
        for wrapper_path in [Path("/usr/local/bin/oh-my-agents"), Path.home() / ".local" / "bin" / "oh-my-agents"]:
            if wrapper_path.exists():
                try:
                    wrapper_path.unlink()
                    console.print(f"  [green]OK[/green] Removed wrapper: {wrapper_path}")
                except OSError:
                    pass

    print_success(f"Uninstall complete. {removed} item(s) removed.")
    console.print("[dim]To remove the oh-my-agents repository itself, delete its folder manually.[/dim]")


def run_check_updates():
    """Check if updates are available and print status."""
    from cli.ui import console, print_success
    has_update, current, latest = check_for_updates()
    if has_update:
        console.print(f"\n[bold cyan]=== Update Available ===[/bold cyan]\n")
        console.print(f"  Current:  [dim]v{current}[/dim]")
        console.print(f"  Latest:   [bold green]v{latest}[/bold green]")
        console.print("")
        console.print("  Run [bold]python main.py --update[/bold] to install.")
    else:
        print_success(f"oh-my-agents is up to date (v{current}).")


def run_update_command(target_version=None):
    """Run the interactive update workflow."""
    success, message = run_update(target_version=target_version)
    if not success:
        from cli.ui import console
        console.print(f"\n[red]Update result: {message}[/red]\n")
        sys.exit(1)
    from cli.ui import console
    console.print(f"\n[green]{message}[/green]\n")


# ---------------------------------------------------------------------------
# Plan activation handlers
# ---------------------------------------------------------------------------

def activate_go_plan(working_root, wizard):
    """Activate Go plan: write agent files with built-in defaults, save plan."""
    from cli.ui import console, print_success
    from plan_manager import PlanManager

    pm = PlanManager(project_root=working_root)
    count = pm.write_agent_files(working_root)
    pm.save_plan("go")

    agents = load_agents(working_root=working_root)
    if not agents:
        console.print("[yellow]No agents could be loaded.[/yellow]")
        return None

    install_global()
    print_success(f"Go plan active with {count} agent(s)")
    return agents


def activate_lmstudio_plan(working_root, manual=False):
    """Activate LM Studio plan: detect server, assign roles, install agents."""
    from cli.ui import console, print_success, print_error
    from plan_manager import PlanManager
    import lmstudio_manager as lm

    console.print("\n[bold cyan]=== LM Studio Setup ===[/bold cyan]\n")

    if not lm.check_lmstudio_running():
        print_error("LM Studio server is not running.")
        console.print("[dim]1. Open LM Studio[/dim]")
        console.print("[dim]2. Go to the Server tab[/dim]")
        console.print("[dim]3. Click 'Start Server'[/dim]")
        console.print("[dim]4. Run this command again[/dim]")
        return None

    status = lm.get_status()
    models = status["models"]

    if not models:
        print_error("No LLM models found in LM Studio.")
        console.print("[dim]Download models from the Discover tab in LM Studio.[/dim]")
        return None

    console.print(f"[green]LM Studio running[/green] -- {len(models)} LLM model(s) detected:\n")
    for i, m in enumerate(models, 1):
        loaded = " [green]loaded[/green]" if m["is_loaded"] else " [dim]not loaded[/dim]"
        code_tag = " [yellow]code[/yellow]" if m["is_code"] else ""
        console.print(f"  {i}. {m['display_name']} ({m['params_string']}, ctx={m['max_context_length']}){loaded}{code_tag}")

    console.print("")

    mode = "manual" if manual else "auto"
    result = lm.install_lmstudio_agents(working_root, models, manual=manual)

    print_success(f"Installed {result['count']} agent(s) for LM Studio plan")
    console.print("\n[bold]Role assignments:[/bold]")
    for a in result["installed"]:
        console.print(f"  @{a['role']:<18} -> {a['display']} ({a['params']})")

    pm = PlanManager(project_root=working_root)
    pm.save_plan("lmstudio")

    ctx = result.get("context", {})
    if ctx.get("changed"):
        console.print(f"\n[yellow]Context fix applied:[/yellow] {ctx['message']}")
        console.print("[yellow]Action required:[/yellow] Reload the model in LM Studio (select another model, then reselect it) or restart LM Studio.")
    elif ctx.get("message"):
        console.print(f"  [dim]Context: {ctx['message']}[/dim]")

    return load_agents(working_root=working_root)


def _pick_models_for_plan(plan: str, working_root):
    """Interactive model picker for copilot/openrouter plans."""
    import questionary
    from plan_manager import PlanManager
    from cli.wizard import SetupWizard
    from cli.ui import console

    pm = PlanManager(project_root=working_root)
    available_models = pm.PLAN_MODELS.get(plan, {}).get("all_available", [])

    if not available_models:
        console.print(f"[red]No known models for plan '{plan}'.[/red]")
        return None

    roles = ["orchestrator", "python-engineer", "db-architect", "structured-engineer",
             "docs-writer", "bulk-processor", "validator", "researcher",
             "frontend-engineer", "devops", "ml-specialist", "security-reviewer",
             "git-manager", "test-engineer", "prompt-engineer"]

    console.print(f"\n[bold cyan]Configure models for {pm.get_plan_display_name(plan)}[/bold cyan]")
    console.print("[dim]Choose a model for each role, or select 'Custom...' to type your own model ID.[/dim]\n")

    CUSTOM_LABEL = "✏️  Custom..."

    assignments = {}
    for role in roles:
        default_idx = min(roles.index(role), len(available_models) - 1)
        default_model = pm.PLAN_MODELS[plan].get(role) or available_models[default_idx]

        choices = available_models + [CUSTOM_LABEL]
        chosen = questionary.select(
            f"Model for @{role}:",
            choices=choices,
            default=default_model,
        ).ask()

        if chosen is None:
            return None
        if chosen == CUSTOM_LABEL:
            custom_id = questionary.text(
                f"Enter custom model ID for @{role}:",
                default=""
            ).ask()
            if not custom_id:
                console.print(f"  [yellow]Skipped @{role}, keeping default.[/yellow]")
                custom_id = default_model
            chosen = custom_id
        assignments[role] = chosen

    # Write agent files using PlanManager (avoids template duplication)
    pm.write_agent_files(working_root, assignments)
    for role, model in assignments.items():
        console.print(f"  [green]OK[/green] @{role:<18} -> {model}")

    pm.save_plan(plan)
    console.print(f"\n[bold green]{pm.get_plan_display_name(plan)} plan activated.[/bold green]")

    return load_agents(working_root=working_root)


def activate_copilot_plan(working_root):
    """Activate GitHub Copilot plan with model selection wizard."""
    from cli.ui import console
    console.print("[dim]GitHub Copilot plan: uses your existing Copilot subscription.[/dim]")
    console.print("[dim]Ensure you have an active GitHub Copilot subscription.[/dim]")
    return _pick_models_for_plan("copilot", working_root)


def activate_openrouter_plan(working_root):
    """Activate OpenRouter plan with model selection wizard."""
    import questionary
    from cli.ui import console

    console.print("[dim]OpenRouter plan: uses your own API key and credits.[/dim]\n")

    api_key = questionary.text(
        "OpenRouter API key (optional, or set OPENROUTER_API_KEY env var):",
        default=""
    ).ask()

    if api_key:
        import os
        os.environ["OPENROUTER_API_KEY"] = api_key
        console.print("  [green]OK[/green] API key set for this session.\n")

    return _pick_models_for_plan("openrouter", working_root)



# ---------------------------------------------------------------------------
# Main dashboard / plan selector
# ---------------------------------------------------------------------------

def show_dashboard(working_root):
    """Unified single-level dashboard. Replaces all submenus."""
    import questionary
    from cli.ui import console, print_header, print_plan_panel, print_action_menu, print_agent_status
    from plan_manager import PlanManager
    from continuity import ContinuityManager

    pm = PlanManager(project_root=working_root)

    # Auto-show continuity on dashboard start (once)
    cm = ContinuityManager(project_root=working_root)
    if cm.has_history():
        banner = cm.get_status_banner()
        if banner:
            console.print(banner)
        cm.inject_context_to_file()
    cm.close()

    while True:
        current_plan = pm.plan
        agents = load_agents(working_root=working_root)

        print_header()

        plans_info = {}
        for key in ["go", "lmstudio", "copilot", "openrouter"]:
            name = pm.get_plan_display_name(key)
            desc = pm.get_plan_description(key)
            if key == current_plan:
                status = "ACTIVE"
            elif key == "go":
                status = "ready"
            else:
                status = "set up"
            plans_info[key] = {"name": name, "description": desc, "status_label": status}

        print_plan_panel(current_plan, plans_info)

        if agents:
            print_agent_status(agents)

        actions = {
            "Provider": [
                ("1", "Switch provider"),
            ],
            "Agent Management": [
                ("2", "View agent status"),
                ("3", "Install globally"),
            ],
            "Sessions & Tools": [
                ("4", "Sessions & continuity"),
                ("5", "Skills & MCP tools"),
            ],
            "System": [
                ("6", "Diagnostics"),
                ("7", "Check for updates"),
            ],
        }
        print_action_menu(actions)

        choice = questionary.select(
            "Select an option:",
            choices=[
                {"name": "Switch provider", "value": "1"},
                {"name": "View agent status", "value": "2"},
                {"name": "Install globally", "value": "3"},
                {"name": "Sessions & continuity", "value": "4"},
                {"name": "Skills & MCP tools", "value": "5"},
                {"name": "Diagnostics", "value": "6"},
                {"name": "Check for updates", "value": "7"},
                {"name": "Exit", "value": "0"},
            ]
        ).ask()

        if choice is None or choice == "0":
            console.print("\n[dim]Goodbye![/dim]")
            break

        if choice == "1":
            _switch_provider(working_root, pm)
        elif choice == "2":
            if agents:
                print_agent_status(agents)
            else:
                console.print("[yellow]No agents configured. Select a plan first.[/yellow]")
        elif choice == "3":
            install_global()
        elif choice == "4":
            _sessions_menu(working_root)
        elif choice == "5":
            _tools_menu(working_root)
        elif choice == "6":
            run_doctor(working_root=working_root)
        elif choice == "7":
            _check_and_offer_update()

        console.print("\n[dim](Press Enter to continue...)[/dim]")
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            break


def _switch_provider(working_root, pm):
    """Switch to a different provider in one step."""
    import questionary
    from cli.ui import console

    plan = questionary.select(
        "Select a provider:",
        choices=[
            {"name": "OpenCode Go Plan (cloud)", "value": "go"},
            {"name": "LM Studio (local)", "value": "lmstudio"},
            {"name": "GitHub Copilot", "value": "copilot"},
            {"name": "OpenRouter", "value": "openrouter"},
        ]
    ).ask()

    if plan is None:
        return

    if plan == "go":
        from cli.wizard import SetupWizard
        wizard = SetupWizard(project_root=working_root)
        activate_go_plan(working_root, wizard)
    elif plan == "lmstudio":
        activate_lmstudio_plan(working_root)
    elif plan == "copilot":
        activate_copilot_plan(working_root)
    elif plan == "openrouter":
        activate_openrouter_plan(working_root)


def _sessions_menu(working_root):
    """Simplified sessions submenu."""
    import questionary
    from cli.ui import console

    choice = questionary.select(
        "Sessions & continuity:",
        choices=[
            {"name": "View session history", "value": "list"},
            {"name": "Continue last session", "value": "continue"},
            {"name": "Project health", "value": "health"},
            {"name": "Back", "value": "back"},
        ]
    ).ask()

    if choice is None or choice == "back":
        return

    if choice == "list":
        run_sessions_list(working_root=working_root)
    elif choice == "continue":
        from continuity import ContinuityManager
        cm = ContinuityManager(project_root=working_root)
        if cm.has_history():
            prompt = cm.get_reentry_prompt()
            if prompt:
                console.print(f"\n[bold cyan]=== Continuity Context ===[/bold cyan]\n")
                console.print(prompt)
        else:
            console.print("[yellow]No session history found.[/yellow]")
        cm.close()
    elif choice == "health":
        from continuity import ContinuityManager
        cm = ContinuityManager(project_root=working_root)
        health = cm.get_project_health()
        console.print(f"\n[bold cyan]=== Project Health ===[/bold cyan]\n")
        console.print(f"  Status:       {health.get('health_status', 'unknown')}")
        console.print(f"  Sessions:     {health.get('total_sessions', 0)}")
        console.print(f"  Total errors: {health.get('total_errors', 0)}")
        console.print(f"  Last active:  {health.get('last_active', 'never')}")
        cm.close()


def _tools_menu(working_root):
    """Simplified tools submenu."""
    import questionary
    from cli.ui import console

    choice = questionary.select(
        "Skills & MCP tools:",
        choices=[
            {"name": "View installed skills", "value": "list"},
            {"name": "Search & install skills", "value": "search"},
            {"name": "View MCP servers", "value": "mcp"},
            {"name": "Back", "value": "back"},
        ]
    ).ask()

    if choice is None or choice == "back":
        return

    if choice == "list":
        run_skills_list(working_root=working_root)
    elif choice == "search":
        query = questionary.text("Search skills:").ask()
        if query:
            run_skills_search(query, working_root=working_root)
    elif choice == "mcp":
        run_mcp_status(working_root=working_root)


def _check_and_offer_update():
    """Check for updates and offer to install."""
    import questionary
    from cli.ui import console
    run_check_updates()
    has_update, _, latest = check_for_updates()
    if has_update:
        do_update = questionary.confirm(f"Install v{latest} now?", default=True).ask()
        if do_update:
            run_update_command()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="oh-my-agents -- Multi-Agent Orchestration for OpenCode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    Interactive dashboard
  python main.py --plan go          Switch to Go plan (default)
  python main.py --plan lmstudio    Detect LM Studio and install agents
  python main.py --doctor           Run system diagnostics
        """
    )

    # Core flags
    parser.add_argument("--plan", type=str, default=None,
                        choices=["go", "lmstudio", "copilot", "openrouter"],
                        help="Switch to a provider plan (go, lmstudio, copilot, openrouter)")
    parser.add_argument("--setup", action="store_true",
                        help="Run the Go plan setup wizard")
    parser.add_argument("--doctor", action="store_true",
                        help="Run system diagnostics")
    parser.add_argument("--dir", type=str, default=None,
                        help="Set the project root directory (overrides auto-detection)")
    parser.add_argument("--version", action="store_true",
                        help="Show version information")

    # Update flags
    parser.add_argument("--update", action="store_true",
                        help="Update oh-my-agents to the latest version")
    parser.add_argument("--check-updates", action="store_true",
                        help="Check if a newer version is available")

    # Install/uninstall
    parser.add_argument("--install-global", action="store_true",
                        help="Install agent files globally to ~/.opencode/agents/")
    parser.add_argument("--uninstall", action="store_true",
                        help="Remove global installation and optional data")

    args = parser.parse_args()

    from utils import resolve_working_root
    from cli.ui import console

    working_root = resolve_working_root(args.dir)

    # Handle version
    if args.version:
        from update_manager import get_current_version
        current = get_current_version()
        console.print(f"[bold cyan]oh-my-agents[/bold cyan] v{current}")
        return

    # Handle update flags
    if args.check_updates:
        run_check_updates()
        return

    if args.update:
        run_update_command()
        return

    # Check dependencies for all other flows
    missing = check_dependencies()
    if missing:
        print(f"\n  ERROR: Missing dependencies: {', '.join(missing)}")
        print(f"  Run: pip install -r requirements.txt\n")
        sys.exit(1)

    # Uninstall
    if args.uninstall:
        run_uninstall()
        return

    # Install global
    if args.install_global:
        install_global()
        return

    # Doctor
    if args.doctor:
        run_doctor(working_root=working_root)
        return

    # Setup wizard (Go plan)
    if args.setup:
        from cli.wizard import SetupWizard
        wizard = SetupWizard(project_root=working_root)
        wizard.run()
        agents = load_agents(working_root=working_root)
        if agents:
            from cli.ui import print_agent_status
            print_agent_status(agents)
            console.print("\n[bold green]Setup complete.[/bold green] Use `opencode --agent orchestrator` to get started.")
        return

    # --plan flag: non-interactive plan switching
    if args.plan:
        plan = args.plan
        if plan == "go":
            from cli.wizard import SetupWizard
            activate_go_plan(working_root, SetupWizard(project_root=working_root))
        elif plan == "lmstudio":
            activate_lmstudio_plan(working_root)
        elif plan == "copilot":
            from cli.ui import print_success
            agents = activate_copilot_plan(working_root)
            if agents:
                print_success(f"Copilot plan active with {len(agents)} agent(s)")
        elif plan == "openrouter":
            from cli.ui import print_success
            agents = activate_openrouter_plan(working_root)
            if agents:
                print_success(f"OpenRouter plan active with {len(agents)} agent(s)")
        return

    # No flags: show interactive dashboard
    show_dashboard(working_root)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        from cli.ui import console
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(0)
