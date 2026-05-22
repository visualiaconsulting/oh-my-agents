# Agent Status — oh-my-agents

This document describes the configuration, status, and architecture of the project's multi-agent system.

---

## 📋 System Overview

The project implements an **Orchestrator and Specialists** architecture on the default **OpenCode Go** plan, with dynamic adaptation capability to other plans (Zen, API, Enterprise, OpenRouter, Copilot, Ollama) via the `PlanManager`.

| Component | Description |
|------------|-------------|
| **Orchestrator** | Main agent that breaks down complex tasks and delegates to sub-agents |
| **Specialists** | Secondary agents with specific roles (code, QA, data) |
| **PlanManager** | Python module that detects the active plan and assigns models |
| **SessionManager** | Manages session logs, bitacora, and continuity between sessions |
| **SkillRegistry** | Downloads and manages skills from skills.sh ecosystem |

---

## 🤖 Configured Agents

| Agent | Role | Model (Go Plan) | Permissions | Description |
| :--- | :--- | :--- | :--- | :--- |
| **@orchestrator** | Main Coordinator | `opencode-go/deepseek-v4-pro` | `Read, Task` | Breaks down complex tasks and delegates to sub-agents. Does NOT write code or execute commands. (SWE-Bench Pro 58.6%) |
| **@code-analyst** | Senior Engineer | `opencode-go/deepseek-v4-flash` | `Edit, Bash, Read` | Clean code and architecture implementation. (GPQA Diamond 90.1%) |
| **@validator** | QA Specialist | `opencode-go/qwen3.6-plus` | `Read Only` | Validation, linting, and quality review. No editing or bash. (94% math precision) |
| **@bulk-processor** | Data Processor | `opencode-go/qwen3.5-plus` | `Edit, Bash, Read` | Repetitive, high-volume tasks (hidden). (MMLU-Pro 87.5%) |
| **@subagent** | Debugger/Fallback | `opencode-go/glm-5.1` | `Edit, Bash, Read` | Generic agent for debugging and auxiliary tasks. |
| **@summarizer** | Session Analyst | `opencode-go/minimax-m2.5` | `Edit, Bash, Read` | Lightweight session summarizer, log analysis, and project continuity. |
| **@frontend** | UI Specialist | `opencode-go/qwen3.6-plus` | `Edit, Bash, Read` | Frontend — React, TypeScript, Tailwind, UI iteration. (SWE-Bench Verified 78.8%, 1M context) |
| **@ml-specialist** | ML Engineer | `opencode-go/minimax-m2.7` | `Edit, Bash, Read` | ML and data pipelines — training, inference, MLOps. (MLE-Bench Lite 66.6%) |

### 🔍 Permission Details by Agent

| Agent | edit | bash | read | task |
|--------|:----:|:----:|:----:|:----:|
| **@orchestrator** | ❌ deny | ❌ deny | ✅ allow | ✅ allow |
| **@code-analyst** | ✅ allow | ✅ allow | ✅ allow | ❌ deny |
| **@validator** | ❌ deny | ❌ deny | ✅ allow | ❌ deny |
| **@bulk-processor** | ✅ allow | ✅ allow | ✅ allow | ❌ deny |
| **@subagent** | ✅ allow | ✅ allow | ✅ allow | ❌ deny |
| **@summarizer** | ✅ allow | ✅ allow | ✅ allow | ❌ deny |
| **@frontend** | ✅ allow | ✅ allow | ✅ allow | ❌ deny |
| **@ml-specialist** | ✅ allow | ✅ allow | ✅ allow | ❌ deny |

---

## 🛠️ Code Infrastructure

### `plan_manager.py` — Dynamic Configuration Core

The `PlanManager` is the logical brain that manages agent configuration based on the detected plan:

- **Plan Detection:** Automatically identifies whether you are in `go`, `zen`, `api`, `enterprise`, `openrouter`, `copilot`, or `ollama` using environment variables and configuration files.
- **Model Mapping:** Maps each role (`orchestrator`, `code-analyst`, `validator`, `bulk-processor`, `subagent`, `summarizer`) to the optimal model for the active plan.
- **Fallbacks:** Provides backup models if the primary one is not available.
- **API Key Validation:** Verifies that external providers have the necessary credentials (only for `api` and `openrouter` plans).

**Default Models in Go Plan:**

| Role | Model |
|:---|:---|
| Orchestrator | `opencode-go/deepseek-v4-pro` |
| Code Analyst | `opencode-go/deepseek-v4-flash` |
| Validator | `opencode-go/qwen3.6-plus` |
| Bulk Processor | `opencode-go/qwen3.5-plus` |
| Subagent | `opencode-go/glm-5.1` |
| Summarizer | `opencode-go/minimax-m2.5` |
| Frontend | `opencode-go/qwen3.6-plus` |
| ML Specialist | `opencode-go/minimax-m2.7` |
| Fallback | `opencode-go/minimax-m2.5` |

### ~~`opencode.jsonc`~~ — Removed

> **Note:** The `opencode.jsonc` file was removed because it caused configuration conflicts. OpenCode reads configuration directly from the `.opencode/agents/*.md` files.

### `main.py` — System CLI

