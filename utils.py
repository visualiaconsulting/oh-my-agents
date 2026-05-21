"""
utils.py — Cross-platform helpers for oh-my-agents

Windows-first, Linux-ready. All path operations use pathlib for portability.
"""
import os
import sys
import json
import re
import uuid
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

SYSTEM_ROOT = Path(__file__).parent.resolve()


def get_system_root() -> Path:
    """Return the directory where oh-my-agents is installed (system root)."""
    return SYSTEM_ROOT


def resolve_working_root(explicit_dir: Optional[str] = None) -> Path:
    """Return the active project directory.

    Priority:
    1. explicit_dir if provided
    2. Path.cwd() (current working directory)
    """
    if explicit_dir:
        return Path(explicit_dir).resolve()
    return Path.cwd().resolve()


def find_agent_source(working_root: Optional[Path] = None) -> Optional[Path]:
    """Find the directory containing agent .md files.

    Search order:
    1. working_root/.opencode/agents/ (local project override)
    2. ~/.opencode/agents/ (global install)
    3. system_root/.opencode/agents/ (repo bundled agents)

    Returns the first directory that exists and contains at least one .md file,
    or None if nothing found.
    """
    candidates = []
    if working_root:
        candidates.append(working_root / ".opencode" / "agents")
    candidates.append(Path.home() / ".opencode" / "agents")
    candidates.append(get_system_root() / ".opencode" / "agents")

    for candidate in candidates:
        if candidate.exists() and any(candidate.glob("*.md")):
            return candidate
    return None


def get_opencode_dir(project_root: Optional[Path] = None) -> Path:
    """Return the .opencode directory path."""
    root = project_root or Path(__file__).parent
    return root / ".opencode"


def get_sessions_dir(project_root: Optional[Path] = None) -> Path:
    """Return the .opencode/sessions directory path."""
    d = get_opencode_dir(project_root) / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_skills_dir(project_root: Optional[Path] = None) -> Path:
    """Return the .opencode/skills directory path."""
    d = get_opencode_dir(project_root) / "skills"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_logs_dir(project_root: Optional[Path] = None) -> Path:
    """Return the .opencode/logs directory path."""
    return get_opencode_dir(project_root) / "logs"


def get_logs_dir_candidates(project_root: Optional[Path] = None) -> list[Path]:
    """Return candidate log directories in priority order.

    Searches these locations (first existing wins):
    a. project_root/.opencode/logs (if project_root provided)
    b. Path.home() / ".opencode" / "logs"
    c. On Windows: %APPDATA%/opencode/logs
    d. On Windows: %LOCALAPPDATA%/opencode/logs
    e. Path.home() / ".config" / "opencode" / "logs" (XDG fallback)

    Returns only paths that exist and are valid.
    """
    candidates = []
    if project_root:
        candidates.append(project_root / ".opencode" / "logs")
    candidates.append(Path.home() / ".opencode" / "logs")
    if is_windows():
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            candidates.append(Path(appdata) / "opencode" / "logs")
        localappdata = os.environ.get("LOCALAPPDATA", "")
        if localappdata:
            candidates.append(Path(localappdata) / "opencode" / "logs")
    candidates.append(Path.home() / ".config" / "opencode" / "logs")

    # Filter to only existing directories, preserving order
    return [p for p in candidates if p.exists() and p.is_dir()]


def get_global_agents_dir() -> Path:
    """Return the global agents directory (~/.opencode/agents/)."""
    return Path.home() / ".opencode" / "agents"


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return str(uuid.uuid4())[:8]


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """Format a datetime for display."""
    dt = dt or datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_timestamp(ts_str: str) -> datetime:
    """Parse a timestamp string back to datetime."""
    try:
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return datetime.min


def is_windows() -> bool:
    """Check if running on Windows."""
    return sys.platform == "win32"


def get_shell_config_file() -> Path:
    """Return the path to the shell config file for the current platform."""
    if is_windows():
        return Path.home() / ".opencode" / "config.json"
    return Path.home() / ".config" / "opencode" / "config.json"


