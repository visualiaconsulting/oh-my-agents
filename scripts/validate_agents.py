"""Read-only validation of bundled OpenCode and native Codex configuration."""
import argparse
import json
import sys
from pathlib import Path

SYSTEM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SYSTEM_ROOT))

import tomlkit  # noqa: E402

from adapters.codex import render_files  # noqa: E402
from agent_catalog import SPECIALISTS, load_catalog, load_profile  # noqa: E402
from utils import validate_agent_directory  # noqa: E402


def _codex_compat(root: Path, actual: dict) -> str:
    """Prefer recorded ownership metadata; infer only when it has no mode."""
    manifest_path = root / ".oh-my-agents/exports/codex.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("Invalid Codex export manifest")
        recorded = manifest.get("codex_compat")
        if recorded is not None:
            if recorded not in ("modern", "legacy"):
                raise ValueError(f"Unknown recorded Codex compatibility mode: {recorded}")
            return recorded
    agents = actual.get("agents", {})
    if isinstance(agents, dict) and "max_threads" in agents and not any(
        name in agents for name in ("enabled", "max_concurrent_threads_per_session")
    ):
        return "legacy"
    return "modern"


def validate_codex(root: Path, require: bool = False) -> list:
    """Compare framework-owned native fields against the canonical render.

    Unrelated configuration fields are ignored. This checks configuration only;
    it neither contacts OpenAI nor claims model access for a signed-in account.
    """
    config_path = root / ".codex" / "config.toml"
    if not config_path.is_file():
        return ["Native Codex config is missing"] if require else []
    errors = []
    try:
        actual = tomlkit.parse(config_path.read_text(encoding="utf-8"))
        compatibility = _codex_compat(root, actual)
        profile = load_profile("chatgpt")
        profile["codex_compat"] = compatibility
        expected_files = render_files(root, load_catalog(), profile)
        expected = tomlkit.parse(expected_files[".codex/config.toml"])
        for field in ("model", "model_reasoning_effort"):
            if actual.get(field) != expected[field]:
                errors.append(f"Codex {field} differs from the ChatGPT profile")
        actual_agents = actual.get("agents", {})
        expected_agents = expected["agents"]
        if not isinstance(actual_agents, dict):
            return errors + ["Codex agents must be a TOML table"]
        agent_fields = ("max_threads",) if compatibility == "legacy" else (
            "enabled", "max_concurrent_threads_per_session"
        )
        for field in agent_fields:
            if actual_agents.get(field) != expected_agents[field]:
                errors.append(f"Codex agents.{field} differs from the profile")
        if compatibility == "legacy":
            features = actual.get("features", {})
            if not isinstance(features, dict) or features.get("multi_agent") is not True:
                errors.append("Legacy Codex requires features.multi_agent = true")
            if any(field in actual_agents for field in ("enabled", "max_concurrent_threads_per_session")):
                errors.append("Legacy Codex must not contain modern agents settings")
        registered = {name for name, value in actual_agents.items() if isinstance(value, dict)}
        if registered != set(SPECIALISTS):
            errors.append("Codex must register exactly the four catalog specialists")
        if compatibility == "modern" and "max_threads" in actual_agents:
            errors.append("Remove the legacy max_threads alias before exporting")
        for role in SPECIALISTS:
            entry = actual_agents.get(role, {})
            if not isinstance(entry, dict):
                errors.append(f"Missing or invalid registration: {role}")
                continue
            for field in ("description", "config_file"):
                if entry.get(field) != expected_agents[role][field]:
                    errors.append(f"Codex {role}.{field} differs from the catalog")
            # Never follow arbitrary config_file paths while validating.
            relative = f"agents/{role}.toml"
            if entry.get("config_file") != relative:
                continue
            path = root / ".codex" / relative
            try:
                path.resolve().relative_to((root / ".codex").resolve())
            except ValueError:
                errors.append(f"Codex agent path escapes .codex: {role}")
                continue
            if not path.is_file():
                errors.append(f"Missing native agent: {role}")
                continue
            agent = tomlkit.parse(path.read_text(encoding="utf-8"))
            canonical = tomlkit.parse(expected_files[f".codex/{relative}"])
            for field in ("name", "description", "model", "model_reasoning_effort", "developer_instructions"):
                if agent.get(field) != canonical[field]:
                    errors.append(f"Codex {role}.{field} differs from its source")
        filenames = {p.stem for p in (root / ".codex/agents").glob("*.toml")}
        if filenames != set(SPECIALISTS):
            errors.append("Native agent directory must contain exactly four specialists")
        instruction_name = next(name for name in expected_files if name.lower() == "agents.md")
        instruction_path = root / instruction_name
        if not instruction_path.is_file() or instruction_path.read_text(encoding="utf-8") != expected_files[instruction_name]:
            errors.append("Managed orchestrator instructions differ from their source")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        errors.append(f"Invalid native Codex configuration: {exc}")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-codex", action="store_true",
                        help="Fail if the repository has no native Codex export")
    args = parser.parse_args(argv)
    agent_dir = SYSTEM_ROOT / ".opencode" / "agents"
    if not agent_dir.is_dir() or not any(agent_dir.glob("*.md")):
        print("ERROR: no bundled OpenCode agents found")
        return 1
    issues = validate_agent_directory(agent_dir)
    for issue in issues:
        print(f"{issue['severity'].upper()}: {issue['message']}")
    errors = validate_codex(SYSTEM_ROOT, require=args.require_codex)
    for error in errors:
        print(f"ERROR: {error}")
    if errors or any(issue["severity"] == "error" for issue in issues):
        return 1
    print("Agent configuration validated (model access is not checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