Command-line interface that:
- Displays the multi-agent system banner
- Runs the setup wizard (`--setup`) if no agents are defined
- Loads and displays agent status via `find_agent_source()` — 3-level discovery (local project → global → repo bundled)
- Diagnoses environment issues (`--doctor`) — now includes model ID validation, session history, and skills status
- Installs agents globally to `~/.opencode/agents/` (`--install-global`)
- **Uninstalls** global installation (`--uninstall`) — removes agents, sessions, skills, config interactively
- Supports explicit working root override (`--dir DIR`)
- **Path separation:** `SYSTEM_ROOT` (install location) ≠ `WORKING_ROOT` (active project — CWD or `--dir`). Runtime data (sessions, logs, skills, context.md) always uses `WORKING_ROOT`.
- **Session management:** `--sessions`, `--session <id>`, `--session-status`, `--summarize`
- **Skills management:** `--skills`, `--skills-search <query>`, `--skills-install <id>`, `--skills-remove <name>`
- **Version info:** `--version` — shows the current installed version
- **Update checking:** `--check-updates` — queries GitHub API for newer releases
- **Auto-update:** `--update` — downloads and applies the latest release automatically
- **LM Studio integration:** `--lmstudio-status`, `--install-lmstudio`, `--install-lmstudio-manual`, `--reset-go` — detect local models, assign roles, write global config

### `session_manager.py` — Session Bitacora

Manages session continuity:
- **`scan_logs()`** — Reads `.opencode/logs/` to extract errors, files changed, commands run
- **`save_session()`** — Saves session record as JSON in `.opencode/sessions/`
- **`inject_context()`** — Generates markdown context from recent sessions for `context.md`
- **`update_context_md()`** — Automatically updates `context.md` with session history
- Sessions are stored with: ID, timestamp, agent, summary, errors, pending tasks, files changed

### `skill_registry.py` — Skills Manager

Manages skills from the skills.sh ecosystem:
- **`search_skills(query)`** — Searches skills.sh for available skills
- **`install_skill(identifier)`** — Downloads skill from GitHub to `.opencode/skills/`
- **`inject_skills_context()`** — Generates markdown context from installed skills
- **`update_context_md()`** — Updates `context.md` with active skills

### `lmstudio_manager.py` — LM Studio Integration

Manages local model inference via LM Studio:
- **`check_lmstudio_running()`** — Checks if LM Studio server is accessible at `http://localhost:1234/v1/models`
- **`list_models()`** — Fetches available models from the OpenAI-compatible endpoint, sorts by parameter size, marks embedding models and code models
- **`auto_assign_roles()`** — Assigns largest model to orchestrator, 2nd to code-analyst, etc.; code models get a +0.5 boost for code-analyst
- **`safe_assign_roles()`** — Like `auto_assign_roles()` but detects known-broken models (e.g., Nemotron with broken Jinja2 template) and reassigns them to subagent, keeping stable models for orchestrator
- **`ensure_global_lmstudio_config()`** — Writes/updates the LM Studio provider in `~/.config/opencode/opencode.jsonc` with baseURL, npm package, assigned models, and per-model limits (context/output)
- **`format_agent_md()`** — Generates agent `.md` files with model ID `lmstudio/<model-name>`
- **`install_lmstudio_agents()`** — Backs up Go agents (both project and global), creates LM Studio agents in both locations, writes `plan.json`, calls `ensure_global_lmstudio_config()`
- **`_install_agents_to_dir()`** — Internal helper that backs up existing agents and writes new ones to a target directory (used for both project and global install)
- **`_restore_agents_from_backup()`** — Internal helper that restores agents from a backup directory
- **`_rmtree()`** — Cross-platform directory removal with Windows permission error handling
- **`reset_to_go()`** — Restores Go agents from backup in both project and global dirs, removes `plan.json`
- **`get_status()`** — Returns server status, model count, and model list

**Required:** LM Studio 0.4+ with API token authentication disabled in the Developer → Server panel.

### Hardware Tiers for LM Studio

oh-my-agents is designed to work on modest hardware. LM Studio can run models even on integrated GPUs, making local AI accessible without expensive hardware.

| Tier | Hardware | Max Model Size | Examples | Roles |
|------|----------|---------------|----------|-------|
| **Integrated** | Intel UHD/Iris, AMD Radeon integrated, no GPU | 1.5B - 3B Q4 | Qwen 2.5 Coder 1.5B, Ministral 3B, Phi-3 Mini 3.8B | Code review, simple tasks, chat |
| **Entry GPU** | GTX 1650/1660, RTX 2050/3050 (4-6GB) | 3B - 7B Q4 | Ministral 3B, Gemma 4 E2B, Qwen 2.5 7B | Orchestrator, validator, full agent suite |
| **Mid GPU** | RTX 2060/3060/4060 (6-12GB) | 7B - 14B Q4 | Qwen 2.5 7B, Mistral 7B, Llama 3.1 8B, DeepSeek Coder V2 Lite | Full 8-agent system, code generation |
| **High GPU** | RTX 3090/4090, A-series (24GB+) | 30B - 70B Q4 | Llama 3.3 70B, Qwen 2.5 72B, DeepSeek V3 | Heavy orchestration, complex analysis |

#### Recommended Models by Tier

**Integrated GPU / CPU-only (1.5B - 3B):**
| Model | Size | Why |
|-------|------|-----|
| Qwen 2.5 Coder 1.5B | 1.5B Q8 (1.5 GB) | Excellent code generation for its size |
| Ministral 3B Instruct | 3B Q4 (2.0 GB) | Best general-purpose for low-end HW |
| Phi-3 Mini 4K | 3.8B Q4 (2.5 GB) | Stable template, efficient |
| Gemma 4 E2B | 2.6B Q4 (3.2 GB) | Multilingual, good reasoning |

**Entry to Mid GPU — RTX 2060 / 3060 (6GB VRAM) (7B - 9B):**
| Model | Size | Why |
|-------|------|-----|
| Qwen 2.5 7B Instruct | 7B Q4 (4.5 GB) | Best quality/speed ratio on 6GB |
| Mistral 7B v0.3 | 7B Q4 (4.5 GB) | Reference model, very stable |
| Llama 3.1 8B Instruct | 8B Q4 (5.0 GB) | Strong general-purpose |
| DeepSeek Coder V2 Lite | 4B Q4 (3.0 GB) | Specialized for code |

