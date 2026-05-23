# 📖 Manual de Usuario — oh-my-agents v1.8.0

> Guía completa para instalar, configurar y usar el sistema de agentes multi-especialista en OpenCode. Incluye dashboard de proveedores, MCP, skills, actualizaciones y desinstalación.

---

## Tabla de Contenidos

1. [Instalación desde Cero](#1-instalación-desde-cero)
2. [Los 8 Agentes](#2-los-8-agentes)
3. [Resolución de Rutas (SYSTEM vs WORKING)](#3-resolución-de-rutas-system-vs-working)
4. [Session Management (Bitácora)](#4-session-management-bitácora)
5. [Skills System](#5-skills-system)
6. [MCP — Model Context Protocol](#6-mcp--model-context-protocol)
7. [Sistema de Actualización Automática](#7-sistema-de-actualización-automática)
8. [Desinstalación Global](#8-desinstalación-global)
9. [Referencia CLI](#9-referencia-cli)
10. [PlanManager](#10-planmanager)
11. [Troubleshooting](#11-troubleshooting)
12. [Quick Reference Card](#12-quick-reference-card)

---

## 1. Instalación desde Cero

### Requisitos Previos

| Requisito | Versión | Cómo verificar |
|-----------|---------|----------------|
| Python | 3.8+ | `python --version` |
| OpenCode CLI | Última | `opencode --version` |
| Suscripción Go | Activa | [opencode.ai/es/go](https://opencode.ai/es/go) |

### Opción A: Instalación Completa (recomendada)

```powershell
# 1. Clonar el repositorio
git clone https://github.com/visualiaconsulting/oh-my-agents.git
cd oh-my-agents

# 2. Ejecutar setup (instala dependencias, configura agentes, instala global)
.\setup.ps1

# 3. Verificar
python main.py --doctor
```

**¿Qué hace setup.ps1?**
1. Busca Python 3.8+ en tu sistema
2. Instala dependencias (PyYAML, questionary, rich, requests, pytest)
3. Verifica que OpenCode CLI esté disponible
4. Ejecuta el wizard interactivo para configurar agentes
5. Instala los agentes globalmente en `~/.opencode/agents/`

### Opción B: Instalación Rápida

```powershell
git clone https://github.com/visualiaconsulting/oh-my-agents.git
cd oh-my-agents
.\install.ps1
```

**¿Qué hace install.ps1?**
- Instala dependencias
- Instala agentes globalmente
- Sin wizard interactivo — usa la configuración por defecto (8 agentes)

### Verificar Instalación

```powershell
python main.py --doctor
```

Output esperado:
```
=== System Diagnostics ===

  ✔ Python 3.14.4
  ✔ Dependencies installed (PyYAML, questionary, rich)
  ✔ OpenCode CLI available
  ✔ Agents configured: 8
  ✔ All agent model IDs valid (8 models)
  ℹ No sessions recorded yet
  ℹ No skills installed

==============================
```

### Instalación Global — ¿Qué es?

OpenCode busca agentes en `.opencode/agents/` del directorio actual. La instalación global copia los agentes a `~/.opencode/agents/` para que `opencode --agent orchestrator` funcione desde **cualquier carpeta**.

```powershell
# Verificar que los agentes están instalados globalmente
ls ~/.opencode/agents/
```

Output esperado:
```
bulk-processor.md
code-analyst.md
frontend.md
ml-specialist.md
orchestrator.md
subagent.md
summarizer.md
validator.md
```

---

## 2. Los 8 Agentes

### Tabla de Agentes

| # | Agente | Modelo | Benchmark | Rol |
|---|--------|--------|-----------|-----|
| 1 | `@orchestrator` | Kimi K2.6 | SWE-Bench Pro 58.6% | Coordinador — descompone tareas y delega |
| 2 | `@code-analyst` | DeepSeek V4 Pro | GPQA Diamond 90.1% | Ingeniero senior — código y arquitectura |
| 3 | `@validator` | MiMo V2.5 Pro | 94% math precision | QA — verificación y edge cases |
| 4 | `@bulk-processor` | DeepSeek V4 Flash | MMLU-Pro 87.5% | Procesamiento masivo (oculto) |
| 5 | `@subagent` | GLM-5.1 | Generalista | Fallback y debugging |
| 6 | `@summarizer` | MiniMax M2.5 | Ligero | Análisis post-sesión y bitácora |
| 7 | `@frontend` | Qwen 3.6 Plus | SWE-Bench Verified 78.8% | UI — React, TypeScript, Tailwind |
| 8 | `@ml-specialist` | MiniMax M2.7 | MLE-Bench Lite 66.6% | ML — training, inference, pipelines |

### Permisos

| Agente | edit | bash | read | task | mcp |
|--------|:----:|:----:|:----:|:----:|:---:|
| @orchestrator | ❌ | ❌ | ✅ | ✅ | ✅ |
| @code-analyst | ✅ | ✅ | ✅ | ❌ | ✅ |
| @validator | ❌ | ❌ | ✅ | ❌ | ❌ |
| @bulk-processor | ✅ | ✅ | ✅ | ❌ | ❌ |
| @subagent | ✅ | ✅ | ✅ | ❌ | ❌ |
| @summarizer | ✅ | ✅ | ✅ | ❌ | ❌ |
| @frontend | ✅ | ✅ | ✅ | ❌ | ❌ |
| @ml-specialist | ✅ | ✅ | ✅ | ❌ | ❌ |

> **v1.5.0:** Los agentes ahora tienen prompts de rol específicos y detallados en sus cuerpos `.md`. El orquestador sabe que debe descomponer y delegar, el validator sabe que es read-only, y cada especialista conoce su stack tecnológico y responsabilidades.

### Flujo Típico

```
Usuario: "Refactoriza el pipeline de datos para usar async, añade tests"
    ↓
@orchestrator (Kimi K2.6)
    ├── Analiza la tarea
    ├── Descompone en subtareas
    ├── Delega a @code-analyst (DeepSeek V4 Pro)
    │       └── Implementa async + tests
    ├── Delega a @validator (MiMo V2.5 Pro)
    │       └── Verifica lógica, edge cases
    └── Retorna resultado consolidado
```

---

## 3. Resolución de Rutas (SYSTEM vs WORKING)

### El Problema Original

Antes de v1.3.3, cuando instalabas globalmente (`--install-global`) y ejecutabas `main.py` desde otro directorio, las sesiones, skills y logs se guardaban en la carpeta del repo (`SYSTEM_ROOT`) en vez de tu proyecto activo (`WORKING_ROOT`). Esto rompía la continuidad entre sesiones.

### La Solución: Dos Raíces

| Concepto | Descripción | ¿Dónde apunta? | Se usa para |
|----------|-------------|----------------|-------------|
| **SYSTEM_ROOT** | Carpeta donde está instalado oh-my-agents | Donde clonaste el repo | Código fuente, agentes base, instalación global |
| **WORKING_ROOT** | Tu proyecto activo | `CWD` actual o `--dir` | Logs, sesiones, skills, `context.md` |

### Ejemplo

```powershell
# Clonaste el repo en:
C:\Users\tu\oh-my-agents          ← SYSTEM_ROOT

# Estás trabajando en:
C:\Users\tu\mi-proyecto           ← WORKING_ROOT (CWD)
```

### Detección de Agentes (3 Niveles)

El sistema busca agentes `.md` en este orden (usa el primero que encuentre):

1. `WORKING_ROOT/.opencode/agents/` — override local por proyecto
2. `~/.opencode/agents/` — instalación global
3. `SYSTEM_ROOT/.opencode/agents/` — agentes incluidos en el repo

Esto significa que puedes tener agentes personalizados por proyecto sin tocar la instalación global.

### Flujo de Datos

```
                        ┌──────────────────────┐
                        │  WORKING_ROOT        │
                        │  (tu proyecto)       │
                        │                      │
                        │  .opencode/          │
                        │  ├── logs/     ← Logs de OpenCode │
                        │  ├── sessions/ ← Bitácora         │
                        │  ├── skills/   ← Skills instalados│
                        │  ├── mcp.json  ← Config MCP       │
                        │  └── context.md← Contexto activo   │
                        └──────────────────────┘
                        
                        ┌──────────────────────┐
                        │  SYSTEM_ROOT         │
                        │  (oh-my-agents repo) │
                        │                      │
                        │  main.py             │
                        │  utils.py            │
                        │  .opencode/agents/   │ ← Agentes base
                        └──────────────────────┘
```

---

## 4. Session Management (Bitácora)

### ¿Qué es?

El sistema de bitácora guarda un registro de cada sesión de trabajo para que no pierdas contexto entre sesiones. Cuando cierras OpenCode y vuelves al día siguiente, el sistema recuerda qué hiciste, qué errores hubo, y qué quedó pendiente.

### Flujo Completo

```
Día 1: Trabajas en OpenCode
    ↓
Cierras OpenCode
    ↓
python main.py --summarize    ← Escanea logs y guarda la sesión
    ↓
Día 2: Abres OpenCode
    ↓
El orquestador lee context.md ← Sabe lo que pasó ayer
    ↓
Continúas donde lo dejaste
```

### Comandos

#### `--summarize` — Guardar sesión

```powershell
python main.py --summarize
```

Output:
```
✔ Session saved: a3f8b2c1
  Files changed: 12
  Errors found: 2
  Context updated in .opencode/context.md
```

**¿Qué hace?**
1. Lee `.opencode/logs/` (logs de OpenCode)
2. Extrae: errores, archivos modificados, comandos ejecutados
3. Guarda JSON en `.opencode/sessions/a3f8b2c1.json`
4. Actualiza `context.md` con las últimas 3 sesiones

#### `--sessions` — Ver historial

```powershell
python main.py --sessions
```

Output:
```
Session History
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━┓
┃ ID       ┃ Timestamp          ┃ Agent      ┃ Summary            ┃ Errs ┃ Files┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━┩
│ a3f8b2c1 │ 2026-04-29 14:32   │ @summarizer│ Auto-summarized... │  2   │  12  │
│ b7c2d4e5 │ 2026-04-28 10:15   │ @summarizer│ Auto-summarized... │  0   │   5  │
└──────────┴────────────────────┴────────────┴────────────────────┴──────┴──────┘
```

#### `--session-status` — Última sesión

```powershell
python main.py --session-status
```

Output:
```
=== Last Session ===

  Session: a3f8b2c1
  Time:    2026-04-29 14:32:00
  Agent:   @summarizer

  Summary:
  Auto-summarized session. 12 files changed, 2 errors found.

  Errors (2):
    • TypeError: cannot read property 'x' of undefined
    • Failed to compile src/components/Header.tsx

  Files Changed (12):
    • src/components/Header.tsx
    • src/utils/api.ts
    • ...
```

#### `--session <id>` — Detalle de sesión específica

```powershell
python main.py --session a3f8b2c1
```

### Formato JSON de una Sesión

Cada sesión se guarda en `.opencode/sessions/<id>.json`:

```json
{
  "session_id": "a3f8b2c1",
  "timestamp": "2026-04-29 14:32:00",
  "agent": "summarizer",
  "summary": "Auto-summarized session. 12 files changed, 2 errors found.",
  "errors": ["TypeError: cannot read property 'x' of undefined"],
  "pending_tasks": ["Fix header responsive layout"],
  "files_changed": ["src/components/Header.tsx"],
  "commands_run": ["npm run build"],
  "warnings": ["Deprecated API usage"]
}
```

### Ejemplo Práctico Paso a Paso

```powershell
# 1. Trabaja en OpenCode durante 2 horas
opencode --agent orchestrator
# ... haces tu trabajo ...
# Sales de OpenCode

# 2. Guarda la sesión
python main.py --summarize
# ✔ Session saved: x1y2z3w4

# 3. Al día siguiente, verifica qué hiciste
python main.py --session-status
# Muestra resumen de la última sesión

# 4. Abre OpenCode — el orquestador ya sabe lo que pasó
opencode --agent orchestrator
# Lee context.md y continúa donde lo dejaste
```

---

## 5. Skills System

### ¿Qué son las Skills?

Las skills son **capacidades reutilizables** para agentes AI. Proveen conocimiento procedural, mejores prácticas, y guías específicas de dominio.

Browse skills en: [skills.sh](https://skills.sh)
Documentación: [skills.sh/docs](https://skills.sh/docs)

### Skills Predefinidas (Auto-Detección) — v1.5.0

oh-my-agents incluye un catálogo de **9 skills predefinidas**. El sistema analiza tu proyecto y recomienda skills relevantes automáticamente.

#### Catálogo Built-in

| Skill | Se activa cuando hay... |
|-------|------------------------|
| **React + TypeScript** | `package.json`, `*.tsx`, `vite.config.ts` |
| **Django REST Framework** | `manage.py`, `settings.py` |
| **FastAPI** | `main.py` con FastAPI, `pyproject.toml` |
| **SQL & PostgreSQL** | `docker-compose.yml`, SQL migrations |
| **Docker & Containers** | `Dockerfile`, `docker-compose.yml` |
| **Tailwind CSS** | `tailwind.config.js`, `*.html` |
| **Python Testing** | `conftest.py`, `pytest.ini`, `test_*.py` |
| **Git Workflow** | `.gitignore`, `.github/workflows/` |
| **ML Pipeline** | `*.ipynb`, `train.py`, scikit-learn/tensorflow |

#### `--skills-recommend` — Analizar proyecto y recomendar skills

```powershell
python main.py --skills-recommend
```

Output:
```
=== Recommended Skills ===

  1. Docker & Containers — Dockerfile best practices, multi-stage builds
     Tags: devops, docker, containers
  2. Python Testing — pytest patterns, fixtures, mocking
     Tags: python, testing, quality
  3. Git Workflow — conventional commits, branching strategies
     Tags: git, workflow, collaboration

? Install recommended skills? (Y/n)
```

#### `--skills-auto` — Instalar recomendaciones sin preguntar

```powershell
python main.py --skills-auto
```

Output:
```
✔ Installed docker
✔ Installed python-testing
✔ Installed git-workflow
```

### Skills desde skills.sh

#### `--skills-search <query>` — Buscar skills

```powershell
python main.py --skills-search database
```

Output:
```
Skills Search: 'database'
┏━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃# ┃ Name                   ┃ Description ┃ Repo                        ┃
┡━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│1 │ neon-postgres          │ —           │ neondatabase/agent-skills   │
│2 │ prisma-database-setup  │ —           │ prisma/skills               │
│3 │ postgres               │ —           │ planetscale/database-skills │
│4 │ database-migration     │ —           │ wshobson/agents             │
│5 │ database               │ —           │ railwayapp/railway-skills   │
└──┴────────────────────────┴─────────────┴─────────────────────────────┘

Install with: python main.py --skills-install owner/repo/name
```

#### `--skills-install <owner/repo/name>` — Instalar skill

```powershell
python main.py --skills-install neondatabase/agent-skills/neon-postgres
```

Output:
```
✔ Skill 'neon-postgres' installed to .opencode/skills/
```

**¿Qué hace?**
1. Descarga el archivo `.md` desde GitHub
2. Lo guarda en `.opencode/skills/neon-postgres.md`
3. La próxima vez que se ejecute un agente, la skill se inyecta en `context.md`

#### `--skills` — Ver skills instaladas

```powershell
python main.py --skills
```

Output:
```
Installed Skills
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name          ┃ Description                ┃ Source               ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ neon-postgres │ Best practices for Neon    │ neondatabase/agent-skills
└───────────────┴────────────────────────────┴──────────────────────┘
```

#### `--skills-remove <name>` — Remover skill

```powershell
python main.py --skills-remove neon-postgres
```

Output:
```
✔ Skill 'neon-postgres' removed.
```

### Ejemplo Práctico Completo

```powershell
# 1. Busca skills de React
python main.py --skills-search react

# 2. Instala la que necesites
python main.py --skills-install vercel-labs/agent-skills/vercel-react-best-practices

# 3. Verifica que se instaló
python main.py --skills

# 4. Usa OpenCode — la skill ya está en el contexto
opencode --agent orchestrator
# El orquestador y todos los agentes ahora conocen las mejores prácticas de React

# 5. Si ya no la necesitas
python main.py --skills-remove vercel-react-best-practices
```

### Dónde se Guardan

| Contenido | Directorio |
|-----------|------------|
| Skills instaladas | `.opencode/skills/*.md` |
| Contexto inyectado | `.opencode/context.md` (sección "Active Skills") |

---

## 6. MCP — Model Context Protocol

### ¿Qué es MCP?

MCP (Model Context Protocol) es un protocolo abierto de Anthropic que permite a los agentes AI conectarse con **herramientas externas** y **fuentes de datos** en tiempo real. En vez de que los agentes solo lean/escriban archivos, con MCP pueden:

- Consultar bases de datos SQL
- Leer/escribir en el sistema de archivos como herramienta
- Interactuar con APIs de GitHub
- Conectarse a Slack, Jira, o cualquier servicio con servidor MCP

### ¿Cómo Funciona?

```
Agente → MCP Client (oh-my-agents) → Servidor MCP (PostgreSQL, etc.)
   ↑                                        ↓
   └────────── resultado JSON-RPC ──────────┘
```

### Templates Predefinidos

oh-my-agents incluye 3 templates listos para usar:

| Template | Comando | Descripción |
|----------|---------|-------------|
| `filesystem` | `npx @modelcontextprotocol/server-filesystem` | Acceso al sistema de archivos como tool MCP |
| `sqlite` | `uvx mcp-server-sqlite` | Consultas a bases SQLite |
| `github` | `npx @modelcontextprotocol/server-github` | Operaciones de GitHub API |

### Comandos

#### `--mcp-add <template>` — Añadir servidor MCP

```powershell
python main.py --mcp-add filesystem
```

Output:
```
✔ Added MCP server 'filesystem'
Run 'python main.py --mcp-status' to verify.
```

Esto guarda la configuración en `.opencode/mcp.json`.

#### `--mcp-status` — Ver servidores y herramientas

```powershell
python main.py --mcp-status
```

Output:
```
=== MCP Servers ===

  filesystem — Read and write files on the local filesystem
    ✔ Connected (4 tool(s))
      • read_file: Read the complete contents of a file
      • write_file: Create a new file or overwrite an existing file
      • list_directory: List the contents of a directory
      • search_files: Search for files matching a pattern
```

### Agentes con MCP Habilitado

Los agentes `@orchestrator` y `@code-analyst` tienen `mcp: allow` en sus permisos. Esto les permite ver y usar herramientas MCP cuando están disponibles. El catálogo de herramientas se inyecta automáticamente en `context.md`.

### Seguridad

- **NUNCA** comitees `.opencode/mcp.json` (está en `.gitignore`)
- El template `github` requiere un token personal — configúralo como variable de entorno, no en el archivo
- Los comandos MCP se ejecutan como subprocesos locales (no hay `shell=True`)

---

## 7. Sistema de Actualización Automática

### ¿Qué es?

oh-my-agents puede **actualizarse a sí mismo** desde GitHub releases con un solo comando. Descarga la última versión, reemplaza los archivos del sistema, y **preserva** tus datos (sesiones, skills, logs, agentes personalizados).

### Comandos

#### `--version` — Ver versión actual

```powershell
python main.py --version
```

Output:
```
oh-my-agents v1.5.0
```

#### `--check-updates` — Buscar actualizaciones

```powershell
python main.py --check-updates
```

Output (sin updates):
```
✔ oh-my-agents is up to date (v1.5.0).
```

Output (con update disponible):
```
=== Update Available ===

  Current:  v1.5.0
  Latest:   v1.6.0

  Run python main.py --update to install.
```

#### `--update` — Instalar actualización

```powershell
python main.py --update
```

**¿Qué hace?**
1. Consulta la API de GitHub para la última versión
2. Descarga el ZIP del release
3. Crea backup de los archivos actuales
4. Sobrescribe archivos del framework (`.py`, `cli/`, `tests/`)
5. **Preserva** tus sesiones, skills, logs y `.git`
6. Actualiza el archivo `VERSION`

**Qué NUNCA se toca durante un update:**
- `.opencode/sessions/` — tu historial de bitácora
- `.opencode/skills/` — tus skills instalados
- `.opencode/logs/` — logs de OpenCode
- `~/.opencode/agents/` — tus agentes personalizados
- `.git/` — historial de git

También puedes actualizar vía scripts:
```bash
./setup.sh --update
powershell -File setup.ps1 --update
```

---

## 8. Desinstalación Global

### `--uninstall` — Remover instalación global

Si necesitas limpiar la instalación o tienes conflictos de versión:

```powershell
python main.py --uninstall
```

**¿Qué hace?**
1. Detecta `~/.opencode/agents/`, `sessions/`, `skills/`, `config.json`
2. Te pregunta interactivamente qué quieres eliminar
3. Elimina los directorios/archivos seleccionados
4. En Linux/Mac, también borra el wrapper `oh-my-agents` de `/usr/local/bin/` o `~/.local/bin/`

Ejemplo de sesión:
```
=== Uninstall oh-my-agents ===

The following will be removed:
  ✖ Global agents: C:\Users\tu\.opencode\agents
  ✖ Global sessions: C:\Users\tu\.opencode\sessions
  ✖ Global skills: C:\Users\tu\.opencode\skills
  ✖ Global config: C:\Users\tu\.opencode\config.json

? Remove ALL of the above (agents, sessions, skills, config)? (Y/n) Y
? This action cannot be undone. Continue? (y/N) Y

  ✔ Removed Global agents
  ✔ Removed Global sessions
  ✔ Removed Global skills
  ✔ Removed Global config
✔ Uninstall complete. 4 item(s) removed.
```

**IMPORTANTE:** La desinstalación **NO** borra el repositorio clonado de oh-my-agents. Para eliminarlo completamente, borra la carpeta del repo manualmente.

También disponible vía scripts:
```bash
./setup.sh --uninstall
powershell -File setup.ps1 --uninstall
```

---

## 9. Referencia CLI

### Argumentos CLI (v1.8.0)

El CLI se ha simplificado de ~30 flags a ~10. La funcionalidad eliminada está disponible en el dashboard interactivo.

| Argumento | Descripción |
|-----------|-------------|
| `--plan NAME` | Cambiar a proveedor (`go`, `lmstudio`, `copilot`, `openrouter`) |
| `--status` | Mostrar plan activo y estado de agentes |
| `--doctor` | Diagnóstico completo del entorno |
| `--setup` | Forzar wizard de configuración (Go plan) |
| `--install-global` | Copiar agentes a `~/.opencode/agents/` |
| `--uninstall` | Eliminar instalación global interactivamente |
| `--version` | Mostrar versión actual |
| `--check-updates` | Buscar nuevas versiones en GitHub |
| `--update` | Actualizar oh-my-agents a la última versión |
| `--dir DIR` | Definir explícitamente el WORKING_ROOT |

### Dashboard Interactivo

Ejecutar `python main.py` sin argumentos abre el dashboard con selector de proveedores:

```
? What would you like to do?
  ❯ Switch to Go plan
    Switch to LM Studio
    Switch to GitHub Copilot
    Switch to OpenRouter
    ---
    View agent status
    Run diagnostics
    Tools & advanced
    Exit
```

Seleccionar un plan lo activa y muestra un menú contextual con opciones como Status, Diagnostics, Sessions, Skills/MCP, Updates.

### Flags Eliminados (accesibles vía dashboard)

Los siguientes flags ya no existen como argumentos CLI. Su funcionalidad está disponible en los submenús del dashboard:

- `--sessions`, `--session`, `--session-status`, `--summarize`
- `--skills`, `--skills-search`, `--skills-install`, `--skills-remove`
- `--skills-recommend`, `--skills-auto`
- `--mcp-add`, `--mcp-status`
- `--install-lmstudio`, `--install-lmstudio-manual`, `--lmstudio-status`, `--reset-go`
- `--auto-enable`, `--auto-disable`
- `--project-status`, `--project-health`, `--continue`, `--list-tasks`, `--complete-task`

---

## 10. PlanManager

### ¿Qué es?

El PlanManager soporta **4 proveedores** seleccionables explícitamente. No hay detección automática — el usuario elige el plan vía dashboard o flag `--plan`.

### Planes Soportados

| Plan | Flag | Orchestrator Model | Descripción |
|------|------|-------------------|-------------|
| **Go** (default) | `--plan go` | `opencode-go/deepseek-v4-pro` | 5000 créditos/día en OpenCode Go |
| **LM Studio** | `--plan lmstudio` | `lmstudio/<detectado>` | Inferencia local ilimitada |
| **GitHub Copilot** | `--plan copilot` | `copilot/claude-sonnet-4` | Modelos vía suscripción Copilot |
| **OpenRouter** | `--plan openrouter` | `openrouter/anthropic/claude-sonnet-4` | Bring-your-own-API-key |

### Cambiar de Plan

```powershell
# Dashboard interactivo
python main.py

# Directo por flag
python main.py --plan go
python main.py --plan lmstudio
python main.py --plan copilot
python main.py --plan openrouter
```

---

## 11. Troubleshooting

### "OpenCode CLI not found"

```
⚠ OpenCode CLI not found
  Install from: https://opencode.ai
```

**Solución:** Instala OpenCode desde [opencode.ai/download](https://opencode.ai/download)

### "Execution policy error" en Windows

```
.\setup.ps1 no se puede cargar porque la ejecución de scripts está deshabilitada
```

**Solución:**
```powershell
# Opción 1: Ejecutar con bypass
powershell -ExecutionPolicy Bypass -File setup.ps1

# Opción 2: Cambiar política (una sola vez, como Admin)
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### "No agents configured"

```
No previous agent configuration detected.
```

**Solución:**
```powershell
python main.py --setup
```

### "Invalid model IDs detected"

```
✖ Invalid model IDs detected:
    @orchestrator → opencode-go/old-model (not in registry)
```

**Solución:**
```powershell
python main.py --setup
# Esto regenera los agentes con modelos válidos
```

### "No logs found in .opencode/logs/"

```
No logs found in .opencode/logs/
Make sure OpenCode has been run in this project first.
```

**Solución:** Ejecuta OpenCode al menos una vez antes de `--summarize`:
```powershell
opencode --agent orchestrator
# Haz algo, luego sale
python main.py --summarize
```

### "Update failed" o "Failed to download release archive"

```
✖ Update failed: Failed to download release archive (HTTP 404).
```

**Solución:**
1. Verifica tu conexión a internet
2. Verifica que el tag/versión existe en GitHub: https://github.com/visualiaconsulting/oh-my-agents/releases
3. Si estás en modo git, asegúrate de que el remote `origin` apunta al repo correcto

### "Command not found: npx" (al usar MCP)

```
✖ Command not found: npx (FileNotFoundError)
```

**Solución:** Los templates MCP `filesystem` y `github` requieren Node.js y npx:
```powershell
# Windows
winget install OpenJS.NodeJS

# Verificar
node --version
npx --version
```

### "No MCP servers configured"

```
No MCP servers configured.
Add one with: python main.py --mcp-add <template_name>
```

**Solución:** Añade un servidor MCP:
```powershell
python main.py --mcp-add filesystem
python main.py --mcp-add sqlite
```

### "requests library not installed"

```
requests library not installed. Run: pip install requests
```

**Solución:**
```powershell
pip install requests
```

---

## 12. Quick Reference Card

### Los 15 Comandos Más Usados

| # | Comando | Qué hace |
|---|---------|----------|
| 1 | `opencode --agent orchestrator` | Inicia el orquestador |
| 2 | `python main.py --doctor` | Diagnóstico completo |
| 3 | `python main.py --check-updates` | Buscar actualizaciones |
| 4 | `python main.py --update` | Actualizar a la última versión |
| 5 | `python main.py --summarize` | Guarda bitácora de sesión |
| 6 | `python main.py --sessions` | Ver historial de sesiones |
| 7 | `python main.py --session-status` | Última sesión |
| 8 | `python main.py --skills-recommend` | Recomendar skills para el proyecto |
| 9 | `python main.py --skills-auto` | Instalar skills recomendadas |
| 10 | `python main.py --skills-search <q>` | Buscar skills |
| 11 | `python main.py --skills-install <id>` | Instalar skill |
| 12 | `python main.py --mcp-add <template>` | Añadir servidor MCP |
| 13 | `python main.py --mcp-status` | Estado de servidores MCP |
| 14 | `python main.py --install-global` | Instalar agentes globalmente |
| 15 | `python main.py --setup` | Reconfigurar agentes |

### Flujo de Trabajo Diario

```powershell
# Mañana
opencode --agent orchestrator    # Trabajar

# Al cerrar
python main.py --summarize       # Guardar bitácora

# Día siguiente
opencode --agent orchestrator    # Continuar donde lo dejaste
```

### Instalación en Nueva PC

```powershell
git clone https://github.com/visualiaconsulting/oh-my-agents.git
cd oh-my-agents
.\install.ps1
opencode --agent orchestrator
```

---

## Información del Proyecto

| Dato | Valor |
|------|-------|
| Repositorio | [visualiaconsulting/oh-my-agents](https://github.com/visualiaconsulting/oh-my-agents) |
| Versión | 1.5.0 |
| Licencia | MIT |
| Skills | [skills.sh](https://skills.sh) |
| OpenCode | [opencode.ai](https://opencode.ai) |
