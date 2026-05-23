#!/usr/bin/env python3
"""
opencode_logger.py — Cross-platform OpenCode CLI wrapper with session logging.

Detects the real opencode binary, runs it, streams output to console
and simultaneously writes to a timestamped log file in the project's
.opencode/logs/ directory.
"""
import os
import sys
import shutil
import random
import string
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from plan_fallback import FallbackManager
import json
import hashlib


def find_real_opencode():
    """Find the real opencode binary, skipping this wrapper script.

    Uses shutil.which to locate the binary, then verifies it is not
    this script itself to avoid recursion.
    """
    this_script = Path(__file__).resolve()

    # shutil.which returns the first match in PATH
    real = shutil.which("opencode")
    if real is None:
        return None

    real_path = Path(real).resolve()

    # On Unix, if the wrapper shim (opencode-logger) was renamed to opencode,
    # it could point to us. Check for opencode_logger.py in the path.
    if real_path == this_script:
        # Also check for the shim named 'opencode-logger' pointing here
        return None

    # Check if the found binary is actually Python calling our script
    if sys.platform == "win32":
        # On Windows, shutil.which finds .bat, .cmd, .exe files
        # If it's our .bat shim, skip it
        if real_path.suffix.lower() in (".bat", ".cmd"):
            # Read the .bat file to check if it calls our script
            try:
                content = real_path.read_text(encoding="utf-8", errors="ignore")
                if "opencode_logger.py" in content:
                    # This is our shim — find the next opencode in PATH
                    return _find_next_in_path("opencode", skip=real_path)
            except OSError:
                pass

    return real_path


def _find_next_in_path(name, skip):
    """Find the next occurrence of `name` in PATH after skipping `skip`."""
    skip = Path(skip).resolve()
    found_first = False
    for path_dir in os.environ.get("PATH", "").split(os.pathsep):
        path_dir = path_dir.strip()
        if not path_dir:
            continue
        candidate = Path(path_dir) / name
        # On Windows, also check with extensions
        candidates = [candidate]
        if sys.platform == "win32":
            for ext in os.environ.get("PATHEXT", ".exe;.bat;.cmd").split(";"):
                candidates.append(Path(path_dir) / (name + ext))
        for c in candidates:
            if c.exists():
                resolved = c.resolve()
                if not found_first:
                    if resolved == skip:
                        found_first = True
                        continue
                if resolved != skip:
                    return resolved
    return None


def generate_log_filename():
    """Generate a log filename: opencode_YYYYMMDD_HHMMSS_<random4>.log"""
    now = datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    rand = ''.join(random.choices(string.digits, k=4))
    return f"opencode_{ts}_{rand}.log"


def stream_and_log(process, log_file):
    """Read process output line by line, write to console and log file simultaneously.

    Runs in a background thread to avoid blocking.
    Uses subprocess.PIPE with universal_newlines=True for text mode streaming.
    """
    try:
        with open(log_file, "a", encoding="utf-8") as lf:
            for line in process.stdout:
                # Write to console
                sys.stdout.write(line)
                sys.stdout.flush()
                # Write to log
                lf.write(line)
                lf.flush()
    except (IOError, OSError):
        # If logging fails, still try to echo to console
        for line in process.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()




def check_and_trigger_fallback(project_root, log_content, args):
    """Check log content for credit errors and trigger fallback if needed."""
    try:
        fm = FallbackManager(project_root)
        
        if not fm.detect_credit_error(log_content):
            return False
        
        current_plan = os.getenv("OPENCODE_PLAN", "go")
        
        if fm.is_fallback_active():
            return False
        
        next_plan = fm.get_next_fallback_plan(current_plan)
        if not next_plan:
            return False
        
        reason = ""
        for line in log_content.splitlines():
            if fm.detect_credit_error(line):
                reason = line.strip()[:200]
                break
        
        event = fm.trigger_fallback(current_plan, reason)
        if event:
            print(f"\n[oh-my-agents] WARNING: Credits exhausted on plan '{current_plan}'", file=sys.stderr)
            print(f"[oh-my-agents] Reason: {reason}", file=sys.stderr)
            print(f"[oh-my-agents] Run: python main.py --plan go to restore Go plan", file=sys.stderr)
            return True
        
        return False
    except Exception:
        return False