#### Role Assignment Strategy

The `safe_assign_roles()` function optimizes model placement for limited hardware:

1. **Filters out** embedding models (no chat capability) and known-broken models
2. **Ranks by parameter size** with a +0.5 boost for code models (prefers them for code-analyst)
3. **Assigns in priority order**: orchestrator > code-analyst > validator > bulk-processor, etc.
4. **Duplicates models** if more roles than available LLMs (e.g., 3 LLMs for 8 roles → smaller model reused)
5. **Broken models** (e.g., Nemotron with bad Jinja2 template) go to subagent (least critical role)

Example with 4 LLMs + 1 embedding on a modest machine:
```
orchestrator  → Ministral 3.3B      (biggest stable model)
code-analyst  → Gemma 4 E2B         (2nd biggest, good reasoning)
validator     → Qwen Coder 1.5B     (fast, lightweight validation)
subagent      → Nemotron 4B         (broken template, least critical)
bulk-processor → Qwen Coder 1.5B   (reused — light async tasks)
```

### `cli/wizard.py` — Setup Wizard

Interactive wizard that proposes default configurations or guides the user through manual agent creation. Assigns `opencode-go/kimi-k2.6` to the orchestrator by default.

### `cli/ui.py` — User Interface

Visual components with `rich` for terminal: banners, agent tables, panels, and styled messages.

---

## ⚠️ Known Issue: Qwen Models (Reincorporated — v1.2.0)

The **Qwen3.6 Plus** and **Qwen3.5 Plus** models were previously removed from the available models list due to a false positive in the OpenCode registry.

