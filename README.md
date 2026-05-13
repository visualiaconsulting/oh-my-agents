<div align="center">

# 🤖 oh-my-agents

### The multi-agent orchestration framework for [OpenCode](https://opencode.ai)

[![OpenCode](https://img.shields.io/badge/Built_for-OpenCode_Go-00D4AA?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyTDIgN2wxMCA1IDEwLTVNMiAxN2wxMCA1IDEwLTVNMiAxMmwxMCA1IDEwLTUiLz48L3N2Zz4=)](https://opencode.ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-1.6.0-blue?style=for-the-badge)](https://github.com/visualiaconsulting/oh-my-agents/releases/tag/v1.6.0)
[![GitHub Stars](https://img.shields.io/github/stars/visualiaconsulting/oh-my-agents?style=for-the-badge&logo=github)](https://github.com/visualiaconsulting/oh-my-agents/stargazers)
[![GitHub Issues](https://img.shields.io/github/issues/visualiaconsulting/oh-my-agents?style=for-the-badge&logo=github)](https://github.com/visualiaconsulting/oh-my-agents/issues)

**Stop writing boilerplate. Start shipping with an AI workforce.**

*oh-my-agents* gives you a production-ready **orchestrator-specialists architecture** for [OpenCode](https://opencode.ai). One orchestrator analyzes your tasks, breaks them down, and delegates to specialized sub-agents — each with the right model and permissions for the job.

[Quick Start](#-quick-start) · [Agents](#-agents) · [Session Management](#-session-management) · [Skills System](#-skills-system) · [Examples](#-examples) · [Configuration](#%EF%B8%8F-planmanager) · [Contributing](#-contributing)

---

</div>

## ✨ Why oh-my-agents?

| Feature | Description |
|---------|-------------|
| 🧠 **Smart Orchestration** | The orchestrator analyzes complex tasks, decomposes them, and delegates to the right specialist |
| 🎯 **Specialist Agents** | Each agent has a focused role: coding, QA validation, data processing, debugging, session analysis |
| 🔐 **Least-Privilege Permissions** | Validator is read-only. Orchestrator only delegates. Code-analyst writes and executes. |
| 📝 **Session Continuity** | Never lose context between sessions. Automatic bitacora saves errors, changes, and pending tasks |
| 🧩 **Skills Ecosystem** | Extend agent capabilities with reusable skills from [skills.sh](https://skills.sh) |
| 🔄 **Multi-Plan Support** | Works with OpenCode Go, Zen, API, Enterprise, OpenRouter, Copilot, and Ollama via `PlanManager` |
| 🚀 **Zero Config Start** | Clone, run setup, start coding. The wizard handles the rest |
| 📦 **Portable** | Copy agents to any project — they adapt via `context.md` |
| 🗄️ **Project Database** | SQLite DB per project stores sessions, file changes, errors, commands (v1.6.0) |
| 🔄 **Auto-Session** | Sessions auto-saved when OpenCode exits — enable with `--auto-enable` (v1.6.0) |

---

### 🔄 Project Continuity & Auto-Session (v1.6.0)

oh-my-agents now automatically tracks your project state across sessions:

| Feature | Description |
|---------|-------------|
| **Project Database** | SQLite DB per project stores sessions, file changes, errors, commands |
| **Auto-Session** | Sessions auto-saved when OpenCode exits (enable with `--auto-enable`) |
| **Continuity** | Re-entry prompts show pending tasks, recent changes, project health |
| **Task Tracking** | Track and mark pending tasks across sessions |

**Quick Start:**
```bash
# Enable auto-session saving
python main.py --auto-enable

# After an OpenCode session, check project status
python main.py --project-status

# View re-entry context from last session
python main.py --continue

# Check project health
python main.py --project-health
```

**How it works:**
1. `opencode-logger` wrapper captures all OpenCode output to `.opencode/logs/`
2. On exit, the wrapper auto-parses the log and saves to `.opencode/project.db`
3. When you return to the project, `--continue` shows what was happening
4. Pending tasks, errors, and file changes are tracked across sessions

---

## 🤖 Agents

| Agent | Model (Go Plan) | Role | Permissions |
|-------|:----------------:|------|:-----------:|
| **@orchestrator** | `kimi-k2.6` | 🎼 Coordinator — decomposes tasks, delegates to specialists | `read` `task` |
| **@code-analyst** | `deepseek-v4-pro` | 💻 Senior Engineer — writes clean code, implements features | `edit` `bash` `read` |
| **@validator** | `mimo-v2.5-pro` | 🔍 QA Specialist — validates quality, edge cases, precision | `read` only |
| **@bulk-processor** | `deepseek-v4-flash` | ⚡ Data Processor — handles repetitive, high-volume tasks (hidden) | `edit` `bash` `read` |
| **@subagent** | `glm-5.1` | 🛠️ Debugger — auxiliary tasks and fallback agent | `edit` `bash` `read` |
| **@summarizer** | `minimax-m2.5` | 📊 Session Analyst — summarizes sessions, analyzes project state | `edit` `bash` `read` |
| **@frontend** | `qwen3.6-plus` | 🎨 UI Specialist — React, TypeScript, Tailwind, rapid iteration | `edit` `bash` `read` |
| **@ml-specialist** | `minimax-m2.7` | 🧪 ML Engineer — training, inference, data pipelines, MLOps | `edit` `bash` `read` |

> **Model selection:** Each model is chosen by benchmark performance — Kimi K2.6 leads SWE-Bench Pro (58.6%), DeepSeek V4 Pro leads GPQA Diamond (90.1%), MiMo V2.5 Pro has 94% math precision, Qwen 3.6 Plus ($0.325/M tokens) is optimal for iterative UI work, MiniMax M2.7 leads MLE-Bench Lite (66.6%).

> **How it works:** You give a task to `@orchestrator`. It analyzes, plans, and delegates to the right specialist(s). The validator checks quality before returning results. After the session, `@summarizer` can analyze logs and save a continuity record.

---

## 🚀 Quick Start

### Prerequisites

- [OpenCode CLI](https://opencode.ai) installed
- Active **OpenCode Go** subscription (or any supported plan)
- API key configured via `/connect` or environment variable

### Option A: Full Setup (recommended for first time)

```bash
# 1. Clone the repository
git clone https://github.com/visualiaconsulting/oh-my-agents.git
cd oh-my-agents

# 2. Run setup (installs deps, configures agents, installs globally)
.\setup.ps1        # Windows
# or
./setup.sh         # Linux/Mac

# 3. Start the orchestrator
opencode --agent orchestrator
```

> **Windows note:** If you get an execution policy error, run:
> `powershell -ExecutionPolicy Bypass -File setup.ps1`

### Option B: Quick Install (for new machines)

```bash
git clone https://github.com/visualiaconsulting/oh-my-agents.git
cd oh-my-agents
.\install.ps1      # Windows only
```

This installs dependencies and agents globally in one step — no interactive wizard.

### Option C: Clone & Go (use agents in another project)

```bash
# Copy agents to your project
cp -r .opencode/agents/ myproject/.opencode/agents/

# Create a context.md for your project
cat > myproject/.opencode/context.md << 'EOF'
---
project: My Project
plan: go
version: 1.0
---
Describe your project context here...
EOF

# Run from your project
cd myproject
opencode --agent orchestrator
```

### Install Globally

To make agents available from **any directory** (not just the cloned repo):

```bash
# From the oh-my-agents directory:
python main.py --install-global
```

This copies agent definitions to `~/.opencode/agents/`, which OpenCode reads automatically. The setup script does this automatically in step 5.

> **💡 Tip:** After installing globally, run `python main.py --check-updates` periodically to ensure you have the latest version with the newest features and fixes.

### 🧭 Path Resolution — SYSTEM_ROOT vs WORKING_ROOT

oh-my-agents now separates two important concepts:

| Concept | Path | Description |
|---------|------|-------------|
| **SYSTEM_ROOT** | `oh-my-agents/` (the cloned repo) | Where the framework code lives |
| **WORKING_ROOT** | Your `cwd` (current project) | Where your project lives |

**Behavior:**
- **Sessions, logs, skills, and `context.md`** are always read/written relative to **WORKING_ROOT** (your active project). This ensures continuity even when the framework is installed globally.
- **Agent `.md` files** are detected in 3 levels (first match wins):
  1. `WORKING_ROOT/.opencode/agents/` — per-project override
  2. `~/.opencode/agents/` — global installation
  3. `SYSTEM_ROOT/.opencode/agents/` — agents bundled in the repo
- Use `--dir DIR` to explicitly set the **WORKING_ROOT** when running `main.py` from a different directory.

> **Before v1.2.1 (bug):** Sessions and skills were saved to `SYSTEM_ROOT/.opencode/`, breaking continuity when switching projects.

---

## 📝 Session Management

### What is it?

Session management ensures you **never lose context** between OpenCode sessions. When you work on a project, close OpenCode, and come back later, the system remembers:

- What was accomplished in the last session
- Errors that occurred and how they were handled
- Files that were modified
- Pending tasks that need attention
- Decisions made during the session

### How it works

```
OpenCode Session → .opencode/logs/ → session_manager.py → .opencode/sessions/ → context.md
                                                                    ↓
                                                          Next session reads
                                                          context.md for continuity
```

1. **During your session:** OpenCode writes logs to `.opencode/logs/`
2. **After your session:** Run `python main.py --summarize` to scan those logs
3. **The system:** Extracts errors, file changes, commands run, and saves a JSON record
4. **Context injection:** The last 3 sessions are automatically injected into `context.md`
5. **Next session:** The orchestrator reads `context.md` and knows exactly where you left off

### Commands

| Command | Description |
|---------|-------------|
| `python main.py --summarize` | Scan logs and save the current session record |
| `python main.py --sessions` | List all recorded sessions in a table |
| `python main.py --session-status` | Show a detailed summary of the last session |
| `python main.py --session <id>` | Show details of a specific session by ID |

> **📍 Storage location:** Session records are always saved to `WORKING_ROOT/.opencode/sessions/` — your active project directory. This means you can have the framework installed globally while maintaining separate session histories per project.

### Example workflow

```bash
# After finishing work in OpenCode:
python main.py --summarize

# Output:
# ✔ Session saved: a3f8b2c1
#   Files changed: 12
#   Errors found: 2
#   Context updated in .opencode/context.md

# Later, check what was done:
python main.py --session-status

# Output:
# === Last Session ===
# Session: a3f8b2c1
# Time:    2026-04-29 14:32:00
# Agent:   @summarizer
#
# Summary: Auto-summarized session. 12 files changed, 2 errors found.
#
# Errors (2):
#   • TypeError: cannot read property 'x' of undefined
#   • Failed to compile src/components/Header.tsx
#
# Files Changed (12):
#   • src/components/Header.tsx
#   • src/utils/api.ts
#   • ...
```

### Session data format

Each session is saved as JSON in `.opencode/sessions/<id>.json`:

```json
{
  "session_id": "a3f8b2c1",
  "timestamp": "2026-04-29 14:32:00",
  "agent": "summarizer",
  "summary": "Auto-summarized session...",
  "errors": ["TypeError: ..."],
  "pending_tasks": ["Fix header responsive layout"],
  "files_changed": ["src/components/Header.tsx"],
  "commands_run": ["npm run build"],
  "warnings": ["Deprecated API usage"]
}
```

### @summarizer agent

The `@summarizer` is a lightweight agent (`opencode-go/minimax-m2.5`) designed for session analysis. When delegated by the orchestrator at the end of a session, it:

1. Reads the session logs
2. Identifies key accomplishments and errors
3. Notes pending tasks
4. Writes the session summary
5. Suggests improvements to `agents.md` if relevant
6. Can download skills from skills.sh if requested

---

## 🔄 Automatic Updates

oh-my-agents can update itself automatically from GitHub releases.

### Check for updates
```bash
python main.py --check-updates
```

### Update to latest version
```bash
python main.py --update
```

The updater will:
1. Query the GitHub API for the latest release
2. Download the release archive
3. Preserve your sessions, skills, logs, and `.git` history
4. Overwrite framework files with the new version
5. Update the `VERSION` file

You can also update via setup scripts:
```bash
./setup.sh --update
powershell -File setup.ps1 --update
```

### Update via menu
Run `python main.py` and select **"Check for updates"** from the interactive menu.

---

## 🧩 Skills System

### What are skills?

Skills are **reusable capabilities** for AI agents. They provide procedural knowledge, best practices, and domain-specific guidance that agents can reference during their work.

The skills ecosystem is managed by [skills.sh](https://skills.sh). Browse available skills at [skills.sh](https://skills.sh) and read the documentation at [skills.sh/docs](https://skills.sh/docs).

### How it works

```
skills.sh (registry) → skill_registry.py → .opencode/skills/ → context.md → Agents
```

1. **Search:** Find skills on skills.sh by topic
2. **Install:** Download the skill's `.md` file from GitHub to `.opencode/skills/`
3. **Inject:** The skill content is automatically added to `context.md`
4. **Use:** All agents see the skill as part of their context and can reference it

### Commands

| Command | Description |
|---------|-------------|
| `python main.py --skills` | List all installed skills |
| `python main.py --skills-search <query>` | Search skills.sh for available skills |
| `python main.py --skills-install <owner/repo/name>` | Install a skill from skills.sh |
| `python main.py --skills-remove <name>` | Remove an installed skill |

### Example: Installing a database skill

```bash
# 1. Search for database-related skills
python main.py --skills-search database

# Output:
# Skills Search: 'database'
# #  Name                         Repo
# 1  neon-postgres                neondatabase/agent-skills
# 2  prisma-database-setup        prisma/skills
# 3  postgres                     planetscale/database-skills
# 4  database-migration           wshobson/agents
# ...
# Install with: python main.py --skills-install owner/repo/name

# 2. Install the Neon Postgres skill
python main.py --skills-install neondatabase/agent-skills/neon-postgres

# Output:
# ✔ Skill 'neon-postgres' installed to .opencode/skills/

# 3. Verify installation
python main.py --skills

# Output:
# Installed Skills
# Name           Description              Source
# neon-postgres  Best practices for Neon  neondatabase/agent-skills
```

### Skill file format

Skills are markdown files with a YAML header:

```markdown
---
name: neon-postgres
description: Best practices for Neon Postgres
source: neondatabase/agent-skills
---

# Neon Postgres Best Practices

When working with Neon Postgres:

1. **Connection pooling:** Always use PgBouncer or the built-in pooler
2. **Read replicas:** Enable for read-heavy workloads
3. **Branching:** Use database branching for safe schema changes
4. **Migrations:** Run migrations during low-traffic periods

## Connection String Format

postgresql://user:password@host:port/database?sslmode=require

## Common Pitfalls

- Don't exceed connection limits on free tier
- Branch resets after 30 days of inactivity
```

### How skills are injected

When a skill is installed, its content is appended to `context.md` under the `## Active Skills` section. Every agent that reads `context.md` (which is all of them) automatically has access to the skill's knowledge.

```markdown
# context.md
---
project: my-app
plan: go
version: 1.0
---

## Active Skills

### Skill: neon-postgres

*Best practices for Neon Postgres*

# Neon Postgres Best Practices
...
```

### Removing a skill

```bash
python main.py --skills-remove neon-postgres
```

This deletes the `.md` file from `.opencode/skills/`. The next `--summarize` run will update `context.md` to remove the skill reference.

---

## 💡 Examples

### Training a YOLO model

```
> complete the training of YOLO26n to 25 epochs with MuSGD and GPU 0
```

The orchestrator:
1. Asks `@code-analyst` to prepare/complete the training script
2. Asks `@validator` to verify parameters are correct
3. Executes the consolidated command

### Analyzing results

```
> review the results of the last training and compare with previous ones
```

The orchestrator:
1. Reads CSV/results.csv
2. Asks `@code-analyst` to extract metrics
3. Asks `@validator` to verify targets are met
4. Returns a comparative summary

### Multi-step task

```
> refactor the data pipeline to use async processing, add error handling, and write tests
```

The orchestrator:
1. Asks `@code-analyst` to refactor with async patterns
2. Asks `@validator` to review the refactored code
3. Asks `@code-analyst` to add error handling and tests
4. Asks `@validator` to run and validate tests
5. Returns consolidated results

### Session continuity workflow

```bash
# Day 1: Work on a feature
opencode --agent orchestrator
# ... work for 2 hours ...
# Exit OpenCode

# Save the session
python main.py --summarize

# Day 2: Resume work
opencode --agent orchestrator
# The orchestrator reads context.md and knows:
# - What was done yesterday
# - What errors occurred
# - What is still pending
```

---

## ⚙️ PlanManager

The `PlanManager` automatically detects your active OpenCode plan and selects the optimal models for each agent role.

```python
from plan_manager import PlanManager

pm = PlanManager()
print(f"Plan detected: {pm.plan}")
print(f"Orchestrator model: {pm.get_model('orchestrator')}")
print(f"Available models: {pm.get_available_models()}")
```

### Supported Plans

| Plan | Detection Method | Orchestrator Model |
|------|------------------|-------------------|
| **Go** (default) | Default or `OPENCODE_PLAN=go` | `opencode-go/kimi-k2.6` |
| **Zen** | `GITHUB_TOKEN` or `COPILOT_TOKEN` | `opencode/claude-sonnet-4.5` |
| **API** | `ANTHROPIC_API_KEY` | `anthropic/claude-sonnet-4` (configurable) |
| **Enterprise** | `OPENCODE_PLAN=enterprise` | `opencode-go/kimi-k2.6` (configurable) |
| **OpenRouter** | `OPENROUTER_API_KEY` | `openrouter/anthropic/claude-sonnet-4.5` (configurable) |
| **Copilot** | Active GitHub Copilot | `copilot/claude-sonnet-4` |
| **Ollama** | `OLLAMA_HOST` or Ollama running | `ollama/llama3.3:70b` (configurable) |

---

## 📁 Project Structure

```
oh-my-agents/
├── README.md                    # This file
├── AGENTS.md                    # Detailed agent state & changelog
├── plan_manager.py              # Model selection logic per plan
├── main.py                      # CLI for the multi-agent system
├── session_manager.py           # Session logging and continuity
├── skill_registry.py            # Skills download and management
├── utils.py                     # Cross-platform helpers
├── requirements.txt             # Python dependencies
├── setup.ps1                    # Windows setup script
├── setup.sh                     # Linux/Mac setup script
├── install.ps1                  # Quick installer for Windows
├── cli/
│   ├── wizard.py                # Interactive configuration wizard
│   └── ui.py                    # Rich terminal UI components
├── tests/
│   ├── conftest.py              # Shared fixtures
│   ├── test_plan_manager.py     # 22 tests
│   ├── test_wizard.py           # 17 tests
│   └── test_main.py             # 15 tests
└── .opencode/
    ├── context.md               # Global context injected to all agents
    ├── sessions/                # Session records (gitignored)
    ├── skills/                  # Installed skills (gitignored)
    └── agents/
        ├── orchestrator.md      # Main coordinator
        ├── code-analyst.md      # Senior software engineer
        ├── validator.md         # QA and code validation
        ├── bulk-processor.md    # High-volume data processing (hidden)
        ├── subagent.md          # Debugger / fallback agent
        ├── summarizer.md        # Session summarizer
        ├── frontend.md          # Frontend specialist
        └── ml-specialist.md     # ML and data pipeline specialist
```

### CLI Arguments

| Argument | Description |
|----------|-------------|
| `--setup` | Force the setup wizard to reconfigure agents |
| `--doctor` | Diagnose environment issues (Python, deps, OpenCode CLI, agents, sessions, skills) |
| `--install-global` | Copy agent `.md` files to `~/.opencode/agents/` for global use |
| `--uninstall` | Remove global installation (agents, sessions, skills, config). Available via interactive menu or setup scripts |
| `--dir DIR` | Override the auto-detected project root directory (WORKING_ROOT) |
| `--sessions` | List recorded sessions |
| `--session <id>` | Show details of a specific session |
| `--session-status` | Show summary of the last session |
| `--summarize` | Scan logs and save session record |
| `--skills` | List installed skills |
| `--skills-search <q>` | Search skills on skills.sh |
| `--skills-install <id>` | Install a skill (owner/repo/name) |
| `--skills-remove <name>` | Remove an installed skill |
| `--version` | Show current version |
| `--check-updates` | Check if a newer version is available on GitHub |
| `--update` | Update oh-my-agents to the latest release |

---

## 📝 Changelog

### v1.6.0 — Project Database & Auto-Session Continuity (May 2026)

**New features:**
- **ProjectDB (`project_db.py`):** SQLite database per project (`.opencode/project.db`) with tables for sessions, files_changed, errors, commands, and project_meta
- **Auto-Session:** Automatic session saving when OpenCode exits (enable with `--auto-enable`)
- **Continuity Manager:** Re-entry prompts, project health reports, pending task tracking
- **Project Hash:** Deterministic SHA-256 hash for project identity across sessions

**New CLI commands:**
| Command | Description |
|---------|-------------|
| `--auto-enable` | Enable automatic session saving |
| `--auto-disable` | Disable automatic session saving |
| `--project-status` | Show project continuity status |
| `--project-health` | Show project health report |
| `--continue` | Show re-entry context from last session |
| `--list-tasks` | List pending tasks |
| `--complete-task <index>` | Mark a pending task as complete |

**Production usage:** The system is being used successfully in the RoadFlow project for session continuity and automatic state tracking.

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

- **Auto-updater:** `update_manager.py` checks GitHub releases and downloads updates automatically
- **New CLI flags:** `--update`, `--check-updates`, `--version`
- **Update strategies:** GitHub ZIP download (fallback for non-git installs)
- **Data preservation:** Sessions, skills, logs, and `.git` history are never overwritten
- **Setup scripts:** Both `setup.sh` and `setup.ps1` support `--update`

### v1.2.1 — Path Separation, Uninstall & 3-Level Agent Discovery (April 2026)

**Critical fix — SYSTEM_ROOT vs WORKING_ROOT separation:**
- **Before (bug):** Sessions, logs, skills, and `context.md` were saved to `SYSTEM_ROOT/.opencode/`, breaking continuity when the framework was run from a different working directory.
- **After (fixed):** All runtime data (sessions, logs, skills, context.md) is now read/written relative to `WORKING_ROOT` (the current project directory).
- Introduced `resolve_working_root()` in `utils.py` — determines the active project directory.
- Introduced `find_agent_source()` — 3-level agent discovery:
  1. `WORKING_ROOT/.opencode/agents/` (local override)
  2. `~/.opencode/agents/` (global install)
  3. `SYSTEM_ROOT/.opencode/agents/` (repo bundled)

**New command: `--uninstall`**
- Removes `~/.opencode/agents/`, `sessions/`, `skills/`, `config.json` interactively
- Also removes the `oh-my-agents` wrapper from `~/.local/bin/` or `/usr/local/bin/` (Linux/Mac)
- Available in the interactive menu: "Uninstall globally"
- Also accessible via setup scripts: `./setup.sh --uninstall` or `powershell -File setup.ps1 --uninstall`

**Other improvements:**
- `--dir` now explicitly defines `WORKING_ROOT` (not `SYSTEM_ROOT`)
- All `session_manager.py` and `skill_registry.py` operations use `project_root` parameter
- Tests updated to reflect new path behavior (86 tests passing)

### v1.2.0 — 8 Agents with Benchmark-Optimized Models (April 2026)

**Model swaps based on verified benchmarks:**
- Orchestrator: `MiMo V2.5 Pro` → **Kimi K2.6** (SWE-Bench Pro 58.6%, 3x usage credits on Go plan)
- Validator: `Kimi K2.6` → **MiMo V2.5 Pro** (94% math precision for rigorous verification)

**New agents:**
- **@frontend** — UI specialist with `Qwen 3.6 Plus` (SWE-Bench Verified 78.8%, 1M context, $0.325/M tokens)
- **@ml-specialist** — ML pipelines with `MiniMax M2.7` (MLE-Bench Lite 66.6%, 10B active parameters)

**Registry fix:**
- Reincorporated `opencode-go/qwen3.5-plus` and `opencode-go/qwen3.6-plus` to available models
- Confirmed not deprecated — original issue was model ID format mismatch
- Verified available on [opencode.ai/es/go](https://opencode.ai/es/go)

### v1.1.1 — Session Continuity & Skills (April 2026)

**New features:**
- **Session bitacora:** `session_manager.py` scans OpenCode logs, saves session records, and injects context for continuity between sessions
- **Skills system:** `skill_registry.py` downloads and manages skills from [skills.sh](https://skills.sh) ecosystem
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

### v0.9.3.3 — Interactive Main Menu (April 2026)

Added interactive `questionary.select` menu that loops when configuration exists, offering: View status, Run wizard, Run diagnostics, Install globally, Exit.

### v0.9.3.1 — Path Independence & Setup Fixes (April 2026)

All Python files now use `Path(__file__).parent` for path resolution. The system works correctly regardless of the current working directory.

### v0.9.2.3 — Full English Translation (April 2026)

Translated all documentation and code comments from Spanish to English.

### v0.9.2.1 — Subagent Model Fix + Multi-Plan Support (April 2026)

Subagent model changed to `glm-5.1`. Added OpenRouter, Copilot, and Ollama plans.

### v0.9.2.0 — Rebrand to oh-my-agents (April 2026)

Renamed from `multi-agentes-opencode` to `oh-my-agents`.

### v0.9.1.0 — Base Project Sync (April 2026)

Fixed model ID mismatch — agents now use registry IDs (`opencode-go/*`).

### v0.9.0.0 — Permission Audit (April 2026)

Removed excessive write/execute permissions. Orchestrator is now strictly `read + task`. Validator is `read` only.

---

## 🤝 Contributing

Contributions are welcome! Here's how:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Ideas for contribution

- 🔌 Add support for new OpenCode plans
- 🤖 Create new specialist agents (e.g., `@doc-writer`, `@security-auditor`)
- 🎨 Improve the CLI wizard UI
- 📖 Translate documentation
- 🧪 Add integration tests
- 🧩 Add skill auto-detection based on project type

---

## 🔗 Links

- **Repository**: [visualiaconsulting/oh-my-agents](https://github.com/visualiaconsulting/oh-my-agents)
- **Organization**: [VisualIA Consulting](https://github.com/visualiaconsulting)
- **OpenCode**: [opencode.ai](https://opencode.ai)
- **Skills**: [skills.sh](https://skills.sh) · [skills.sh/docs](https://skills.sh/docs)
- **Issues**: [Report a bug](https://github.com/visualiaconsulting/oh-my-agents/issues)

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ❤️ for the [OpenCode](https://opencode.ai) community**

*If you find this useful, give it a ⭐ — it helps others discover it!*

</div>