def auto_save_session(project_root, log_filepath, returncode, duration_seconds, args):
    """Auto-save a session record to the project database after OpenCode exits.
    
    This function:
    1. Reads the log file content
    2. Parses it to extract errors, warnings, files, commands
    3. Generates a session summary
    4. Saves to the project's SQLite database (.opencode/project.db)
    5. Updates the project's context.md with session history
    
    This only runs if the .opencode/.auto_session_enabled flag file exists
    in the project directory.
    """
    try:
        # Check if auto-session is enabled
        flag_file = project_root / ".opencode" / ".auto_session_enabled"
        if not flag_file.exists():
            return
        
        # Read the log file
        try:
            with open(log_filepath, "r", encoding="utf-8") as f:
                log_content = f.read()
        except (IOError, OSError):
            return
        
        if not log_content.strip():
            return
        
        # Import project modules (add project root to path if needed)
        import sys
        parent_dir = str(Path(__file__).resolve().parent.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        from utils import (
            generate_session_id,
            format_timestamp,
            get_current_git_branch,
            parse_openCode_log_content,
            truncate_text,
        )
        from project_db import ProjectDB
        
        # Parse log content
        parsed = parse_openCode_log_content(log_content)
        
        # Generate summary from the last part of the log (conclusions)
        summary_hint = parsed.get("summary_hint", "")
        summary = f"Auto-saved session. "
        if parsed["errors"]:
            summary += f"{len(parsed['errors'])} error(s) found. "
        if parsed["files_changed"]:
            summary += f"{len(parsed['files_changed'])} file(s) changed. "
        if summary_hint:
            summary += f"Context: {truncate_text(summary_hint, 200)}"
        else:
            summary += truncate_text(log_content.splitlines()[-1] if log_content.splitlines() else "", 200)
        
        # Build session data
        session_data = {
            "session_id": generate_session_id(),
            "timestamp": format_timestamp(),
            "agent": _detect_agent(args),
            "summary": summary,
            "log_file": str(log_filepath),
            "exit_code": returncode,
            "duration_seconds": duration_seconds,
            "raw_log_preview": log_content[:2000],
            "pending_tasks": [],
            "decisions": [],
            "files_changed": [{"filepath": f, "change_type": "modified"} for f in parsed.get("files_changed", [])],
            "errors": [{"error_message": e, "severity": "error"} for e in parsed.get("errors", [])][:20],
            "commands": [{"command": c, "exit_code": 0, "duration_ms": 0} for c in parsed.get("commands_run", [])][:20],
        }
        
        # Save to project DB
        db = ProjectDB(project_root)
        try:
            session_id = db.save_session(session_data)
            
            # Update context.md
            context = db.inject_context(max_sessions=3)
            if context:
                context_file = project_root / ".opencode" / "context.md"
                if context_file.exists():
                    try:
                        content = context_file.read_text(encoding="utf-8")
                    except OSError:
                        content = ""
                    from utils import inject_markdown_section
                    updated = inject_markdown_section(content, "## Recent Session History", context)
                    if updated != content:
                        context_file.write_text(updated, encoding="utf-8")
            
            # Print brief notification (to stderr so it doesn't mix with pipe output)
            import sys as _sys
            print(f"\n[oh-my-agents] Session saved: {session_id} ({len(parsed.get('files_changed', []))} files, {len(parsed.get('errors', []))} errors)", file=_sys.stderr)
            
            # Also save JSON backup for backward compatibility
            try:
                from utils import get_sessions_dir, safe_json_save
                sessions_dir = get_sessions_dir(project_root)
                json_session = {
                    "session_id": session_data["session_id"],
                    "timestamp": session_data["timestamp"],
                    "agent": session_data["agent"],
                    "summary": session_data["summary"],
                    "errors": parsed.get("errors", [])[:20],
                    "pending_tasks": [],
                    "files_changed": parsed.get("files_changed", []),
                    "decisions": [],
                    "commands_run": parsed.get("commands_run", [])[:20],
                    "warnings": parsed.get("warnings", [])[:20],
                }
                safe_json_save(sessions_dir / f"{session_data['session_id']}.json", json_session)
            except Exception:
                pass  # JSON backup is best-effort
                
        finally:
            db.close()
            
    except Exception:
        # Auto-save should never crash the wrapper
        pass


def _detect_agent(args):
    """Detect which agent was used from the command-line arguments."""
    for i, arg in enumerate(args):
        if arg in ("--agent", "-a") and i + 1 < len(args):
            return args[i + 1]
        if arg.startswith("--agent="):
            return arg.split("=", 1)[1]
    return "unknown"


def run():
    """Main entry point for the logger wrapper."""
    # Find the real opencode binary
    real_opencode = find_real_opencode()
    if real_opencode is None:
        print("ERROR: Could not find the real opencode binary.", file=sys.stderr)
        print("Make sure opencode is installed and available in your PATH.", file=sys.stderr)
        print("If you renamed 'opencode-logger' to 'opencode', undo that change.", file=sys.stderr)
        sys.exit(1)

    # Collect arguments (skip this script's name)
    args = sys.argv[1:]

    # Determine project root (CWD at the time of invocation)
    project_root = Path.cwd().resolve()

    # Ensure the logs directory exists
    logs_dir = project_root / ".opencode" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Generate log filename
    log_filename = generate_log_filename()
    log_filepath = logs_dir / log_filename

    # Build the command
    cmd = [str(real_opencode)] + args

    # Prepare log header
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = (
        f"# oh-my-agents session log\n"
        f"# Started: {now}\n"
        f"# Command: opencode {' '.join(args)}\n"
        f"# Working directory: {project_root}\n"
        f"#\n"
    )

    # Write header to log file
    try:
        with open(log_filepath, "w", encoding="utf-8") as lf:
            lf.write(header)
    except (IOError, OSError) as e:
        print(f"ERROR: Could not write log file {log_filepath}: {e}", file=sys.stderr)
        # Fall back to running without logging
        sys.exit(subprocess.call(cmd))

    # Start the real opencode process
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
        )
    except OSError as e:
        print(f"ERROR: Could not start opencode: {e}", file=sys.stderr)
        sys.exit(1)

    # Stream output in a thread
    stream_thread = threading.Thread(
        target=stream_and_log,
        args=(process, log_filepath),
        daemon=True,
    )
    stream_thread.start()

    # Wait for the process to complete
    returncode = process.wait()
    stream_thread.join(timeout=5)

    # Append footer to log file
    ended = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    footer = (
        f"#\n"
        f"# Exit code: {returncode}\n"
        f"# Ended: {ended}\n"
    )
    try:
        with open(log_filepath, "a", encoding="utf-8") as lf:
            lf.write(footer)
    except (IOError, OSError):
        pass

    # Check for credit errors and trigger fallback if needed
    try:
        with open(log_filepath, "r", encoding="utf-8") as lf:
            log_content = lf.read()
        check_and_trigger_fallback(project_root, log_content, args)
    except Exception:
        pass

    # Auto-save session if enabled
    start_time_str = now  # captured earlier as datetime.now().strftime(...)
    duration = (datetime.now() - datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")).total_seconds()
    auto_save_session(project_root, log_filepath, returncode, duration, args)

    sys.exit(returncode)


if __name__ == "__main__":
    run()