> **Applied solution:** Reincorporated in v1.2.0. Verified available on [opencode.ai/es/go](https://opencode.ai/es/go) with credits: Qwen 3.6 Plus (3,300/5h), Qwen 3.5 Plus (10,200/5h). The original issue was a model ID format mismatch, not actual deprecation. Registry IDs: `opencode-go/qwen3.6-plus` and `opencode-go/qwen3.5-plus`.

---

## ⚠️ Known Issue: Nemotron Jinja2 Template (v1.7.2)

The **NVIDIA Nemotron 3 Nano 4B** GGUF model has a broken Jinja2 prompt template that causes the error:

> `Cannot apply filter "string" to type: NullValue`

This happens when OpenCode sends a chat completion request — the template applies a `| string` filter to a null message field, which Jinja2 cannot process.

**Solution:** `safe_assign_roles()` in `lmstudio_manager.py` detects Nemotron by its model ID and reassigns it to the `subagent` role (least critical). The orchestrator gets the next largest stable model (e.g., Ministral 3.3B). If you still want to use Nemotron as orchestrator, you can fix the template manually in LM Studio:

1. Open LM Studio → My Models
2. Select Nemotron 3 Nano 4B → Settings
3. Scroll to "Prompt Template" and paste a valid template (e.g., the one from lmstudio-community)
4. Save and reload

Alternatively, download a model with a known-good template from the [Recommended Models by Tier](#recommended-models-by-tier) table above.

---

## 📝 Changelog

### v1.7.2 — Global Agent Install, Nemotron Template Fix & Hardware Tiers (May 2026)

**Bug fix — `--install-lmstudio` only wrote project agents:**
- **Problem:** `install_lmstudio_agents()` only wrote LM Studio agents to the project's `.opencode/agents/`, but `opencode --agent orchestrator` resolves agents from `~/.opencode/agents/` (global directory). The orchestrator still loaded the Go plan model.
- **Solution:** Added `_install_agents_to_dir()` and `_restore_agents_from_backup()` helpers. `install_lmstudio_agents()` now writes agents to both project `.opencode/agents/` AND global `~/.opencode/agents/` (with backup of existing Go agents). `reset_to_go()` restores both locations.

**Bug fix — Nemotron broken Jinja2 template:**
- **Problem:** The Nemotron 3 Nano 4B model has a broken Jinja2 prompt template (`Cannot apply filter "string" to type: NullValue`), crashing every request sent to it.
- **Solution:** Added `safe_assign_roles()` that detects known-broken models by ID pattern and reassigns them to `subagent` (least critical role). Stable models are assigned to orchestrator first.

**New feature — Hardware tier documentation:**
- Added "Hardware Tiers for LM Studio" section with 4 tiers (Integrated, Entry GPU, Mid GPU, High GPU)
- Added "Recommended Models by Tier" tables with specific model recommendations per hardware level
- Added "Role Assignment Strategy" section explaining how `safe_assign_roles()` optimizes for limited hardware
- Documented model duplication when fewer LLMs than roles

**New files:**
- None

**Files modified:**
- `lmstudio_manager.py` — Added `safe_assign_roles()`, `_install_agents_to_dir()`, `_restore_agents_from_backup()`, `_rmtree()`, model limits in `ensure_global_lmstudio_config()`, `assignments` parameter in `install_lmstudio_agents()`
- `main.py` — Fixed Unicode arrow (`→` → `->`) for Windows cp1252 compatibility
- `tests/test_lmstudio.py` — 6 new tests for `safe_assign_roles()` (26 total)

**Tests:** 168 passing (26 LM Studio tests, 19 pre-existing failures on LM Studio-installed projects)

### v1.7.1 — LM Studio Auth Fix & Global Config (May 2026)

**Bug fix — LM Studio API token requirement:**
- **Problem:** LM Studio 0.4.12+ requires a Bearer token for all API endpoints (`invalid_api_key` error), and the `http-server-config.json` had no `apiToken` field.
- **Solution:** Documented that users must disable "Require API Token" in LM Studio Developer → Server panel. Updated `check_lmstudio_running()` and `list_models()` to use the OpenAI-compatible `/v1/models` endpoint instead of the removed `/api/v0/models`.
- `list_models()` now parses the v1 response format `{data: [{id, owned_by}]}` and infers parameters from model ID pattern.

**New feature — Global provider config:**
- Added `ensure_global_lmstudio_config()` to write/update LM Studio provider in `~/.config/opencode/opencode.jsonc` so OpenCode knows how to connect to the local server.
- Called automatically during `--install-lmstudio` after agents and `plan.json` are written.

**New files:**
- `tests/test_lmstudio.py` — 4 new tests for `ensure_global_lmstudio_config()` (creation, merge, update, empty list)

**Files modified:**
- `lmstudio_manager.py` — Added `ensure_global_lmstudio_config()` and `_get_global_config_path()`, rewrote `check_lmstudio_running()` and `list_models()` for v1 API, added `_model_id_to_display()` helper

**Tests:** 162 passing (19 pre-existing failures on LM Studio-installed projects where tests expect Go plan)

### v1.6.0 — Project Database & Auto-Session Continuity (May 2026)

**New features:**
- **ProjectDB (`project_db.py`):** SQLite database per project (`.opencode/project.db`) with tables for sessions, files_changed, errors, commands, and project_meta. Enables rich querying of session history and project state.
- **Auto-Session (`wrappers/opencode_logger.py`):** Automatic session saving when OpenCode exits. Enabled via `--auto-enable` flag. Sessions are auto-parsed from log output, saved to both SQLite and JSON backup, and `context.md` is auto-updated.
- **Continuity Manager (`continuity.py`):** Provides re-entry prompts, project health reports, pending task tracking, and status banners when returning to a project.
- **Project Hash:** Deterministic SHA-256 hash (12 chars) derived from project path for project identity across sessions.

**New CLI commands:**
| Command | Description |
|---------|-------------|
| `--auto-enable` | Enable automatic session saving for this project |
| `--auto-disable` | Disable automatic session saving |
| `--project-status` | Show project continuity status and session history |
| `--project-health` | Show project health report |
| `--continue` | Show re-entry context from last session |
| `--list-tasks` | List pending tasks from last session |
| `--complete-task <index>` | Mark a pending task as complete |

**New files:**
- `project_db.py` — SQLite project database manager (WAL mode, 5 tables, 5+ indexes)
- `continuity.py` — ContinuityManager for project re-entry experience
- `tests/test_project_db.py` — Comprehensive tests (20+ tests)

**Modified files:**
- `utils.py` — Added `get_project_db_path()`, `generate_project_hash()`, `get_current_git_branch()`, `get_current_git_diff_summary()`, `parse_openCode_log_content()`, `get_auto_session_flag_path()`, `is_auto_session_enabled()`
- `wrappers/opencode_logger.py` — Added `auto_save_session()` hook on process exit
- `session_manager.py` — Added `use_db` parameter and DB-backed operations
- `main.py` — Added 7 new CLI arguments and 7 handler functions, updated interactive menu with 5 new options

**Production usage:** The system is being used successfully in the RoadFlow project for session continuity and automatic state tracking across development sessions.

### v1.5.0 — MCP Integration & Auto-Skills (Feature Branch)

**New features:**
- **MCP Client:** `mcp_client.py` implements Model Context Protocol (JSON-RPC 2.0 over stdio)
- **MCP Config:** `mcp_config.py` manages `.opencode/mcp.json` with server templates
- **Auto-Skills:** `skill_recommender.py` analyzes your project and recommends relevant skills
- **Skills Catalog:** `skills_catalog.json` with 9 built-in skills (React, Django, FastAPI, Docker, etc.)
- **New CLI flags:** `--mcp-status`, `--mcp-add`, `--skills-recommend`, `--skills-auto`
- **Agent permissions:** `mcp: allow` for orchestrator and code-analyst

**New files:**
- `mcp_client.py`, `mcp_config.py` — MCP protocol implementation
- `skill_recommender.py`, `skills_catalog.json` — Auto-skill recommendation
- `tests/test_mcp.py` — MCP and recommender tests

**Note:** This is a feature branch (`feature/mcp-skills`). Test thoroughly before merging to main.

### v1.3.3 — Automatic Update System (April 2026)

**New features:**
- **Auto-updater:** `update_manager.py` queries GitHub releases, downloads, and applies updates
- **New CLI flags:** `--update`, `--check-updates`, `--version`
- **Data-safe updates:** Preserves `.git/`, `.opencode/sessions/`, `.opencode/skills/`, `.opencode/logs/`
- **Menu integration:** "Check for updates" in interactive menu

**New files:**
- `update_manager.py` — Update detection, download, and installation
- `VERSION` — Current version tracker

**Modified files:**
- `main.py` — Added `--update`, `--check-updates`, `--version`, menu option
- `setup.ps1` — Added `--update` handler
- `setup.sh` — Added `--update` handler

### v1.2.1 — Path Separation, Uninstall & 3-Level Agent Discovery (April 2026)

**Critical fix — SYSTEM_ROOT vs WORKING_ROOT separation:**
- **Problem:** Sessions, logs, skills, and `context.md` were saved to `SYSTEM_ROOT/.opencode/`, breaking continuity when the framework was run from a different working directory.
- **Fix:** Introduced `resolve_working_root()` and `find_agent_source()` in `utils.py`. All runtime data now uses `WORKING_ROOT` (the active CWD or `--dir` path), not `SYSTEM_ROOT`.
- Agent `.md` files are now discovered in 3 levels:
  1. `WORKING_ROOT/.opencode/agents/` (per-project override)
  2. `~/.opencode/agents/` (global installation)
  3. `SYSTEM_ROOT/.opencode/agents/` (bundled with repo)

**New command: `--uninstall`**
- Interactive removal of global installation (`~/.opencode/`)
- Removes agents, sessions, skills, and config individually
- Also cleans up the `oh-my-agents` wrapper from `~/.local/bin/` or `/usr/local/bin/` (Linux/Mac)
- Available via CLI flag, interactive menu, and setup scripts

**New files:**
- `utils.py` — Cross-platform path helpers (`resolve_working_root()`, `find_agent_source()`, `get_sessions_dir()`, `get_skills_dir()`, etc.)

**Files modified:**
- `main.py` — Added `--uninstall` flag, `run_uninstall()` function, `run_doctor()` now uses `working_root`
- `utils.py` — Added `SYSTEM_ROOT`, `resolve_working_root()`, `find_agent_source()`, `get_*_dir()` helpers
- `session_manager.py` — All operations now accept and use `project_root` parameter
- `skill_registry.py` — All operations now accept and use `project_root` parameter
- `cli/wizard.py` — Uses `working_root` from `main.py`
- `setup.sh` — Added `--uninstall` handler before launching `main.py`
- `setup.ps1` — Added `-Uninstall` handler before launching `main.py`
- `tests/` — Updated test counts to 66

### v1.2.0 — 8 Agents with Benchmark-Optimized Models (April 2026)

**Model swaps based on verified benchmarks:**
- Orchestrator: `MiMo V2.5 Pro` → **Kimi K2.6** (SWE-Bench Pro 58.6%, 3x usage credits on Go plan)
- Validator: `Kimi K2.6` → **MiMo V2.5 Pro** (94% math precision for rigorous verification)

**New agents:**
- **@frontend:** Qwen 3.6 Plus (SWE-Bench Verified 78.8%, 1M context, $0.325/M tokens). Added to all 7 plans.
- **@ml-specialist:** MiniMax M2.7 (MLE-Bench Lite 66.6%, 10B active parameters). Added to all 7 plans.

**Registry fix:**
- Reincorporated `opencode-go/qwen3.5-plus` and `opencode-go/qwen3.6-plus` to Go plan `all_available`
- Confirmed not deprecated — original issue #22644 was model ID format mismatch
- Verified available on [opencode.ai/es/go](https://opencode.ai/es/go)

**Files modified:**
- `plan_manager.py` — +2 models to registry, swap orch/val, +2 roles in all 7 plans
- `.opencode/agents/frontend.md` — New agent definition
- `.opencode/agents/ml-specialist.md` — New agent definition
- `cli/wizard.py` — 8 defaults with updated models
- `tests/test_wizard.py` — +4 tests (8 agents, frontend, ml-specialist, model swaps)
- `tests/test_plan_manager.py` — +2 model tests, swap asserts
- `.opencode/context.md` — Version 1.2.0, 8 agents with benchmarks

### v1.1.1 — Session Continuity & Skills (April 2026)

**New features:**
- **Session bitacora:** `session_manager.py` scans OpenCode logs, saves session records, and injects context for continuity between sessions
- **Skills system:** `skill_registry.py` downloads and manages skills from skills.sh ecosystem
- **@summarizer agent:** New lightweight agent (`opencode-go/minimax-m2.5`) for session analysis and project continuity
- **Global install automatic:** `setup.ps1` now installs agents globally by default — `opencode --agent orchestrator` works from any folder
- **Quick install:** `install.ps1` for fast setup on new machines

**New CLI commands:**
| Command | Description |
|---------|-------------|
| `--sessions` | List recorded sessions |
| `--session <id>` | Show details of a specific session |
| `--session-status` | Show summary of the last session |
| `--summarize` | Scan logs and save session record |
| `--skills` | List installed skills |
| `--skills-search <q>` | Search skills on skills.sh |
| `--skills-install <id>` | Install a skill from skills.sh |
| `--skills-remove <name>` | Remove an installed skill |

**New files:**
- `session_manager.py` — Session logging and continuity
- `skill_registry.py` — Skills download and management
- `utils.py` — Cross-platform helpers
- `install.ps1` — Quick installer for Windows
- `.opencode/agents/summarizer.md` — Summarizer agent definition

**Files modified:**
- `main.py` — 8 new CLI arguments, interactive menu updated
- `plan_manager.py` — Added `summarizer` role to all plans
- `cli/ui.py` — Session and skills UI components
- `cli/wizard.py` — Summarizer added to defaults
- `setup.ps1` — Global install now automatic
- `.opencode/context.md` — Session and skills documentation
- `requirements.txt` — Added `requests`
- `.gitignore` — Added `.opencode/sessions/`, `.opencode/skills/`

### v0.9.3.3 — Interactive Main Menu (April 2026)

**Problem:** Running `python main.py` without flags when agents were already configured would print the status table and exit immediately — no way to interact.

**Solution:** Added an interactive `questionary.select` menu that loops when configuration exists, offering:
- View agent status
- Run setup wizard (reconfigure)
- Run diagnostics (`--doctor`)
- Install globally (`--install-global`)
- Exit

CLI flags (`--setup`, `--doctor`, `--install-global`) still bypass the menu and work as direct commands. First-time (no config) still prompts to run the wizard.

**File modified:**
- `main.py` — Replaced linear flow with interactive menu loop in `main()`

### v0.9.3.2 — Global Install, Tests, Model Validation & CI (April 2026)

**Setup experience overhaul:** Global install is now the default. Agents work from ANY directory after setup — not just inside the project folder.

**Files modified:**
- `setup.ps1` — Global install prompts `[Yn]` (default yes) with clear explanation of why it matters
- `setup.sh` — Same improvement for Linux/Mac, renumbered steps to `[5/5]`
- `main.py` — Improved `install_global()` success message; `--doctor` now validates model IDs
- `plan_manager.py` — Added `validate_models()` method that checks agent models against the registry
- `README.md` — Updated Quick Start and global install docs with explanation of agent scope

**New files:**
- `tests/conftest.py` — Shared fixtures (temp_project, clean_env, mock_questionary)
- `tests/test_plan_manager.py` — 22 tests: plan detection, model mapping, validate_models()
- `tests/test_wizard.py` — 15 tests: init, defaults, permissions, save, format_md
- `tests/test_main.py` — 15 tests: load_agents, dependencies, install_global, doctor
- `.github/workflows/ci.yml` — CI pipeline: test matrix (Python 3.8–3.12) + ruff lint

**What `--doctor` now detects:**
- Invalid model IDs in agent `.md` files that don't match any known registry model
- Reports each mismatched agent and suggests re-running `--setup`

### v0.9.3.1 — Path Independence & Setup Fixes (April 2026)

**Critical fix:** All Python files now use `Path(__file__).parent` for path resolution instead of relative paths. The system works correctly regardless of the current working directory.

**Files modified:**
- `main.py` — Added `PROJECT_ROOT` constant, `--install-global`, `--dir` flags, `install_global()` function
- `cli/wizard.py` — Accepts `project_root` parameter, derives paths from script location (`Path(__file__).resolve().parent.parent`)
- `plan_manager.py` — Accepts `project_root` parameter for config file detection
- `setup.ps1` — Fixed ExecutionPolicy guidance, robust Python detection (`py -3` → `python3` → `python`), absolute paths, global install option
- `setup.sh` — Added `cd` to script directory, absolute paths, `--install-global` flag (checked before main.py runs)
- `README.md` — Documented new CLI args, global install section, ExecutionPolicy note, changelog entry

**New CLI arguments:**
| Argument | Description |
|----------|-------------|
| `--setup` | Force the setup wizard to reconfigure agents |
| `--doctor` | Diagnose environment issues (Python, deps, OpenCode CLI, agents) |
| `--install-global` | Copy agent `.md` files to `~/.opencode/agents/` for global use |
| `--dir DIR` | Override the auto-detected project root directory |

**How path resolution works now:**
- `PROJECT_ROOT = Path(__file__).parent.resolve()` in `main.py`
- `SetupWizard(project_root=...)` passes it to `PlanManager(project_root=...)`
- All `.opencode/agents/` references use `project_root / ".opencode" / "agents"` instead of `Path(".opencode/agents")`
- Scripts (`setup.ps1`, `setup.sh`) `cd` to their own directory before doing anything

### v0.9.2.3 — Full English Translation (April 2026)

Translated all documentation, comments, and user-facing strings from Spanish to English across the entire project for broader global reach.

**Files translated:**
- `.opencode/agents/*.md` — Agent descriptions and body text
- `.opencode/context.md` — Project context
- `agents.md` — Full documentation (278 lines)
- `plan_manager.py` — 14 comments and docstrings
- `main.py` — 31 comments, docstrings, and UI strings
- `cli/wizard.py` — 30 comments, prompts, and UI strings
- `cli/ui.py` — 7 UI labels and comments

**Note:** README.md was already in English.

### v0.9.2.1 — Subagent Model Fix + Multi-Plan Support (April 2026)

**Subagent model:** Changed from `opencode-go/mimo-v2.5-pro` to `opencode-go/glm-5.1` to eliminate duplication with the orchestrator.

**New plans supported in PlanManager:**
- `openrouter` — Configurable models via OPENROUTER_API_KEY
- `copilot` — GitHub Copilot models
- `ollama` — Self-hosted local models

**Documentation fixes:**
- AGENTS.md: Orchestrator permissions corrected to `read + task` (not edit/bash)
- AGENTS.md: Removed contradictory note about permission rollback
- AGENTS.md: GLM-5.1 references updated to mimo-v2.5-pro
- README.md: Subagent model updated

**Final models (no duplicates):**

| Agent | Model |
|--------|--------|
| @orchestrator | `opencode-go/mimo-v2.5-pro` |
| @code-analyst | `opencode-go/deepseek-v4-pro` |
| @validator | `opencode-go/kimi-k2.6` |
| @bulk-processor | `opencode-go/deepseek-v4-flash` |
| @subagent | `opencode-go/glm-5.1` |

---

### v0.9.2.0 — Rebrand to oh-my-agents (April 2026)

**New identity:** The project has been renamed from `multi-agentes-opencode` to `oh-my-agents` for better memorability, discoverability, and alignment with trending GitHub naming patterns.

- Renamed repository to `oh-my-agents`
- Updated all documentation and references
- Explicit OpenCode branding throughout
- Banner updated with VisualIA Consulting credit and MIT license

---

### v0.9.1.0 — Base Project Sync (April 2026)

**Critical model fix:** The `.opencode/agents/*.md` files were using display names (`GLM-5.1`, `DeepSeek V4 Pro`) instead of registry IDs (`opencode-go/mimo-v2.5-pro`, `opencode-go/deepseek-v4-pro`), causing `ProviderModelNotFoundError`.

| File | Before (broken) | After (correct) |
|---------|--------------|---------------------|
| `orchestrator.md` | `model: GLM-5.1` | `model: opencode-go/mimo-v2.5-pro` |
| `code-analyst.md` | `model: DeepSeek V4 Pro` | `model: opencode-go/deepseek-v4-pro` |
| `validator.md` | `model: Kimi K2.6` | `model: opencode-go/kimi-k2.6` |
| `bulk-processor.md` | `model: DeepSeek V4 Flash` | `model: opencode-go/deepseek-v4-flash` |
| `subagent.md` | `model: MiMo-V2.5-Pro` | `model: opencode-go/glm-5.1` |

**Additional changes:**
- Removed `opencode.jsonc` — caused conflicts; the base project doesn't use it
- Orchestrator model changed from `glm-5.1` to `mimo-v2.5-pro` (consistent with base project)
- Orchestrator permissions: `edit: deny`, `bash: deny`, `read: allow`, `task: allow`
- Updated documentation (`AGENTS.md`, `README.md`, `context.md`)

---

### v0.9.0.0 — Permission Audit (April 2026)

**Agent permission audit:** Verified that each agent has exactly the permissions that correspond to its role, removing excessive privileges that allowed write/execute where not appropriate.

| Agent | Change | Before | After |
|--------|--------|-------|---------|
| **@orchestrator** | `edit` | ✅ allow | ❌ deny |
| **@orchestrator** | `bash` | ✅ allow | ❌ deny |
| **@validator** | `edit` | ✅ allow | ❌ deny |
| **@validator** | `bash` | ✅ allow | ❌ deny |

**Final verified permissions:**

| Agent | edit | bash | read | task | Mode |
|--------|:----:|:----:|:----:|:----:|------|
| **@orchestrator** | ❌ deny | ❌ deny | ✅ allow | ✅ allow | Coordination — delegates to sub-agents |
| **@code-analyst** | ✅ allow | ✅ allow | ✅ allow | ❌ deny | Execution — writes and executes |
| **@validator** | ❌ deny | ❌ deny | ✅ allow | ❌ deny | Read Only — reviews and reports only |
| **@bulk-processor** | ✅ allow | ✅ allow | ✅ allow | ❌ deny | Execution — bulk processing |
| **@subagent** | ✅ allow | ✅ allow | ✅ allow | ❌ deny | Execution — debugging and fallback |

**Updated role descriptions:**
- **Orchestrator**: Now explicitly states *"You do NOT write code or execute commands directly — you delegate all implementation to sub-agents"*
- **Validator**: Now explicitly states *"You do NOT write or execute code. You only read and report findings"*

**Modified files:**
- `.opencode/agents/orchestrator.md` — permissions and description
- `.opencode/agents/validator.md` — permissions and description
- `AGENTS.md` — permission tables and fixes
- `README.md` — permission table

---

### v0.8.0 — Registry IDs and Fixes (April 2026)

- Fix: Model IDs changed from display names to registry IDs (`opencode-go/*`)
- Fix: Personal path removed from README
- Fix: `plan_manager.py` updated with registry IDs for all plans
- Fix: `_detect_plan()` fallback corrected from `api` to `go`
- Fix: Bare `except` → `(json.JSONDecodeError, OSError)`
- Add: `subagent.md`, `main.py`, `cli/` to the repository

---

## 🐛 Recent Fixes Applied (April 2026)

| # | Problem | File | Solution |
|---|----------|---------|----------|
| 1 | Inconsistent orchestrator: `plan_manager.py` pointed to `Qwen3.6 Plus` | `plan_manager.py` | Changed to `opencode-go/mimo-v2.5-pro` |
| 2 | Validator had edit/bash permissions despite being "Read Only" | `validator.md` | `edit: deny`, `bash: deny` |
| 3 | `_detect_plan()` returned `"api"` if `OPENCODE_API_KEY` existed | `plan_manager.py` | Removed from check; only `ANTHROPIC_API_KEY` → api |
| 4 | Bare `except` silenced all exceptions when reading JSON | `plan_manager.py` | Specified `(json.JSONDecodeError, OSError)` |
| 5 | Placeholder comments in `main.py` | `main.py` | Replaced with docstrings |
| 6 | Wizard proposed `Qwen3.6 Plus` as orchestrator | `cli/wizard.py` | Changed to `opencode-go/mimo-v2.5-pro` |
| 7 | Agents used display names instead of registry IDs | `*.md`, `plan_manager.py` | Changed to IDs `opencode-go/*` |
| 8 | Orchestrator had `edit/bash: allow` despite being plan mode | `orchestrator.md` | Changed to `deny` — only `read + task` |
| 9 | Validator had `edit/bash: allow` despite being "Read Only" | `validator.md` | Changed to `deny` |
| 10 | `opencode.jsonc` caused configuration conflicts | `opencode.jsonc` | Removed |
| 11 | Orchestrator model inconsistent with base project | `orchestrator.md` | Changed to `opencode-go/mimo-v2.5-pro` |
| 12 | All Python files used relative paths (`Path(".opencode/...")`) — broke when CWD ≠ project root | `main.py`, `wizard.py`, `plan_manager.py` | Changed to `Path(__file__).parent`-based resolution |
| 13 | `setup.ps1` had no ExecutionPolicy guidance, no `cd` to script dir, only tried `python` | `setup.ps1` | Added `Set-Location $ScriptDir`, `Find-Python` function, ExecutionPolicy comments |
| 14 | `setup.sh` had no `cd` to script dir, `--install-global` flag checked after `main.py` ran | `setup.sh` | Added `cd "$SCRIPT_DIR"`, moved flag check before `main.py` |
| 15 | Sessions/skills/logs saved to SYSTEM_ROOT instead of WORKING_ROOT — broke continuity across projects | `main.py`, `session_manager.py`, `skill_registry.py`, `utils.py` (new) | Introduced `SYSTEM_ROOT` vs `WORKING_ROOT` separation. `find_agent_source()` for 3-level agent discovery. All runtime data now bound to active project. |
| 16 | LM Studio `invalid_api_key` — auth token required by LM Studio 0.4.12+, v0 API endpoints removed | `lmstudio_manager.py` | Switched to OpenAI-compatible `/v1/models` endpoint. Documented disabling "Require API Token" in LM Studio Developer panel. |
| 17 | LM Studio agents only installed to project dir — `opencode --agent orchestrator` still used Go plan | `lmstudio_manager.py` | Added `_install_agents_to_dir()` to write agents to both project `.opencode/agents/` and global `~/.opencode/agents/`. `reset_to_go()` restores both. |
| 18 | Nemotron 3 Nano 4B Jinja2 template crashes every request (`Cannot apply filter "string" to type: NullValue`) | `lmstudio_manager.py` | Added `safe_assign_roles()` that detects broken models and reassigns them to `subagent`, keeping stable models for orchestrator. |

---

## 📁 File Structure

```
./
├── AGENTS.md                    # This document (agent status)
├── README.md                    # Main project documentation
├── plan_manager.py              # Model selection logic + model validation
├── main.py                      # Multi-agent system CLI
├── session_manager.py           # Session logging and continuity
├── skill_registry.py            # Skills download and management
├── project_db.py                # SQLite project database manager
├── continuity.py                # Project continuity manager
├── mcp_client.py                # MCP protocol client (JSON-RPC 2.0 over stdio)
├── mcp_config.py                # MCP configuration manager
├── skill_recommender.py         # Auto-skill recommendation engine
├── skills_catalog.json          # Built-in skills catalog (9 skills)
├── update_manager.py            # Automatic update system
├── lmstudio_manager.py          # LM Studio integration (detection, role assignment, global config)
├── VERSION                      # Current version tracker
├── utils.py                     # Cross-platform helpers
├── requirements.txt             # Python dependencies (now includes requests)
├── setup.ps1                    # Windows setup script (global install by default)
├── setup.sh                     # Linux/Mac setup script (global install by default)
├── install.ps1                  # Quick installer for Windows
├── cli/
│   ├── __init__.py
│   ├── wizard.py                # Interactive setup wizard
│   └── ui.py                    # Visual components (rich)
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures
│   ├── test_plan_manager.py     # 29 tests: plans, models, validation
│   ├── test_wizard.py           # 22 tests: defaults, permissions, save
│   ├── test_main.py             # 15 tests: agents, deps, global install, uninstall
│   ├── test_update_manager.py   # 10 tests: version, updates, merge
│   ├── test_lmstudio.py         # 26 tests: LM Studio detection, role assignment, global config, safe_assign
│   ├── test_mcp.py              # 10 tests: MCP config, client, recommender
│   └── test_project_db.py       # 20+ tests: project database, continuity
├── .github/
│   └── workflows/
│       └── ci.yml               # CI pipeline (test matrix + lint)
└── .opencode/
    ├── context.md               # Global context injected to all agents
    └── agents/
        ├── orchestrator.md      # Main coordinator
        ├── code-analyst.md      # Senior software engineer
        ├── validator.md         # QA and code validation
        ├── bulk-processor.md    # Bulk processing (hidden)
        ├── subagent.md          # Debugger / fallback agent
        ├── summarizer.md        # Session summarizer
        ├── frontend.md          # Frontend specialist
        └── ml-specialist.md     # ML and data pipeline specialist
```

---

## 🔧 PlanManager Usage

```python
from plan_manager import PlanManager

pm = PlanManager()
print(f"Plan detected: {pm.plan}")
print(f"Orchestrator model: {pm.get_model('orchestrator')}")
print(f"Available models: {pm.get_available_models()}")
```

### Supported Plans

| Plan | Detection Method | Orchestrator Model |
|------|---------------------|--------------------|
| **Go** (default) | Default or `OPENCODE_PLAN=go` | `opencode-go/deepseek-v4-pro` |
| **Zen** | `GITHUB_TOKEN` or `COPILOT_TOKEN` | `opencode/claude-sonnet-4.5` |
| **API** | `ANTHROPIC_API_KEY` | `anthropic/claude-sonnet-4` (configurable) |
| **Enterprise** | `OPENCODE_PLAN=enterprise` | `opencode-go/deepseek-v4-pro` (configurable) |
| **OpenRouter** | `OPENROUTER_API_KEY` | `openrouter/deepseek/deepseek-v3` (configurable) |
| **Copilot** | Active GitHub Copilot | `copilot/claude-sonnet-4` |
| **Ollama** | `OLLAMA_HOST` or Ollama running | `ollama/llama3.3:70b` (configurable) |

---

## 🚀 Suggested Next Steps

1. **Run tests locally:** `pytest tests/ -v` (168 tests, all current features covered)
2. **Connectivity Validation:** Run `python main.py` to verify that the PlanManager correctly detects the environment
3. **Delegation Tests:** Use `opencode --agent orchestrator` with a complex task to validate interaction between agents (works from any folder after global install)
4. **Model Health Check:** Run `python main.py --doctor` to verify all agent model IDs are valid
5. **Session Continuity:** Run `python main.py --summarize` after an OpenCode session to save the session record
6. **Skills Exploration:** Run `python main.py --skills-search database` to find relevant skills for your project
7. **Uninstall Test:** Run `python main.py --uninstall` to verify the interactive removal workflow works correctly (reinstall with `python main.py --install-global`)
8. **Update test:** Run `python main.py --check-updates` to verify the update system can reach GitHub
9. **Test project DB:** Run `python main.py --project-status` to verify project continuity features
10. **Enable auto-session:** Run `python main.py --auto-enable` to enable automatic session saving
11. **View continuity:** Run `python main.py --continue` to see re-entry context
12. **Enable auto-session:** Run `python main.py --auto-enable` to enable automatic session saving
13. **LM Studio test:** Run `python main.py --lmstudio-status` to verify local model detection
14. **LM Studio install:** Run `python main.py --install-lmstudio` to switch to local models
15. **LM Studio hardware check:** Run `python main.py --lmstudio-status` to see which tier your setup fits

---

## 🔗 Links

- **Repository**: [visualiaconsulting/oh-my-agents](https://github.com/visualiaconsulting/oh-my-agents)
- **Organization**: [VisualIA Consulting](https://github.com/visualiaconsulting)
- **License**: MIT
