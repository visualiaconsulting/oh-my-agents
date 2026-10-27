"""Project-scoped runtime setup and honest, manually recorded continuity."""
import json
import shutil
from pathlib import Path


def active_runtime(root):
    """Read local selection, falling back to native Codex config or legacy Go."""
    path = Path(root) / ".oh-my-agents" / "active.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Active runtime configuration must be a JSON object")
        if data.get("runtime") in ("codex", "opencode"):
            return data["runtime"], data.get("profile")
        raise ValueError("Invalid active runtime; export a valid profile")
    if (Path(root) / ".codex" / "config.toml").exists():
        return "codex", "chatgpt"
    from plan_manager import PlanManager
    return "opencode", PlanManager(project_root=Path(root)).plan


def select_runtime(root, runtime, profile):
    from adapters import _atomic_write, _safe_path
    from agent_catalog import load_profile
    if load_profile(profile)["runtime"] != runtime:
        raise ValueError("Selected runtime/profile do not match")
    root = Path(root).resolve()
    path = _safe_path(root, ".oh-my-agents/active.json")
    _atomic_write(path, json.dumps({"runtime": runtime, "profile": profile}, indent=2) + "\n")


def configured_agents(root, runtime, profile=None):
    """Inspect saved native files, never label unverified agents as running."""
    if runtime == "opencode":
        from main import load_agents
        return load_agents(working_root=root)
    import tomlkit
    config_path = Path(root) / ".codex" / "config.toml"
    if not config_path.exists():
        return []
    config = tomlkit.parse(config_path.read_text(encoding="utf-8"))
    agents = [{"name": "@orchestrator", "role": "Coordinator", "model": config.get("model", "unknown")}]
    directory = Path(root) / ".codex" / "agents"
    for path in sorted(directory.glob("*.toml")):
        data = tomlkit.parse(path.read_text(encoding="utf-8"))
        agents.append({"name": "@" + data.get("name", path.stem), "role": "Specialist",
                       "model": data.get("model", "inherited")})
    return agents


def recorded_sessions(root, session_id=None):
    """Prefer SQLite records; retain legacy JSON history when no DB rows exist."""
    root = Path(root)
    if (root / ".opencode" / "project.db").exists():
        from project_db import ProjectDB
        with ProjectDB(root) as db:
            result = db.get_session(session_id) if session_id else db.list_sessions(limit=100)
        if result:
            return result
    from session_manager import SessionManager
    manager = SessionManager(project_root=root)
    return manager.get_session(session_id) if session_id else manager.list_sessions()


def export_project(root, runtime, profile=None, dry_run=False, inventory=None, codex_compat=None):
    from adapters import export_runtime
    overrides = None
    if runtime == "opencode":
        from plan_manager import PlanManager
        manager = PlanManager(plan=profile, project_root=Path(root))
        profile = manager.plan
        overrides = {role: manager.get_model(role) for role in manager.ALL_ROLES}
    result = export_runtime(root, runtime, profile, dry_run=dry_run, available_models=inventory,
                            model_overrides=overrides, codex_compat=codex_compat)
    if not dry_run:
        select_runtime(root, runtime, result["profile"])
    return result


def print_export_report(result):
    from cli.ui import console
    console.print(f"{result['runtime']} / {result['profile']} - "
                  f"{'preview' if result['dry_run'] else 'exported'}", markup=False)
    if result.get("codex_compat"):
        console.print(f"Codex format: {result['codex_compat']}", markup=False)
    for item in result["files"]:
        console.print(f"  {item['action']:<10} {item['path']}", markup=False)
    for warning in result.get("warnings", []):
        console.print(f"  Warning: {warning}", markup=False)
    if result.get("backup"):
        console.print(f"  Backup: {result['backup']}", markup=False)
    console.print("Model access: validated against supplied inventory." if result.get("model_validation") == "supplied_inventory"
                  else "Model access: configuration checked; sign-in, account access and inference not tested.", markup=False)


