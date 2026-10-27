# Mantenimiento de oh-my-agents

Esta guía describe dónde cambiar el comportamiento compartido, cómo regenerar exportaciones nativas y qué revisar al actualizar una instalación.

## Fuentes de verdad

- `agents/catalog.yaml`: los cinco roles, sus descripciones y las declaraciones de permisos utilizadas por el sistema.
- `agents/prompts/`: instrucciones canónicas por rol. Edita aquí los prompts, no en los archivos nativos generados.
- `profiles/`: asignaciones de modelos y ajustes por runtime. `profiles/codex-chatgpt.yaml` declara el perfil ChatGPT; no prueba disponibilidad en una cuenta.
- `adapters/codex.py` y `adapters/opencode.py`: generación de formatos nativos. `adapters/__init__.py` aplica exportación, propiedad, detección de conflictos, copias de seguridad y rollback.
- `runtime_cli.py` y `main.py`: comandos, selección de runtime, diagnóstico y registro explícito de sesiones.
- `design_skills.py` y `design-skills.lock.json`: instalación de skills de diseño con revisiones y hashes fijados.
- `project_db.py`: esquema SQLite y migraciones de continuidad. La ubicación actual de la base es `.opencode/project.db`.

No añadas roles: amplía el prompt, contrato o skill del rol existente que corresponda. Los permisos nativos efectivos pertenecen al host; las instrucciones de los agentes no aíslan procesos ni cambian los permisos del usuario.

## Cambios de prompts y exportación

1. Edita una sola fuente canónica de prompt por vez en `agents/prompts/` y revisa las instrucciones comunes de `AGENTS.md` si aplica.
2. Ejecuta primero un dry run en un proyecto de prueba o destino elegido:

   ```sh
   python main.py --runtime codex --profile chatgpt --export --dry-run --dir PROJECT
   ```

3. Revisa diferencias, warnings y conflictos. Después ejecuta la misma orden sin `--dry-run`.
4. Revisa los archivos nativos resultantes y el backup informado en `.oh-my-agents/backups/`.
5. Regenera también Go con `python main.py --runtime opencode --profile go --export` cuando cambien fuentes comunes. Verifica la salida reproducible y ejecuta `python scripts/validate_agents.py --require-codex` antes de integrar.

No edites directamente `.codex/agents/*.toml` o el bloque administrado `oh-my-agents` en `AGENTS.md`: los cambios manuales allí se perderán o detectarán como conflicto. Las instrucciones previas al bloque y posteriores al bloque de `AGENTS.md` se conservan.

La exportación usa `.oh-my-agents/exports/<runtime>.json` como manifiesto de hashes administrados. Las definiciones de agente modificadas fuera del hash registrado son conflicto; resuelve el conflicto revisando y guardando cualquier personalización antes de regenerar. Registros personalizados de Codex fuera del catálogo se conservan y se reportan. Los agentes históricos conocidos de OpenCode pueden archivarse por huella; los archivos no reconocidos se conservan.

El manifiesto Codex conserva `codex_compat`: `modern` usa el esquema actual; `legacy` utiliza las claves aceptadas por CLI 0.130.0. Cambia de modo mediante `--codex-compat` con una previsualización antes de aplicar. La conversión respalda la configuración y mantiene los IDs de modelo. Los modelos personalizados de OpenCode también se conservan al reexportar el mismo perfil.

## Actualización de la instalación

El actualizador de código y la exportación del proyecto son pasos distintos. Después de actualizar el repositorio o paquete, revisa los cambios y vuelve a ejecutar el dry run en cada proyecto. Aplica explícitamente `--export` para que el proyecto reciba las versiones actuales de los prompts y perfiles. La actualización no implica que la configuración de todos los proyectos se haya regenerado.

Para instalar las skills fijadas, repite `python main.py --runtime codex --install-design-skills --dry-run --dir PROJECT` y luego la misma orden sin `--dry-run`. Comprueba manifiesto y hashes. Si una skill local se personalizó, la instalación detecta el conflicto y no la reemplaza; guarda la personalización aparte y resuelve deliberadamente el conflicto.

## Continuidad y SQLite

`--record-session` guarda los resultados proporcionados en JSON; no recoge automáticamente el transcript de Codex. Registra únicamente evidencia observada, usa `partial` cuando la tarea no esté completa y deja `model` vacío si se desconoce. Un check sin estado explícito queda `not_run`. `--resume-context`, `--sessions`, `--session-status` y `--session ID` consultan los registros disponibles; el contexto histórico se presenta como datos, no como instrucciones.

La base `.opencode/project.db` tiene `project_meta`, `sessions`, `files_changed`, `errors` y `commands`. La versión de esquema actual es 2. `sessions` mantiene los campos anteriores de resumen, duración, logs y tareas pendientes, además de `runtime`, `profile`, `model`, `role`, `task_id`, `parent_task_id`, `status`, `evidence` y `checks`. Migrar un esquema anterior agrega las columnas sin copiar ni eliminar registros y crea antes una copia online SQLite en el directorio de la base. La copia incluye transacciones confirmadas del WAL. No reemplaza una copia de recuperación anterior.

Antes de una migración en producción, conserva también una copia externa de `.opencode/`. Si la migración falla, guarda el archivo nuevo para diagnóstico, cierra los procesos que usan la base y restaura la copia `project.pre-codex-v2-*.db` con SQLite sin conexiones abiertas. Asegúrate de que la restauración esté en `.opencode/project.db`; después verifica sesiones y relaciones antes de reanudar escrituras.

## Verificación y publicación

Ejecuta las comprobaciones definidas por el proyecto y reporta sus resultados reales:

```sh
python -m pytest tests/ -q
python -m ruff check . --select E,F,W --ignore E501
python scripts/validate_agents.py
```

La validación de configuración y las pruebas locales no demuestran inicio de sesión de ChatGPT, acceso a modelos, cuotas ni una inferencia real. Para afirmar esos resultados se necesita evidencia directa del cliente y de una ejecución observada. Mantén vacíos los modelos desconocidos en registros de sesión y documentación.
