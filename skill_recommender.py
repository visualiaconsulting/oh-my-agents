"""
skill_recommender.py — Automatic skill recommendation for oh-my-agents

Analyzes the current project structure and recommends relevant skills
from the built-in catalog. Can auto-install with user confirmation.
"""
import json
from pathlib import Path
from typing import List, Optional, Tuple
from fnmatch import fnmatch

from utils import get_system_root
from skill_registry import SkillRegistry


class SkillRecommender:
    """Recommends skills based on project file analysis."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.catalog = self._load_catalog()

    def _load_catalog(self) -> List[dict]:
        """Load the built-in skills catalog."""
        catalog_paths = [
            self.project_root / ".opencode" / "skills_catalog.json",
            get_system_root() / "skills_catalog.json",
        ]
        for path in catalog_paths:
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    return data.get("skills", [])
                except (json.JSONDecodeError, OSError):
                    continue
        return []

    def analyze_project(self) -> List[dict]:
        """Analyze project files and return matching skills sorted by relevance."""
        if not self.project_root.exists():
            return []

        matches = []
        for skill in self.catalog:
            score = self._score_skill(skill)
            if score > 0:
                matches.append({"skill": skill, "score": score})

        # Sort by score descending, then by priority
        matches.sort(key=lambda x: (x["score"], -x["skill"].get("priority", 99)), reverse=True)
        return matches

    def _score_skill(self, skill: dict) -> int:
        """Calculate match score (0 = no match)."""
        score = 0
        triggers = skill.get("triggers", [])
        trigger_content = skill.get("trigger_content", [])

        # Check file triggers (glob patterns)
        for trigger in triggers:
            if self._matches_trigger(trigger):
                score += 10
                break  # Only count once per skill

        # Check content triggers (file contents)
        if trigger_content and score == 0:
            if self._matches_content(trigger_content):
                score += 5

        return score

    # Directories to skip during project scanning
    _SKIP_DIRS = {".git", ".opencode", "node_modules", "__pycache__",
                  ".pytest_cache", ".venv", "venv", ".mypy_cache", ".tox"}

    def _should_skip(self, path: Path) -> bool:
        """Check if a path is inside a directory that should be skipped."""
        parts = set(path.parts)
        return bool(parts & self._SKIP_DIRS)

    def _matches_trigger(self, pattern: str) -> bool:
        """Check if any file in the project matches the glob pattern."""
        try:
            for path in self.project_root.rglob("*"):
                if path.is_file() and not self._should_skip(path):
                    relative = str(path.relative_to(self.project_root))
                    if fnmatch(relative, pattern) or fnmatch(path.name, pattern):
                        return True
        except (OSError, ValueError):
            pass
        return False

    def _matches_content(self, keywords: List[str]) -> bool:
        """Check if any project file contains the keywords."""
        checked_files = 0
        max_files = 50  # Limit to avoid performance issues

        try:
            for path in self.project_root.rglob("*"):
                if path.is_file() and not self._should_skip(path):
                    if path.stat().st_size >= 50_000:  # Skip large files
                        continue
                    if checked_files >= max_files:
                        break
                    checked_files += 1
                    try:
                        content = path.read_text(encoding="utf-8", errors="ignore")
                        for keyword in keywords:
                            if keyword.lower() in content.lower():
                                return True
                    except (OSError, UnicodeDecodeError):
                        continue
        except OSError:
            pass
        return False

    def install_from_catalog(self, skill_id: str) -> bool:
        """Install a skill from the built-in catalog by ID."""
        sr = SkillRegistry(project_root=self.project_root)
        for skill in self.catalog:
            if skill.get("id") == skill_id:
                source = skill.get("source", "")
                if source:
                    return sr.install_skill(source)
                return False
        return False

    def get_recommendations(self, limit: int = 5) -> List[dict]:
        """Get top N recommended skills."""
        matches = self.analyze_project()
        return [m["skill"] for m in matches[:limit]]

    def get_installable_recommendations(self, limit: int = 5) -> List[dict]:
        """Get recommendations that are NOT already installed."""
        sr = SkillRegistry(project_root=self.project_root)
        installed = {s["name"] for s in sr.list_skills()}

        recommendations = self.get_recommendations(limit=limit * 2)
        return [s for s in recommendations if s["id"] not in installed][:limit]

    def install_recommendations(self, skills: List[dict]) -> List[Tuple[str, bool]]:
        """Install a list of recommended skills."""
        sr = SkillRegistry(project_root=self.project_root)
        results = []
        for skill in skills:
            source = skill.get("source", "")
            if source:
                success = sr.install_skill(source)
                results.append((skill["id"], success))
            else:
                results.append((skill["id"], False))
        return results

    def generate_report(self) -> str:
        """Generate a markdown report of recommendations."""
        recommendations = self.get_recommendations()
        if not recommendations:
            return "No skill recommendations for this project."

        lines = ["## Recommended Skills", ""]
        for i, skill in enumerate(recommendations, 1):
            lines.append(f"{i}. **{skill['name']}** -- {skill['description']}")
            lines.append(f"   Tags: {', '.join(skill.get('tags', []))}")
            lines.append("")

        lines.append("Install with:")
        lines.append("```bash")
        for skill in recommendations:
            lines.append(f"python main.py --skills-install {skill['source']}")
        lines.append("```")
        return "\n".join(lines)
