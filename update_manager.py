"""
update_manager.py — Version check and update mechanism for oh-my-agents.

Fetches the latest version from GitHub releases and provides
interactive update capabilities.
"""

import shutil
from pathlib import Path
from typing import Optional, Tuple

SYSTEM_ROOT = Path(__file__).parent.resolve()
REPO_OWNER = "visualiaconsulting"
REPO_NAME = "oh-my-agents"


def get_current_version() -> str:
    """Read the current version from the VERSION file."""
    version_file = SYSTEM_ROOT / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return "0.0.0"


def check_for_updates() -> Tuple[bool, str, str]:
    """Check if a newer version is available on GitHub.

    Returns:
        Tuple of (has_update: bool, current_version: str, latest_version: str)
    """
    current = get_current_version()
    try:
        import requests

        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "oh-my-agents-updater",
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        latest = data.get("tag_name", "").lstrip("v")

        if not latest:
            return False, current, current

        has_update = _version_greater(latest, current)
        return has_update, current, latest

    except Exception:
        # Network error or API failure — silently fail
        return False, current, current


def run_update(target_version: Optional[str] = None) -> Tuple[bool, str]:
    """Run the update workflow.

    Downloads the latest (or specified) version from GitHub and
    updates framework sources in-place, preserving native agent configuration,
    installed skills, project instructions, virtualenvs and runtime data.
    Run an explicit export after the update to refresh generated configuration.

    Args:
        target_version: Specific version tag to install (e.g. "1.2.1").
                        If None, installs the latest available version.

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        import requests
        import tempfile
        import zipfile

        # Determine target version
        if target_version is None:
            has_update, current, target_version = check_for_updates()
            if not has_update:
                return True, f"Already up to date (v{current})."

        tag = target_version.lstrip("v")
        print(f"Downloading oh-my-agents v{tag}...")

        url = (
            f"https://github.com/{REPO_OWNER}/{REPO_NAME}/"
            f"archive/refs/tags/v{tag}.zip"
        )
        headers = {"User-Agent": "oh-my-agents-updater"}

        response = requests.get(url, headers=headers, timeout=60, stream=True)
        response.raise_for_status()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            zip_path = tmpdir_path / "update.zip"

            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Extract
            extract_dir = tmpdir_path / "extracted"
            extract_dir.mkdir()
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)

            # Find the extracted directory (oh-my-agents-<version>)
            extracted_dirs = list(extract_dir.glob(f"{REPO_NAME}-*"))
            if not extracted_dirs:
                return False, (
                    f"Unexpected archive structure: "
                    f"no {REPO_NAME}-* directory found."
                )

            source = extracted_dirs[0]

            # Preserved items (user data and VCS)
            preserved = {
                ".git",
                ".codex",
                ".agents",
                ".oh-my-agents",
                ".venv",
                "venv",
                "__pycache__",
                ".pytest_cache",
                ".ruff_cache",
                ".python-version",
            }

            for item in source.iterdir():
                dest = SYSTEM_ROOT / item.name

                # Skip preserved items — don't overwrite user data
                if item.name in preserved:
                    continue

                # Project instructions may contain user rules outside our block.
                if item.name.lower() == "agents.md" and dest.exists():
                    continue

                # Keep all existing project context, agents and runtime files.
                if item.name == ".opencode":
                    _merge_opencode_dir(item, dest)
                    continue

                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

            # Write the new version
            (SYSTEM_ROOT / "VERSION").write_text(f"{tag}\n", encoding="utf-8")

            return True, (
                f"Successfully updated to v{tag}. "
                "Run 'python main.py --version' to verify. "
                "Native configuration and project instructions were preserved. "
                "Preview an explicit --export --dry-run before refreshing agents."
            )

    except Exception as e:
        return False, f"Update failed: {e}"


def _merge_opencode_dir(source: Path, dest: Path) -> None:
    """Seed missing OpenCode files without replacing project-owned instructions.

    An existing agent collection is left intact as a whole, even when a new
    release adds roles. Mixing generations could reactivate obsolete roles.
    The normal exporter provides the review/backup/ownership workflow instead.
    """
    context_src = source / "context.md"
    if context_src.exists() and not (dest / "context.md").exists():
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(context_src, dest / "context.md")

    agents_src = source / "agents"
    if agents_src.exists():
        agents_dest = dest / "agents"
        if agents_dest.exists() and any(agents_dest.glob("*.md")):
            return
        agents_dest.mkdir(parents=True, exist_ok=True)
        for agent_file in agents_src.glob("*.md"):
            shutil.copy2(agent_file, agents_dest / agent_file.name)


def _version_greater(a: str, b: str) -> bool:
    """Compare two semantic version strings. Returns True if a > b."""
    try:
        from packaging.version import Version

        return Version(a) > Version(b)
    except ImportError:
        # Fallback: simple (major, minor, patch) tuple comparison
        def parse(v: str) -> tuple:
            parts = v.split(".")
            return tuple(int(p) for p in parts[:3] if p.isdigit())

        try:
            return parse(a) > parse(b)
        except (ValueError, IndexError):
            return False
