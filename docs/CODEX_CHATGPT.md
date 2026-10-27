# Codex con ChatGPT

Esta guía configura los agentes nativos del proyecto. Codex ejecuta las solicitudes con la sesión iniciada en la aplicación; el perfil no configura una API key ni prueba inicio de sesión o inferencia.

## Requisitos e instalación

Se admite Python 3.9 o posterior. Desde la raíz del repositorio, crea un entorno virtual e instala las dependencias:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

En macOS/Linux, usa `python3 -m venv .venv` y `source .venv/bin/activate`. Abre el proyecto en Codex y verifica que la aplicación tenga iniciada la cuenta de ChatGPT que quieres usar. No se necesita una clave de API para este perfil.

## Roles y modelos configurados

El catálogo contiene cinco roles. El orquestador es la sesión principal y puede coordinar hasta tres especialistas concurrentes; los cuatro especialistas son:

| Rol | Modelo del perfil | Esfuerzo |
| --- | --- | --- |
| `orchestrator` | `gpt-6-astra` | `medium` |
| `writer` | `gpt-6-luna` | `medium` |
| `coder` | `gpt-6.1-sol` | `medium` |
| `database` | `gpt-6.1-sol` | `high` |
| `dashboard-designer` | `gpt-6.1-terra` | `medium` |

Estas son asignaciones declaradas por el perfil, no una garantía de que cada modelo aparezca en la cuenta o esté disponible en la versión instalada de Codex. El exportador comprueba estructura y compatibilidad de archivos, no inicia sesión ni ejecuta modelos. Inicia sesión en Codex y revisa su selector de modelos.

## Exportación al proyecto

Primero inspecciona el proyecto objetivo. El modo de prueba solo informa qué haría y no crea carpetas ni escribe archivos:

```powershell
python main.py --runtime codex --profile chatgpt --export --dry-run --dir C:\ruta\al\proyecto
```

Revisa la lista de acciones, advertencias y conflictos. Si está correcta, exporta:

```powershell
python main.py --runtime codex --profile chatgpt --export --dir C:\ruta\al\proyecto
```

La configuración nativa se escribe bajo `.codex/`, y las instrucciones comunes en `AGENTS.md` (o el `agents.md` existente). La exportación conserva el texto ajeno al bloque administrado de instrucciones, detecta agentes personalizados modificados y no los sobrescribe silenciosamente. Los archivos previos administrados se respaldan bajo `.oh-my-agents/backups/`; revisa el reporte. No cambies la configuración global de Codex para activar este export: es configuración del proyecto. Codex puede pedir confiar en las instrucciones o configuración del proyecto; revisa los cambios antes de conceder confianza.

Opcionalmente, puedes pasar un inventario JSON de IDs de modelos conocido por ti para validar que los nombres del perfil estén en esa lista:

```powershell
python main.py --runtime codex --profile chatgpt --export --dry-run --available-models .\models.json --dir C:\ruta\al\proyecto
```

Un inventario suministrado no equivale a autenticación ni demuestra que un modelo pueda inferir. No hay consulta automática de acceso o cuotas de la cuenta.

## Compatibilidad con clientes Codex antiguos

El formato predeterminado es el de los clientes actuales. Si un CLI antiguo rechaza `agents.enabled` o `max_concurrent_threads_per_session`, exporta explícitamente el formato compatible, manteniendo los mismos modelos:

```sh
python main.py --runtime codex --profile chatgpt --export --codex-compat legacy --dry-run --dir PROJECT
python main.py --runtime codex --profile chatgpt --export --codex-compat legacy --dir PROJECT
```

El modo se conserva en el manifiesto para las siguientes exportaciones. `--codex-compat modern` vuelve al formato actual. El modo compatible se comprobó con el parser nativo de Codex CLI 0.130.0 en un perfil temporal aislado; esa comprobación no incluyó autenticación ni inferencia. Si el propio perfil global del cliente presenta errores, usa un cliente actualizado o corrige esa configuración desde sus ajustes. El exportador solo modifica el proyecto.

## Skills de diseño

La instalación descarga exclusivamente los archivos de las dos skills fijadas por revisión en `design-skills.lock.json`: `frontend-design` y `web-design-guidelines`. No ejecuta el instalador remoto. Primero previsualiza y luego instala:

```powershell
python main.py --runtime codex --install-design-skills --dry-run --dir C:\ruta\al\proyecto
python main.py --runtime codex --install-design-skills --dir C:\ruta\al\proyecto
```

Los archivos quedan en `.agents/skills/` dentro del proyecto, con un manifiesto de propiedad bajo `.oh-my-agents/`. Se verifican los hashes Git de los archivos remotos; si detecta una personalización o un cambio de checksum, se detiene y pide resolver el conflicto. Los archivos anteriores se respaldan antes de reemplazarse.

## Diagnóstico y sesiones

```powershell
python main.py --runtime codex --profile chatgpt --doctor --dir C:\ruta\al\proyecto
python main.py --sessions --dir C:\ruta\al\proyecto
python main.py --session-status --dir C:\ruta\al\proyecto
python main.py --session ID --dir C:\ruta\al\proyecto
python main.py --resume-context --dir C:\ruta\al\proyecto
```

El diagnóstico revisa CLI local, perfil, catálogo, archivos nativos y diferencias pendientes. No autentica la cuenta ni ejecuta inferencia. Las sesiones Codex se registran explícitamente; no se capturan automáticamente desde los logs de OpenCode. Usa un JSON con los resultados reales:

```json
{
  "summary": "Actualicé el manual y confirmé los comandos de exportación.",
  "runtime": "codex",
  "profile": "chatgpt",
  "role": "writer",
  "model": "",
  "status": "partial",
  "decisions": ["Mantener la exportación limitada al proyecto"],
  "pending_tasks": ["Verificar el flujo en otra instalación"],
  "evidence": ["Revisé la ayuda del CLI"],
  "checks": [
    {"name": "Ayuda del CLI", "status": "passed", "evidence": "python main.py --help"},
    {"name": "Prueba de inferencia", "status": "not_run"}
  ],
  "files_changed": ["docs/CODEX_CHATGPT.md"]
}
```

Guárdalo, por ejemplo, como `session.json` y registra el contenido:

```powershell
python main.py --runtime codex --profile chatgpt --record-session session.json --dir C:\ruta\al\proyecto
```

El `summary` es obligatorio. `status` acepta `partial`, `planned`, `running`, `completed`, `failed`, `blocked` o `cancelled`; si falta, se registra `partial`. Cada comprobación necesita `name` o `command` y, si no se especifica, su estado queda `not_run`. Los campos opcionales no suministrados quedan vacíos o en listas vacías. Deja `model` vacío si no observaste qué modelo se usó: el perfil seleccionado no prueba el modelo real. La continuidad resume evidencia y tareas pendientes registradas; no verifica su veracidad.

La base de sesiones existente sigue en `.opencode/project.db` por compatibilidad. No es un logger de Codex. Al actualizar una base antigua, SQLite hace una copia en el mismo directorio con nombre `project.pre-codex-v2-<marca-de-tiempo>-<id>.db` antes de añadir metadatos. Conserva esa copia hasta verificar la base migrada; la recuperación consiste en cerrar el CLI y restaurar la copia con SQLite cerrada. No borres archivos `-wal`/`-shm` mientras la base esté abierta.

## Referencias

- [Configuración oficial de subagentes](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Referencia oficial de configuración](https://learn.chatgpt.com/docs/config-file/config-reference)
- [Selección de modelos](https://developers.openai.com/api/docs/guides/model-selection)
- [Evidencia de esta entrega](VALIDATION.md)
