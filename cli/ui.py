import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme
from rich.align import Align
from rich.columns import Columns
from rich.layout import Layout
from rich.box import ROUNDED, MINIMAL, HEAVY_HEAD

custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "header": "bold magenta",
    "accent": "bold cyan",
    "plan_active": "bold green",
    "plan_inactive": "dim white",
    "label": "cyan",
})

console = Console(theme=custom_theme, force_terminal=True, legacy_windows=False)


def print_header():
    ascii_art = """
    ██████╗ ██████╗ ███████╗███╗   ██╗ ██████╗  ██████╗ ██████╗ ███████╗
    ██╔══██╗██╔══██╗██╔════╝████╗  ██║██╔════╝ ██╔═══██╗██╔══██╗██╔════╝
    ██║  ██║██████╔╝█████╗  ██╔██╗ ██║██║      ██║   ██║██║  ██║█████╗
    ██║  ██║██╔═══╝ ██╔══╝  ██║╚██╗██║██║      ██║   ██║██║  ██║██╔══╝
    ██████╔╝██║     ███████╗██║ ╚████║╚██████╗ ╚██████╔╝██████╔╝███████╗
    ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝ ╚═════╝ ╚═════╝
    """
    console.print(Align.center(f"[accent]{ascii_art}[/accent]"))

    title = Text("oh-my-agents", style="bold cyan")
    subtitle = Text("Multi-Agent Orchestration Framework", style="dim")
    credit = Text("A product of VisualIA Consulting - Licensed under MIT", style="dim italic")

    panel_content = Align.center(
        Text.assemble(title, "\n", subtitle, "\n\n", credit)
    )

    panel = Panel(
        panel_content,
        border_style="dim",
        padding=(1, 2),
    )
    console.print(panel)


def print_dashboard_header(current_plan: str, agent_count: int, plan_display: str):
    """Compact status bar showing current plan and agent count."""
    console.print()
    status = f"[bold cyan]Current:[/bold cyan] {plan_display}   [bold cyan]Agents:[/bold cyan] {agent_count}   [bold cyan]Plan:[/bold cyan] {current_plan}"
    console.print(Panel(status, border_style="accent", padding=(1, 2), box=HEAVY_HEAD))
    console.print()


def print_plan_selector(current_plan: str, plans: dict):
    """Display an interactive-style plan selector panel.

    plans: dict of {plan_key: {name, description, status_label}}
    """
    rows = []
    for key, info in plans.items():
        name = info["name"]
        desc = info["description"]
        status = info["status_label"]
        if key == current_plan:
            line = f"  [plan_active]{'■'} {name:<30} ACTIVE[/plan_active]"
        else:
            line = f"  [plan_inactive]{'□'} {name:<30}[/plan_inactive] [yellow]{status}[/yellow]"
        rows.append(line)
        rows.append(f"     [dim]{desc}[/dim]")
        rows.append("")

    text = Text.from_markup("\n".join(rows))
    panel = Panel(text, title="[bold]Select your AI Provider[/bold]", border_style="accent", box=ROUNDED, padding=(1, 2))
    console.print(panel)
    console.print()


def print_simple_menu(title: str, items: list):
    """Print a compact menu panel.

    items: list of (key, label) tuples. key is the number/letter, label is the text.
    """
    lines = []
    for key, label in items:
        lines.append(f"  [accent][{key}][/accent] {label}")
    text = Text.from_markup("\n".join(lines))
    panel = Panel(text, title=f"[bold]{title}[/bold]", border_style="dim", box=MINIMAL, padding=(1, 2))
    console.print(panel)
    console.print()


def print_agent_status(agents_data):
    table = Table(title="Active Agents", border_style="dim")
    table.add_column("Agent", style="accent")
    table.add_column("Role", style="info")
    table.add_column("Model", style="white")
    table.add_column("Status", justify="center")

    for agent in agents_data:
        table.add_row(
            agent['name'],
            agent['role'],
            agent['model'],
            "[bold green]Active[/bold green]"
        )

    console.print(table)


