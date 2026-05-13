"""
skill_registry.py — Skill management for oh-my-agents

Downloads, installs, and manages skills from skills.sh ecosystem.
Skills are stored in .opencode/skills/ as markdown files.
"""
import re
from pathlib import Path
from typing import Optional

from utils import (
    get_skills_dir,
    get_opencode_dir,
    safe_json_load,
    safe_json_save,
    truncate_text,
)

SKILLS_REGISTRY_URL = "https://skills.sh"
SKILLS_API_SEARCH = "https://skills.sh/api/search"


class SkillRegistry:
    """Manages skill installation and context injection."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent
        self.skills_dir = get_skills_dir(self.project_root)
        self._registry_cache = None

    def list_skills(self) -> list:
        """List all installed skills."""
        if not self.skills_dir.exists():
            return []

        skills = []
        for skill_file in sorted(self.skills_dir.glob("*.md")):
            try:
                with open(skill_file, "r", encoding="utf-8") as f:
                    content = f.read()

                metadata = self._parse_skill_header(content)
                skills.append({
                    "name": skill_file.stem,
                    "file": str(skill_file),
                    "description": metadata.get("description", ""),
                    "source": metadata.get("source", "local"),
                })
            except OSError:
                continue

        return skills

    def install_skill(self, identifier: str) -> bool:
        """Install a skill from skills.sh or a local file.

        Identifier formats:
            - owner/repo/skill-name  (from skills.sh)
            - owner/repo             (installs default skill from repo)
            - /path/to/file.md       (local file)
        """
        if not self.skills_dir.exists():
            self.skills_dir.mkdir(parents=True, exist_ok=True)

        if Path(identifier).is_file() and identifier.endswith(".md"):
            return self._install_local_file(Path(identifier))

        return self._install_from_skills_sh(identifier)

    def remove_skill(self, name: str) -> bool:
        """Remove an installed skill."""
        skill_file = self.skills_dir / f"{name}.md"
        if skill_file.exists():
            skill_file.unlink()
            return True
        return False

    def get_skill_content(self, name: str) -> Optional[str]:
        """Get the full content of an installed skill."""
        skill_file = self.skills_dir / f"{name}.md"
        if not skill_file.exists():
            return None

        try:
            with open(skill_file, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            return None

    def inject_skills_context(self, skill_names: Optional[list] = None) -> str:
        """Generate a context string with active skills.

        If skill_names is None, injects all installed skills.
        """
        skills = self.list_skills()
        if not skills:
            return ""

        if skill_names:
            skills = [s for s in skills if s["name"] in skill_names]

        if not skills:
            return ""

        lines = []
        lines.append("## Active Skills")
        lines.append("")

        for skill in skills:
            content = self.get_skill_content(skill["name"])
            if content:
                lines.append(f"### Skill: {skill['name']}")
                lines.append("")
                if skill.get("description"):
                    lines.append(f"*{skill['description']}*")
                    lines.append("")
                lines.append(content)
                lines.append("")
                lines.append("---")
                lines.append("")

        return "\n".join(lines)

    def search_skills(self, query: str) -> list:
        """Search for skills on skills.sh.

        Returns a list of dicts with name, description, repo, installs.
        """
        try:
            import requests
        except ImportError:
            return [{"error": "requests library not installed. Run: pip install requests"}]

        try:
            response = requests.get(
                f"{SKILLS_REGISTRY_URL}/api/search",
                params={"q": query},
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("skills", data if isinstance(data, list) else [])
        except Exception:
            pass

        return self._fallback_search(query)

    def update_context_md(self, skill_names: Optional[list] = None):
        """Update .opencode/context.md with active skills."""
        context_file = get_opencode_dir(self.project_root) / "context.md"
        if not context_file.exists():
            return

        try:
            with open(context_file, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            return

        skills_context = self.inject_skills_context(skill_names)

        if not skills_context:
            return

        marker = "## Active Skills"
        if marker in content:
            content = re.sub(
                rf"{marker}.*?(?=---\n|$)",
                skills_context.rstrip(),
                content,
                flags=re.DOTALL,
            )
        else:
            content = content.rstrip() + "\n\n" + skills_context.rstrip()

        try:
            with open(context_file, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError:
            pass

    def _install_local_file(self, filepath: Path) -> bool:
        """Install a skill from a local .md file."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            return False

        metadata = self._parse_skill_header(content)
        name = metadata.get("name", filepath.stem)

        target = self.skills_dir / f"{name}.md"
        try:
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except OSError:
            return False

    def _install_from_skills_sh(self, identifier: str) -> bool:
        """Install a skill from skills.sh by downloading from GitHub.
        
        Tries multiple URL patterns to find the skill file.
        """
        try:
            import requests
        except ImportError:
            return False

        parts = identifier.split("/")
        if len(parts) < 2:
            return False

        owner = parts[0]
        repo = parts[1]
        skill_name = parts[2] if len(parts) > 2 else repo

        # Define candidate URL patterns
        # 1. Direct file in root (original)
        # 2. In skills/ directory as [skill_name].md
        # 3. In skills/[skill_name]/SKILL.md (neondatabase style)
        # 4. In plugins/*/skills/[skill_name]/SKILL.md (wshobson style)
        
        base_github = f"https://raw.githubusercontent.com/{owner}/{repo}"
        
        # We'll try both main and master branches
        branches = ["main", "master"]
        
        patterns = [
            "{base}/{branch}/{name}.md",
            "{base}/{branch}/skills/{name}.md",
            "{base}/{branch}/skills/{name}/SKILL.md",
        ]
        
        # Special case for wshobson-style plugins (requires searching, but we'll try common ones)
        common_plugins = ["python-development", "javascript-development", "backend-development", "developer-essentials"]
        for plugin in common_plugins:
            patterns.append(f"{{base}}/{{branch}}/plugins/{plugin}/skills/{{name}}/SKILL.md")

        for branch in branches:
            for pattern in patterns:
                url = pattern.format(base=base_github, branch=branch, name=skill_name)
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        content = response.text
                        target = self.skills_dir / f"{skill_name}.md"
                        with open(target, "w", encoding="utf-8") as f:
                            f.write(content)
                        return True
                except Exception:
                    continue

        return False

    def _fallback_search(self, query: str) -> list:
        """Fallback search that returns a helpful message."""
        return [{
            "name": "search-unavailable",
            "description": f"Direct search unavailable. Browse skills at {SKILLS_REGISTRY_URL}/?q={query}",
            "source": "fallback",
        }]

    def _parse_skill_header(self, content: str) -> dict:
        """Parse YAML-like header from skill markdown."""
        if not content.startswith("---"):
            return {}
        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}
        try:
            import yaml
            metadata = yaml.safe_load(parts[1])
            return metadata if isinstance(metadata, dict) else {}
        except (yaml.YAMLError, Exception):
            return {}
