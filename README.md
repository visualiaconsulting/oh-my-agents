# oh-my-agents

Cinco agentes para trabajar desde **Codex con tu cuenta de ChatGPT**, con soporte de **OpenCode Go** como base alternativa.

El orquestador entiende el objetivo, delega a cuatro especialistas, integra los cambios y revisa las comprobaciones. Las capacidades nuevas se incorporan mediante skills dentro de estos cinco roles.

| Agente | Modelo en Codex | Trabajo |
| --- | --- | --- |
| Orquestador | Astra — `gpt-6-astra` | Planificar, coordinar, revisar e integrar |
| Documentación e informes | Luna — `gpt-6-luna` | Manuales, informes, resúmenes y bitácora |
| Código | Sol — `gpt-6.1-sol` | Programación, APIs, pruebas, depuración y automatización |
| Bases de datos | Sol — `gpt-6.1-sol` | Modelado, SQL, migraciones, integridad y rendimiento |
| Diseño de dashboards | Terra — `gpt-6.1-terra` | UX/UI, gráficos, componentes y accesibilidad |

Un máximo configurado de tres especialistas concurrentes permite ejecutar al cuarto en otra etapa. Se respeta cualquier límite menor del entorno. Los permisos efectivos pertenecen a Codex y a las herramientas de la sesión.

## Empezar con Codex y ChatGPT

Requiere Python 3.9+, las dependencias del proyecto y un cliente Codex compatible. El acceso a cada modelo depende de tu cuenta y del cliente. Este perfil no utiliza una API key.

```sh
git clone https://github.com/visualiaconsulting/oh-my-agents.git
cd oh-my-agents
python -m venv .venv
```

Activa el entorno con `.venv\\Scripts\\Activate.ps1` en PowerShell o `source .venv/bin/activate` en macOS/Linux. Después:

```sh
python -m pip install -r requirements.txt
python main.py --runtime codex --profile chatgpt --export --dry-run
python main.py --runtime codex --profile chatgpt --export
python main.py --runtime codex --install-design-skills
python main.py --runtime codex --doctor
```

Abre el proyecto en Codex, inicia sesión con ChatGPT, revisa la confianza del proyecto y confirma los modelos en el selector. Las definiciones nativas ya están incluidas en este repositorio; la exportación también sirve para instalar el equipo en otros proyectos:

```sh
python main.py --runtime codex --profile chatgpt --export --dry-run --dir /ruta/al/proyecto
python main.py --runtime codex --profile chatgpt --export --dir /ruta/al/proyecto
python main.py --runtime codex --install-design-skills --dir /ruta/al/proyecto
```

En Windows usa una ruta como `"C:\\Mis proyectos\\Mi app"`. Los scripts `setup.ps1` y `setup.sh` aceptan estos argumentos y conservan el directorio desde el que los ejecutas.

Ejemplo de solicitud al orquestador:

> Mejora el panel de ventas. Delega el diseño a dashboard-designer, la consulta agregada a database, la integración y pruebas a coder y el informe final a writer. Asigna archivos distintos, espera los resultados y revisa el funcionamiento antes de cerrar.

## Skills de diseño

El instalador descarga `frontend-design` de Anthropic y `web-design-guidelines` de Vercel desde las revisiones fijadas en `design-skills.lock.json`. Verifica sus hashes Git, instala texto en `.agents/skills/` y conserva las personalizaciones. No ejecuta instaladores remotos.

Las skills web se aplican a los dashboards web de tus proyectos. El dashboard administrativo de este repositorio sigue siendo una interfaz de terminal.

## OpenCode Go

```sh
python main.py --runtime opencode --profile go --export --dry-run --dir /ruta/al/proyecto
python main.py --runtime opencode --profile go --export --dir /ruta/al/proyecto
opencode --agent orchestrator
```

El catálogo Go también tiene cinco roles. Los archivos originales conocidos de los 21 agentes se archivan con copia de seguridad al exportar; los archivos personalizados se conservan y se reportan como advertencia o conflicto. Las consultas con nombres de roles antiguos siguen disponibles como aliases de compatibilidad, sin crear agentes adicionales.

Las integraciones existentes con LM Studio, Copilot y OpenRouter conservan su selector en `python main.py`. Los modelos elegidos se guardan por perfil. LM Studio requiere modelos instalados reales; los IDs de ejemplo del perfil no prueban disponibilidad. La instalación global de OpenCode es explícita mediante `--install-global`.

## Sesiones y continuidad

Codex se registra explícitamente mediante un archivo JSON con resultados observados. Puedes copiar `examples/session-record.json`, editarlo con lo ocurrido y ejecutar:

```sh
python main.py --runtime codex --record-session session.json --dir /ruta/al/proyecto
python main.py --sessions --dir /ruta/al/proyecto
python main.py --session-status --dir /ruta/al/proyecto
python main.py --resume-context --dir /ruta/al/proyecto
```

El modelo no se infiere del perfil; si se desconoce, queda vacío. El estado por defecto es `partial`. La base existente permanece en `.opencode/project.db`, con migración respaldada e idempotente. El logger de OpenCode continúa separado del flujo Codex.

## Configuración y mantenimiento

- Roles y contratos: `agents/catalog.yaml` y `agents/prompts/`.
- Modelos: `profiles/codex-chatgpt.yaml`, `profiles/go.yaml` y perfiles adicionales.
- Salida Codex: `.codex/config.toml`, cuatro archivos en `.codex/agents/` y el bloque administrado en `AGENTS.md`.
- Salida Go: cinco archivos en `.opencode/agents/` y `.opencode/plan.json`.
- Propiedad de archivos: `.oh-my-agents/exports/`; copias locales: `.oh-my-agents/backups/`.

Edita las fuentes canónicas y vuelve a exportar. El modo `--dry-run` no escribe archivos. Las modificaciones de agentes generados se detectan antes de sobrescribirlos. Las actualizaciones de código preservan configuraciones locales y requieren una exportación posterior explícita para actualizar los agentes.

## Comprobaciones

```sh
python -m pip install ruff
python -m pytest tests/ -q
python -m ruff check . --select E,F,W --ignore E501
python scripts/validate_agents.py --require-codex
```

CI ejecuta la suite en Windows y Ubuntu con Python 3.9–3.12. Las pruebas de integración son locales, con procesos simulados y proyectos temporales; no consumen llamadas de modelos.

## Documentación

- [Guía de instalación y uso](docs/CODEX_CHATGPT.md)
- [Mantenimiento, arquitectura y recuperación](docs/MAINTENANCE.md)
- [Estado de implementación y validación](docs/VALIDATION.md)
- [Tareas de evaluación reproducibles](examples/tasks.md)
- [Plan acordado](docs/PLAN_CODEX_CHATGPT.md)

[Repositorio de VisualIA Consulting](https://github.com/visualiaconsulting/oh-my-agents).
