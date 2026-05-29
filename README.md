<div align="center">

<p>
  <b>🚀 Use my referral code and get started with OpenCode Go!</b><br>
  <a href="https://opencode.ai/go?ref=SGBJ1TJNGA">https://opencode.ai/go?ref=SGBJ1TJNGA</a><br>
  <sub>Referral code: <code>SGBJ1TJNGA</code> — helps support this project</sub>
</p>

---

# 🤖 oh-my-agents

### The multi-agent orchestration framework for [OpenCode](https://opencode.ai)

[![OpenCode](https://img.shields.io/badge/Built_for-OpenCode_Go-00D4AA?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyTDIgN2wxMCA1IDEwLTVNMiAxN2wxMCA1IDEwLTVNMiAxMmwxMCA1IDEwLTUiLz48L3N2Zz4=)](https://opencode.ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-2.0.0-blue?style=for-the-badge)](https://github.com/visualiaconsulting/oh-my-agents/releases/tag/v2.0.0)
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
| **Dashboard-First CLI** | Interactive provider selector — pick Go, LM Studio, Copilot, or OpenRouter from one screen |
| **Smart Orchestration** | The orchestrator analyzes complex tasks, decomposes them, and delegates to the right specialist |
| **15 Specialist Agents** | Each agent has a focused role: Python backend, databases, documentation, QA, security, DevOps, testing, and more |
| **Least-Privilege Permissions** | Validator and Security Reviewer are read-only. Orchestrator only delegates. |
| **Session Continuity** | Never lose context between sessions. Automatic bitacora saves errors, changes, and pending tasks |
| **Skills Ecosystem** | Extend agent capabilities with reusable skills from [skills.sh](https://skills.sh) |
| **Multi-Provider** | Switch between Go cloud, LM Studio local, GitHub Copilot, or OpenRouter with one command |
| **Zero Config Start** | Clone, run setup, start coding. The wizard handles the rest |
| **Portable** | Copy agents to any project — they adapt via `context.md` |
| **Project Database** | SQLite DB per project stores sessions, file changes, errors, commands |

---

### Provider Plans

oh-my-agents supports 4 provider plans, switchable from the interactive dashboard:

| Plan | Description | How to Activate |
|------|-------------|-----------------|
| **OpenCode Go** (default) | Cloud hosted models, 5000 credits/day | Always active or `python main.py --plan go` |
| **LM Studio** | Run agents locally on your machine | `python main.py --plan lmstudio` |
| **GitHub Copilot** | Use your Copilot subscription models | `python main.py --plan copilot` |
| **OpenRouter** | Bring your own API credits | `python main.py --plan openrouter` |

```bash
# Quick switch between providers
python main.py --plan go          # Switch to Go cloud plan
python main.py --plan lmstudio    # Auto-detect local LM Studio models
python main.py --plan copilot     # Configure Copilot models
python main.py --plan openrouter  # Configure OpenRouter models

# Or use the interactive dashboard
python main.py
```

---

## 🤖 Agents

| Agent | Model (Go Plan) | Role | Permissions |
|-------|:----------------:|------|:-----------:|
| **@orchestrator** | `deepseek-v4-pro` | 🎼 Coordinator — decomposes tasks, delegates to specialists | `read` `task` |
| **@python-engineer** | `minimax-m2.7` | 🐍 Python Backend — FastAPI, automation, APIs | `edit` `bash` `read` |
| **@db-architect** | `qwen3.6-plus` | 🗄️ PostgreSQL — schemas, queries, performance | `edit` `bash` `read` |
| **@structured-engineer** | `qwen3.5-plus` | 📋 Structured Data — JSON, YAML, OpenAPI, Docker Compose | `edit` `bash` `read` |
| **@docs-writer** | `minimax-m2.5` | 📝 Documentation — READMEs, manuals, wikis | `edit` `bash` `read` |
| **@bulk-processor** | `deepseek-v4-flash` | ⚡ Bulk Processing — repetitive, high-volume tasks | `edit` `bash` `read` |
| **@validator** | `mimo-v2.5-pro` | 🔍 QA Specialist — validates quality, linting, precision | `read` only |
| **@researcher** | `glm-5.1` | 🔬 Tech Research — explores technologies, compares frameworks | `edit` `bash` `read` |
| **@frontend-engineer** | `qwen3.6-plus` | 🎨 UI/UX — React, Next.js, Tailwind | `edit` `bash` `read` |
| **@devops** | `deepseek-v4-flash` | 🚀 Infrastructure — Docker, CI/CD, deployment | `edit` `bash` `read` |
| **@ml-specialist** | `minimax-m2.7` | 🧪 ML Engineer — training, inference, data pipelines | `edit` `bash` `read` |
| **@security-reviewer** | `mimo-v2.5-pro` | 🔒 Security — audits code, APIs, authentication | `read` only |
| **@git-manager** | `deepseek-v4-flash` | 📦 Git — commits, branches, changelogs | `edit` `bash` `read` |
| **@test-engineer** | `qwen3.5-plus` | 🧪 Testing — pytest, unit/integration tests | `edit` `bash` `read` |
| **@prompt-engineer** | `glm-5.1` | ✨ Prompt Design — AI agent instructions, workflows | `edit` `bash` `read` |

> **Model selection:** Models chosen by benchmark performance — DeepSeek V4 Pro leads GPQA Diamond (90.1%), MiMo V2.5 Pro has 94% math precision, Qwen 3.6 Plus ($0.325/M tokens) for UI work, MiniMax M2.7 leads MLE-Bench Lite (66.6%).

> **How it works:** You give a task to `@orchestrator`. It analyzes, plans, and delegates to the right specialist(s). The validator checks quality before returning results. 15 specialized agents cover the full development lifecycle.

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

> **Tip:** After installing globally, run `python main.py` to open the interactive dashboard, or `python main.py --check-updates` to check for updates.

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

## Session Management

Session management ensures you **never lose context** between OpenCode sessions. When you work on a project, close OpenCode, and come back later, the system remembers:
what was accomplished, errors that occurred, files modified, and pending tasks.

All session commands are accessible from the dashboard: run `python main.py`, then select **"Sessions & continuity"** from the plan menu.

```
OpenCode Session -> .opencode/logs/ -> session_manager.py -> .opencode/sessions/ -> context.md
```

### Session data format

Each session is saved as JSON in `.opencode/sessions/<id>.json`:

```json
{
  "session_id": "a3f8b2c1",
  "timestamp": "2026-04-29 14:32:00",
  "agent": "system",
  "summary": "Auto-summarized session...",
  "errors": ["TypeError: ..."],
  "pending_tasks": ["Fix header responsive layout"],
  "files_changed": ["src/components/Header.tsx"],
  "commands_run": ["npm run build"],
  "warnings": ["Deprecated API usage"]
}
```

> **Storage location:** Session records are always saved to `WORKING_ROOT/.opencode/sessions/` -- your active project directory.

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

### Update via dashboard
Run `python main.py`, select your provider, then choose **"Check for updates"** from the plan menu.

---

## Skills System

Skills are **reusable capabilities** for AI agents. They provide procedural knowledge, best practices, and domain-specific guidance.

The skills ecosystem is managed by [skills.sh](https://skills.sh).

Skills management is accessible from the dashboard: run `python main.py`, select your provider, then choose **"Skills & MCP tools"** from the plan menu.

### How it works

```
skills.sh (registry) -> skill_registry.py -> .opencode/skills/ -> context.md -> Agents
```

1. **Search:** Find skills on skills.sh by topic
2. **Install:** Download the skill's `.md` file from GitHub to `.opencode/skills/`
3. **Inject:** The skill content is automatically added to `context.md`
4. **Use:** All agents see the skill as part of their context

### Skill file format

```markdown
---
name: neon-postgres
description: Best practices for Neon Postgres
source: neondatabase/agent-skills
---

# Neon Postgres Best Practices

1. **Connection pooling:** Always use PgBouncer or the built-in pooler
2. **Read replicas:** Enable for read-heavy workloads
3. **Branching:** Use database branching for safe schema changes
```

### Quick example

```bash
# Search, install, and verify from the dashboard menu
# Or use the non-interactive shortcut (go to submenu first):
# The submenu will prompt for search terms and install IDs
```

---

## 💡 Examples

### Training a YOLO model

```
> complete the training of YOLO26n to 25 epochs with MuSGD and GPU 0
```

The orchestrator:
1. Asks `@python-engineer` to prepare/complete the training script
2. Asks `@validator` to verify parameters are correct
3. Executes the consolidated command

### Analyzing results

```
> review the results of the last training and compare with previous ones
```

The orchestrator:
1. Reads CSV/results.csv
2. Asks `@python-engineer` to extract metrics
3. Asks `@validator` to verify targets are met
4. Returns a comparative summary

### Multi-step task

```
> refactor the data pipeline to use async processing, add error handling, and write tests
```

The orchestrator:
1. Asks `@python-engineer` to refactor with async patterns
2. Asks `@validator` to review the refactored code
3. Asks `@test-engineer` to add error handling and tests
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

## PlanManager

The `PlanManager` supports 4 provider plans, switchable via the interactive dashboard or the `--plan` flag.

```python
from plan_manager import PlanManager

pm = PlanManager()
print(f"Plan detected: {pm.plan}")
print(f"Orchestrator model: {pm.get_model('orchestrator')}")
print(f"Plan name: {pm.get_plan_display_name()}")
```

### Supported Plans

| Plan | Orchestrator Model | How to Activate |
|------|-------------------|-----------------|
| **Go** (default) | `opencode-go/deepseek-v4-pro` | `python main.py --plan go` |
| **LM Studio** | `lmstudio/<detected-model>` | `python main.py --plan lmstudio` |
| **GitHub Copilot** | `copilot/claude-sonnet-4` | `python main.py --plan copilot` |
| **OpenRouter** | `openrouter/anthropic/claude-sonnet-4` | `python main.py --plan openrouter` |

### LM Studio Integration

LM Studio provides unlimited local inference with no API key needed. Models are auto-detected via the REST API and assigned to roles using `safe_assign_roles()`.

```bash
python main.py --plan lmstudio
```

**How role assignment works:**
1. Connects to `http://localhost:1234/v1/models` (OpenAI-compatible endpoint)
2. Filters LLM models (excludes embeddings and known-broken models from critical roles)
3. Ranks by parameter size with +0.5 boost for code models
4. Assigns in priority: orchestrator -> python-engineer -> db-architect -> validator -> ...
5. Duplicates smaller models when more roles than available LLMs
6. Backs up Go agents before replacing them (both project and global)
7. Writes LM Studio provider to `~/.config/opencode/opencode.jsonc` automatically

#### Hardware Tiers

| Tier | Hardware | Max Model | Example Models |
|------|----------|-----------|----------------|
| **Integrated** | Intel UHD/Iris, no GPU | 1.5B-3B | Qwen Coder 1.5B, Ministral 3B, Phi-3 Mini |
| **Entry GPU** | GTX 1650/1660, RTX 3050 (4-6GB) | 3B-7B | Ministral 3B, Gemma 4 E2B, Qwen 2.5 7B |
| **Mid GPU** | RTX 2060/3060/4060 (6-12GB) | 7B-14B | Qwen 2.5 7B, Mistral 7B, Llama 3.1 8B |
| **High GPU** | RTX 3090/4090 (24GB+) | 30B-70B | Llama 3.3 70B, Qwen 2.5 72B |

**Requirements:**
- LM Studio 0.4+ running with the HTTP server enabled
- API Token authentication must be disabled in LM Studio -> Developer -> Server panel
- Models must be already downloaded in LM Studio

**Troubleshooting:**
- Run `python main.py --plan lmstudio` to auto-detect and install
- If you get `invalid_api_key` errors, disable API token auth in LM Studio's Server settings
- If the orchestrator has template errors, `safe_assign_roles()` will reassign Nemotron to least critical roles automatically
- **Error `n_keep >= n_ctx`**: Set Context Length to >= 32768 in LM Studio model settings, then reload

---

## 📁 Project Structure

```
oh-my-agents/
├── README.md                    # This file
├── AGENTS.md                    # Detailed agent state & changelog
├── plan_manager.py              # Go-only plan manager + lmstudio via plan.json
├── plan_fallback.py             # Simplified fallback (manual reset only)
├── lmstudio_manager.py          # LM Studio detection, ranking, role assignment
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
│   ├── test_plan_manager.py     # Go-only tests
│   ├── test_lmstudio.py         # LM Studio manager tests
│   ├── test_wizard.py           # Wizard tests
│   └── test_main.py             # Main CLI tests
└── .opencode/
    ├── context.md               # Global context injected to all agents
    ├── sessions/                # Session records (gitignored)
    ├── skills/                  # Installed skills (gitignored)
    └── agents/
        ├── orchestrator.md      # Main coordinator
        ├── python-engineer.md   # Python backend engineer
        ├── db-architect.md      # PostgreSQL specialist
        ├── structured-engineer.md # JSON/YAML/OpenAPI specialist
        ├── docs-writer.md       # Technical documentation
        ├── bulk-processor.md    # Bulk processing
        ├── validator.md         # QA and code validation (read-only)
        ├── researcher.md        # Tech researcher
        ├── frontend-engineer.md # UI/UX specialist
        ├── devops.md            # Docker/CI/CD specialist
        ├── ml-specialist.md     # ML and data pipeline specialist
        ├── security-reviewer.md # Security auditor (read-only)
        ├── git-manager.md       # Git specialist
        ├── test-engineer.md     # Testing specialist
        └── prompt-engineer.md   # Prompt designer
```

### CLI Usage

```
python main.py                          Interactive provider dashboard
python main.py --plan NAME              Switch to a provider (go, lmstudio, copilot, openrouter)
python main.py --status                 Show current plan and agent status
python main.py --doctor                 Run system diagnostics
python main.py --setup                  Run Go plan setup wizard
python main.py --install-global         Install agents globally to ~/.opencode/agents/
python main.py --uninstall              Remove global installation
python main.py --version                Show version
python main.py --check-updates          Check for updates
python main.py --update                 Update to latest version
python main.py --dir DIR                Set project root directory
```

---

## 📝 Changelog

### v2.0.0 — 15 Specialized Agents (May 2026)

**Major restructuring: 8 generic agents → 15 specialized agents.**

| Before | After |
|--------|-------|
| orchestrator | orchestrator |
| code-analyst | python-engineer, db-architect, structured-engineer |
| validator | validator |
| bulk-processor | bulk-processor |
| subagent | researcher, devops, git-manager |
| summarizer | docs-writer, prompt-engineer |
| frontend | frontend-engineer |
| ml-specialist | ml-specialist, security-reviewer, test-engineer |

**New agents:**
- **@python-engineer** — Python backend specialist (FastAPI, automation, APIs)
- **@db-architect** — PostgreSQL schemas, queries, performance
- **@structured-engineer** — JSON, YAML, OpenAPI, Docker Compose
- **@docs-writer** — Technical documentation (READMEs, manuals, wikis)
- **@researcher** — Tech research and framework comparison
- **@frontend-engineer** — UI/UX specialist (React, Next.js, Tailwind)
- **@devops** — Docker, CI/CD, deployment infrastructure
- **@security-reviewer** — Security auditor (read-only)
- **@git-manager** — Git specialist (commits, branches, changelogs)
- **@test-engineer** — Testing specialist (pytest, unit/integration tests)
- **@prompt-engineer** — Prompt designer for AI agents and workflows

**Removed agents:**
- `code-analyst` → replaced by `python-engineer`
- `subagent` → replaced by `researcher`, `devops`, `git-manager`
- `summarizer` → replaced by `docs-writer` (session analysis moved to system)
- `frontend` → renamed to `frontend-engineer`

**Permission changes:**
- `validator` → now read-only (edit: deny, bash: deny)
- `security-reviewer` → read-only (edit: deny, bash: deny)
- All execution agents retain full edit/bash/read permissions

**Files modified:**
- `plan_manager.py` — 15 roles, permissions, descriptions, ALL_ROLES
- `lmstudio_manager.py` — 15 ROLE_NAMES, safe_assign_roles() priority order
- `main.py` — _pick_models_for_plan() uses 15 roles
- `cli/wizard.py` — 15 agent defaults, permission map
- `.opencode/context.md` — v2.0.0, 15 agents listed
- `agents.md` — Full documentation update
- `tests/test_plan_manager.py` — 33 tests for 15 roles
- `tests/test_wizard.py` — 27 tests for 15 agents
- `tests/test_lmstudio.py` — Updated for new role names

**Tests:** 178 passing

### v1.8.0 — Dashboard-First CLI, Copilot & OpenRouter Plans (May 2026)

**New --plan system:** Four provider plans in one unified CLI.

| Plan | Flag | Description |
|------|------|-------------|
| Go | `--plan go` | Default cloud plan, 5000 credits/day |
| LM Studio | `--plan lmstudio` | Local models, auto-detect and assign |
| GitHub Copilot | `--plan copilot` | Copilot subscription models |
| OpenRouter | `--plan openrouter` | Bring your own API credits |

**Dashboard-first interactive menu:**
- Running `python main.py` shows a provider selector with all 4 plans at a glance
- Selecting a plan activates it and shows a contextual menu (Status, Diagnostics, Sessions, Skills/MCP)
- Sessions, skills, and MCP tools are now in clean submenus, not top-level

**CLI flags reduced from ~30 to ~10:**
- Removed: `--install-lmstudio`, `--install-lmstudio-manual`, `--lmstudio-status`, `--reset-go`
- Removed: `--sessions`, `--session`, `--session-status`, `--summarize`
- Removed: `--skills`, `--skills-search`, `--skills-install`, `--skills-remove`
- Removed: `--auto-enable`, `--auto-disable`, `--project-status`, `--project-health`
- Removed: `--mcp-status`, `--mcp-add`, `--skills-recommend`, `--skills-auto`
- All removed functionality is accessible via the interactive dashboard submenus

**New plan_manager.py features:**
- `copilot` and `openrouter` plans with full model mappings
- `get_plan_display_name()`, `get_plan_description()`, `save_plan()` methods
- Model selection wizard for Copilot and OpenRouter plans

### v1.7.0 — LM Studio Integration & Go-Only Standard (May 2026)

**New features:**
- **LM Studio Manager (`lmstudio_manager.py`):** Detects LM Studio server, lists downloaded models, ranks by size, assigns roles automatically or manually
- **Auto role assignment:** Largest model → orchestrator, 2nd → python-engineer, etc. Code models get a boost for python-engineer role
- **Manual mode:** User selects which model goes to each role via interactive menu
- **Backup & restore:** Go agents are backed up before LM Studio install; `--reset-go` restores them

**New CLI commands:**
| Command | Description |
|---------|-------------|
| `--install-lmstudio` | Auto-detect models, assign roles by size |
| `--install-lmstudio-manual` | Manually assign models to roles |
| `--lmstudio-status` | Show server status and current assignments |
| `--reset-go` | Restore Go plan from backup |

**Breaking changes:**
- **Go-only standard:** `_detect_plan()` always returns `"go"` unless `plan.json` says `"lmstudio"`
- **No auto-detection:** Zen, API, OpenRouter, Copilot, Ollama are no longer auto-detected
- **No automatic fallback:** Removed `FALLBACK_CHAIN`, `ZEN_FREE_MODELS`, `get_free_model()`, `switch_to_fallback()`
- **Removed agents:** `bugfix210526.md`, `orquestador.md`, `proptech_expert.md`, `prompt_crafter.md`, `python_architect.md`, `qa_reviewer.md`

**Files changed:**
- `lmstudio_manager.py` — New: LM Studio detection, ranking, role assignment
- `plan_manager.py` — Simplified: Go-only, lmstudio via plan.json
- `plan_fallback.py` — Simplified: no automatic fallback chain
- `main.py` — 4 new commands + interactive menu options
- `tests/test_lmstudio.py` — 26 tests: detection, parsing, role assignment, global config, safe_assign
- `tests/test_plan_manager.py` — Updated for Go-only behavior

**Tests:** 158 passing

### v1.7.2 — Global Agent Install, Nemotron Template Fix & Hardware Tiers (May 2026)

**Bug fix — LM Studio agents installed globally:**
- `install_lmstudio_agents()` now writes agents to both project `.opencode/agents/` AND global `~/.opencode/agents/` so `opencode --agent orchestrator` finds LM Studio models.
- `reset_to_go()` restores both locations from backup.

**Bug fix — Nemotron broken Jinja2 template:**
- Added `safe_assign_roles()` that detects Nemotron (and similar broken models) and reassigns them to least critical roles, keeping stable models for orchestrator.

**New feature — Hardware tiers:**
- Documented 4 hardware tiers (Integrated, Entry GPU, Mid GPU, High GPU) with recommended models for each.

**Files modified:**
- `lmstudio_manager.py` — Added `safe_assign_roles()`, `_install_agents_to_dir()`, `_restore_agents_from_backup()`, `_rmtree()`, model limits in config
- `main.py` — Fixed Unicode arrow for Windows cp1252
- `tests/test_lmstudio.py` — 6 new tests (26 total)

**Tests:** 168 passing (26 LM Studio tests)

### v1.7.1 — LM Studio Auth Fix & Global Config (May 2026)

**Bug fix — LM Studio API token requirement:**
- LM Studio 0.4.12+ requires a Bearer token. Fixed by documenting the "Require API Token" toggle in Developer → Server panel.
- Switched from deprecated `/api/v0/models` to OpenAI-compatible `/v1/models` endpoint.

**New feature:**
- `ensure_global_lmstudio_config()` writes LM Studio provider to `~/.config/opencode/opencode.jsonc` so OpenCode can connect to the local server. Called automatically during `--install-lmstudio`.

**Files modified:**
- `lmstudio_manager.py` — Added global config writer, rewritten for v1 API

**Tests:** 168 passing (19 pre-existing failures on LM Studio projects where tests expect Go plan)

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
- **Agent permissions:** `mcp: allow` for orchestrator and python-engineer

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
- **@frontend-engineer** — UI/UX specialist with `Qwen 3.6 Plus` (SWE-Bench Verified 78.8%, 1M context, $0.325/M tokens)
- **@ml-specialist** — ML pipelines with `MiniMax M2.7` (MLE-Bench Lite 66.6%, 10B active parameters)

**Registry fix:**
- Reincorporated `opencode-go/qwen3.5-plus` and `opencode-go/qwen3.6-plus` to available models
- Confirmed not deprecated — original issue was model ID format mismatch
- Verified available on [opencode.ai/es/go](https://opencode.ai/es/go)

### v1.1.1 — Session Continuity & Skills (April 2026)

**New features:**
- **Session bitacora:** `session_manager.py` scans OpenCode logs, saves session records, and injects context for continuity between sessions
- **Skills system:** `skill_registry.py` downloads and manages skills from [skills.sh](https://skills.sh) ecosystem
- **@docs-writer agent:** Technical documentation writer (`opencode-go/minimax-m2.5`) for READMEs, manuals, and wikis
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
- `.opencode/agents/docs-writer.md` — Docs writer agent definition

### v0.9.3.3 — Interactive Main Menu (April 2026)

Added interactive `questionary.select` menu that loops when configuration exists, offering: View status, Run wizard, Run diagnostics, Install globally, Exit.

### v0.9.3.1 — Path Independence & Setup Fixes (April 2026)

All Python files now use `Path(__file__).parent` for path resolution. The system works correctly regardless of the current working directory.

### v0.9.2.3 — Full English Translation (April 2026)

Translated all documentation and code comments from Spanish to English.

### v0.9.2.1 — Subagent Model Fix + Multi-Plan Support (April 2026)

Subagent model changed to `glm-5.1`. Added OpenRouter, Copilot, and Ollama plans. (Agents later restructured in v2.0.0)

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
- 🤖 Create new specialist agents (e.g., `@data-engineer`, `@platform-engineer`)
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