def read_inventory(filename):
    data = json.loads(Path(filename).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("models", data.get("data"))
    if not isinstance(data, list):
        raise ValueError("Model inventory must be a JSON list or an object with models/data")
    ids = [item.get("id") if isinstance(item, dict) else item for item in data]
    if any(not isinstance(item, str) or not item.strip() for item in ids):
        raise ValueError("Model inventory entries must be nonempty model IDs")
    return ids


def doctor(root, runtime, profile=None, inventory=None, codex_compat=None):
    from cli.ui import console, print_diagnostic_panel
    from agent_catalog import ROLES
    result = export_project(root, runtime, profile, dry_run=True, inventory=inventory, codex_compat=codex_compat)
    cli = shutil.which(runtime)
    native = configured_agents(root, runtime, profile)
    checks = [
        {"name": "Runtime", "ok": bool(cli), "detail": cli or f"{runtime} CLI not found on PATH"},
        {"name": "Profile", "ok": True, "detail": result["profile"]},
        {"name": "Catalog", "ok": True, "detail": f"{len(ROLES)} roles"},
        {"name": "Project export", "ok": bool(native), "detail": f"{len(native)} native definitions found"},
        {"name": "Export drift", "ok": result["changed"] == 0, "detail": f"{result['changed']} pending changes"},
    ]
    print_diagnostic_panel(checks)
    for warning in result["warnings"]:
        console.print(warning, markup=False)
    console.print("Sign in with ChatGPT in Codex and verify the four models in its model picker. "
                  "This diagnostic does not authenticate or run a model.", markup=False)
    return checks


def record_session(root, filename, runtime, profile):
    from agent_catalog import ROLES, load_profile
    from project_db import ProjectDB
    data = json.loads(Path(filename).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("summary"), str) or not data["summary"].strip():
        raise ValueError("Session record must be an object with a nonempty summary")
    data.setdefault("runtime", runtime)
    data.setdefault("profile", profile if data["runtime"] == runtime else
                    ("chatgpt" if data["runtime"] == "codex" else "go"))
    if load_profile(data["profile"])["runtime"] != data["runtime"]:
        raise ValueError("Recorded runtime/profile do not match")
    data.setdefault("role", data.get("agent") or "orchestrator")
    if data["role"] not in ROLES:
        raise ValueError("Session role must be one of the five catalog roles")
    if not isinstance(data.get("model", ""), str):
        raise ValueError("Session model must be a string (leave empty if unknown)")
    # A chosen profile is not proof of the model actually used. Never infer it.
    with ProjectDB(Path(root)) as db:
        db.ensure_project_meta()
        return db.save_session(data)


def handle_runtime_args(args, parser, root):
    """Return true if a runtime/continuity command was handled."""
    from cli.ui import console
    action = (args.export or args.install_design_skills or args.record_session or args.resume_context
              or args.enable_auto_session or args.inject_context or args.doctor)
    if args.dry_run and not (args.export or args.install_design_skills):
        parser.error("--dry-run requires --export or --install-design-skills")
    if args.dry_run and (args.record_session or args.resume_context or args.enable_auto_session or args.inject_context):
        parser.error("--dry-run cannot be combined with continuity actions")
    if args.available_models and not (args.export or args.doctor):
        parser.error("--available-models requires --export or --doctor")
    if args.codex_compat and not (args.export or args.doctor):
        parser.error("--codex-compat requires --export or --doctor")
    if args.plan and (args.runtime == "codex" or args.profile):
        parser.error("--plan is an OpenCode option; use --runtime/--profile instead")
    if args.install_global and args.runtime == "codex":
        parser.error("Codex uses project-scoped --export; --install-global is for OpenCode")
    if args.profile and not action and not args.runtime:
        parser.error("Use --profile with --runtime and an action such as --export")
    if not action and args.runtime and args.profile:
        from agent_catalog import load_profile
        if load_profile(args.profile)["runtime"] != args.runtime:
            parser.error("Selected runtime/profile do not match")
    if not action:
        return False
    if args.plan or args.setup or args.install_global or args.uninstall or args.update or args.check_updates:
        parser.error("Runtime actions cannot be combined with legacy setup/update actions")
    try:
        selected_runtime, selected_profile = active_runtime(root)
        runtime = args.runtime or ("codex" if args.profile == "chatgpt" else selected_runtime)
        profile = args.profile or (selected_profile if runtime == selected_runtime else None)
        profile = profile or ("chatgpt" if runtime == "codex" else "go")
        from agent_catalog import load_profile
        if load_profile(profile)["runtime"] != runtime:
            raise ValueError("Selected runtime/profile do not match")
        inventory = read_inventory(args.available_models) if args.available_models else None
        if args.install_design_skills and runtime != "codex":
            raise ValueError("Design skill installation requires --runtime codex")
        # Validate all local inputs before an export can write anything.
        if args.record_session and (args.export or args.install_design_skills):
            raise ValueError("Record sessions separately from installation")
        if args.export:
            print_export_report(export_project(root, runtime, profile, args.dry_run, inventory, args.codex_compat))
        if args.install_design_skills:
            from design_skills import install_design_skills
            result = install_design_skills(root, args.dry_run)
            console.print(json.dumps(result, ensure_ascii=False, indent=2), markup=False)
        if args.doctor:
            doctor(root, runtime, profile, inventory, args.codex_compat)
        if args.record_session:
            sid = record_session(root, args.record_session, runtime, profile)
            console.print(f"Session recorded: {sid}", markup=False)
        if args.resume_context or args.enable_auto_session or args.inject_context:
            from continuity import ContinuityManager
            with ContinuityManager(root) as cm:
                if args.resume_context:
                    console.print(cm.get_reentry_prompt() or "No recorded session history.", markup=False)
                if args.enable_auto_session:
                    if not cm.enable_auto_session():
                        raise OSError("Could not enable session flag")
                    console.print("OpenCode logger auto-session flag enabled. Codex sessions use --record-session.", markup=False)
                if args.inject_context:
                    updated = cm.inject_context_to_file()
                    console.print("OpenCode context updated." if updated else "No OpenCode context update (no file/history or no change).", markup=False)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    return True