def print_session_list(sessions):
    table = Table(title="Session History", border_style="dim")
    table.add_column("ID", style="accent")
    table.add_column("Timestamp", style="info")
    table.add_column("Agent", style="white")
    table.add_column("Summary", style="dim")
    table.add_column("Errors", justify="center")
    table.add_column("Files", justify="center")

    for session in sessions:
        sid = session.get("session_id", "?")
        ts = session.get("timestamp", "?")
        agent = session.get("agent", "?")
        summary = session.get("summary", "")
        if len(summary) > 60:
            summary = summary[:57] + "..."
        errors = len(session.get("errors", []))
        files = len(session.get("files_changed", []))

        error_style = "red" if errors > 0 else "green"

        table.add_row(
            sid,
            ts,
            f"@{agent}",
            summary or "[dim]No summary[/dim]",
            f"[{error_style}]{errors}[/{error_style}]",
            str(files),
        )

    console.print(table)


def print_session_detail(session):
    from utils import truncate_text

    sid = session.get("session_id", "?")
    ts = session.get("timestamp", "?")
    agent = session.get("agent", "?")
    summary = session.get("summary", "")

    console.print(f"  [bold]Session:[/bold] {sid}")
    console.print(f"  [bold]Time:[/bold]    {ts}")
    console.print(f"  [bold]Agent:[/bold]   @{agent}")
    console.print("")

    if summary:
        console.print(f"  [bold]Summary:[/bold]")
        console.print(f"  {summary}")
        console.print("")

    errors = session.get("errors", [])
    if errors:
        console.print(f"  [bold red]Errors ({len(errors)}):[/bold red]")
        for err in errors[:5]:
            console.print(f"    [red]·[/red] {truncate_text(err, 100)}")
        if len(errors) > 5:
            console.print(f"    [dim]... and {len(errors) - 5} more[/dim]")
        console.print("")

    pending = session.get("pending_tasks", [])
    if pending:
        console.print(f"  [bold yellow]Pending Tasks:[/bold yellow]")
        for task in pending:
            console.print(f"    [yellow]·[/yellow] {truncate_text(task, 100)}")
        console.print("")

    files = session.get("files_changed", [])
    if files:
        console.print(f"  [bold]Files Changed ({len(files)}):[/bold]")
        for f in files[:10]:
            console.print(f"    [dim]·[/dim] {f}")
        if len(files) > 10:
            console.print(f"    [dim]... and {len(files) - 10} more[/dim]")
        console.print("")


def print_skills_list(skills):
    table = Table(title="Installed Skills", border_style="dim")
    table.add_column("Name", style="accent")
    table.add_column("Description", style="dim")
    table.add_column("Source", style="info")

    for skill in skills:
        desc = skill.get("description", "")
        if len(desc) > 60:
            desc = desc[:57] + "..."
        table.add_row(
            skill["name"],
            desc or "[dim]No description[/dim]",
            skill.get("source", "local"),
        )

    console.print(table)


def print_skills_search(results, query):
    table = Table(title=f"Skills Search: '{query}'", border_style="dim")
    table.add_column("#", style="accent")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="dim")
    table.add_column("Repo", style="info")

    for i, skill in enumerate(results[:15], 1):
        if "error" in skill:
            console.print(f"[yellow]{skill['error']}[/yellow]")
            return

        name = skill.get("name", "?")
        desc = skill.get("description", "")
        repo = skill.get("repo", skill.get("source", "?"))
        if len(desc) > 50:
            desc = desc[:47] + "..."

        table.add_row(str(i), name, desc or "[dim]--[/dim]", repo)

    console.print(table)
    console.print("\n[dim]Install with: python main.py --skills-install owner/repo/name[/dim]")


def print_step(message):
    console.print(Panel(message, border_style="info", expand=False))


def print_success(message):
    console.print(f"[success]OK[/success] {message}")


def print_error(message):
    console.print(f"[error]X[/error] {message}")