def safe_json_load(filepath: Path, default=None):
    """Safely load a JSON file, returning default on error."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def safe_json_save(filepath: Path, data: dict):
    """Safely save data as JSON."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def truncate_text(text: str, max_length: int = 200) -> str:
    """Truncate text to max_length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def inject_markdown_section(content: str, marker: str, new_content: str) -> str:
    """Inject or replace a marked section in markdown content.

    If `marker` exists, replaces everything from the marker to the
    next `---` separator or end-of-file. If not, appends new_content
    at the end.

    Returns the updated content.
    """
    import re
    if marker in content:
        content = re.sub(
            rf"{re.escape(marker)}.*?(?=---\n|$)",
            new_content.rstrip(),
            content,
            flags=re.DOTALL,
        )
    else:
        content = content.rstrip() + "\n\n" + new_content.rstrip()
    return content


def update_context_md_file(project_root: Path, section_marker: str, section_content: str) -> bool:
    """Update .opencode/context.md with a new section.

    Reads the file, injects/replaces the section identified by section_marker
    with section_content, and writes it back.

    Returns True if the file was updated, False if context.md doesn't exist.
    """
    context_file = get_opencode_dir(project_root) / "context.md"
    if not context_file.exists():
        return False

    try:
        content = context_file.read_text(encoding="utf-8")
    except OSError:
        return False

    if not section_content:
        return False

    content = inject_markdown_section(content, section_marker, section_content)

    try:
        context_file.write_text(content, encoding="utf-8")
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Project database and auto-session helpers
# ---------------------------------------------------------------------------


def get_project_db_path(project_root: Optional[Path] = None) -> Path:
    """Return the path to .opencode/project.db within the project.

    Creates the parent .opencode directory if it doesn't exist.
    """
    opencode_dir = get_opencode_dir(project_root)
    opencode_dir.mkdir(parents=True, exist_ok=True)
    return opencode_dir / "project.db"


def generate_project_hash(project_root: Optional[Path] = None) -> str:
    """Generate a deterministic hash for the project based on its absolute path.

    Uses SHA-256 truncated to 12 characters for a short, stable identifier.
    """
    root = (project_root or Path.cwd()).resolve()
    return hashlib.sha256(str(root).encode()).hexdigest()[:12]


def get_current_git_branch(project_root: Optional[Path] = None) -> str:
    """Detect the current git branch name.

    Returns the branch name, or empty string if not a git repo or on error.
    """
    try:
        root = (project_root or Path.cwd()).resolve()
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(root),
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        pass
    return ""


def get_current_git_diff_summary(project_root: Optional[Path] = None) -> str:
    """Get a brief git diff summary using ``git diff --stat HEAD``.

    Returns the first 500 characters of the diff stat, or empty string
    if not a git repo or on error. Useful for capturing session changes.
    """
    try:
        root = (project_root or Path.cwd()).resolve()
        result = subprocess.run(
            ["git", "diff", "--stat", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(root),
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()[:500]
    except (subprocess.SubprocessError, OSError):
        pass
    return ""


def parse_openCode_log_content(raw_content: str) -> dict:
    """Analyze raw OpenCode log content and extract structured information.

    Uses the same regex patterns as :class:`session_manager.SessionManager`
    for consistency.

    Returns a dict with keys:
        - errors: list of error line matches
        - warnings: list of warning line matches
        - files_changed: list of unique file paths found
        - commands_run: list of command lines found
        - summary_hint: last 20 lines (where conclusions usually appear)
    """
    result = {
        "errors": [],
        "warnings": [],
        "files_changed": [],
        "commands_run": [],
        "summary_hint": "",
    }

    for line in raw_content.splitlines():
        if re.search(r"(error|exception|failed|failure)", line, re.IGNORECASE):
            result["errors"].append(line.strip())
        elif re.search(r"(warning|warn)", line, re.IGNORECASE):
            result["warnings"].append(line.strip())
        elif re.search(
            r"(modified|created|deleted|wrote|edited)", line, re.IGNORECASE
        ):
            match = re.search(r"[\w./\\-]+\.\w+", line)
            if match:
                result["files_changed"].append(match.group(0))
        elif re.match(r"\$\s+", line) or re.search(
            r"Running:\s+", line, re.IGNORECASE
        ):
            result["commands_run"].append(line.strip())

    # Deduplicate and trim
    result["files_changed"] = list(set(result["files_changed"]))
    result["errors"] = result["errors"][:50]
    result["warnings"] = result["warnings"][:50]
    result["commands_run"] = result["commands_run"][:50]

    # Extract summary hint from the last 20 lines
    lines = raw_content.splitlines()
    result["summary_hint"] = "\n".join(lines[-20:])

    return result


def get_auto_session_flag_path(project_root: Optional[Path] = None) -> Path:
    """Return the path to the ``.opencode/.auto_session_enabled`` flag file."""
    return get_opencode_dir(project_root) / ".auto_session_enabled"


def is_auto_session_enabled(project_root: Optional[Path] = None) -> bool:
    """Check if the auto-session flag file exists for this project."""
    return get_auto_session_flag_path(project_root).exists()


# ---------------------------------------------------------------------------
# Agent directory validation (prevents duplicate/shadow agent files)
# ---------------------------------------------------------------------------


def _levenshtein(a: str, b: str) -> int:
    """Compute Levenshtein distance between two strings (case-insensitive)."""
    a, b = a.lower(), b.lower()
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = range(len(b) + 1)
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[-1]


def validate_agent_directory(agent_dir: Path) -> list[dict]:
    """Validate an agent .md directory for integrity issues.

    Checks:
      1. Multiple files with ``mode: primary``
      2. Files without valid YAML front matter
      3. Duplicate ``name:`` values across files
      4. Files with suspiciously similar names (Levenshtein distance < 3)

    Returns a list of dicts with keys:
      - ``severity``: ``"error"`` or ``"warning"``
      - ``message``: human-readable description
      - ``files``: list of filenames involved (optional)
    """
    issues: list[dict] = []

    if not agent_dir.exists():
        return issues

    md_files = sorted(agent_dir.glob("*.md"))
    if not md_files:
        return issues

    parsed = []

    for f in md_files:
        try:
            content = f.read_text(encoding="utf-8").strip()
        except OSError:
            continue

        if not content.startswith("---"):
            parsed.append({"stem": f.stem, "file": f.name, "no_frontmatter": True})
            continue

        parts = content.split("---")
        if len(parts) < 3:
            parsed.append({"stem": f.stem, "file": f.name, "no_frontmatter": True})
            continue

        import yaml

        try:
            meta = yaml.safe_load(parts[1])
        except yaml.YAMLError:
            parsed.append({"stem": f.stem, "file": f.name, "no_frontmatter": True})
            continue

        if not isinstance(meta, dict):
            parsed.append({"stem": f.stem, "file": f.name, "no_frontmatter": True})
            continue

        parsed.append(
            {
                "stem": f.stem,
                "file": f.name,
                "name": meta.get("name"),
                "mode": meta.get("mode"),
                "no_frontmatter": False,
            }
        )

    # Check 1: duplicate name values
    names_seen = {}
    for p in parsed:
        if p["no_frontmatter"]:
            continue
        n = p["name"]
        if n is None:
            continue
        if n in names_seen:
            issues.append(
                {
                    "severity": "error",
                    "message": f"Duplicate agent name \"{n}\" in files: {names_seen[n]}, {p['file']}",
                    "files": [names_seen[n], p["file"]],
                }
            )
        else:
            names_seen[n] = p["file"]

    # Check 2: multiple primary agents
    primaries = [p for p in parsed if not p["no_frontmatter"] and p["mode"] == "primary"]
    if len(primaries) > 1:
        primary_files = [p["file"] for p in primaries]
        issues.append(
            {
                "severity": "error",
                "message": f"Multiple agents with mode: primary — {', '.join(primary_files)}. Only one coordinator is allowed.",
                "files": primary_files,
            }
        )

    # Check 3: files without valid front matter
    no_fm = [p for p in parsed if p["no_frontmatter"]]
    if no_fm:
        no_fm_files = [p["file"] for p in no_fm]
        issues.append(
            {
                "severity": "warning",
                "message": f"Files without valid YAML front matter: {', '.join(no_fm_files)}",
                "files": no_fm_files,
            }
        )

    # Check 4: suspiciously similar filenames (Levenshtein distance < 3)
    stems = [p["stem"] for p in parsed]
    for i in range(len(stems)):
        for j in range(i + 1, len(stems)):
            dist = _levenshtein(stems[i], stems[j])
            if 0 < dist < 3 and dist != len(stems[j]):
                # Only flag if not already caught as duplicate name
                already_caught = any(
                    stems[i] in str(issue.get("files", []))
                    and stems[j] in str(issue.get("files", []))
                    for issue in issues
                )
                if not already_caught:
                    issues.append(
                        {
                            "severity": "warning",
                            "message": f"Filennames \"{stems[i]}.md\" and \"{stems[j]}.md\" are very similar (distance={dist}) — possible duplicate/shadow file",
                            "files": [f"{stems[i]}.md", f"{stems[j]}.md"],
                        }
                    )

    return issues
