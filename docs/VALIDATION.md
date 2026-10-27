# Estado de implementación y validación

Fecha: 27 de octubre de 2026. Versión del código: 3.0.0, preparada para revisión en GitHub.

## Implementado

- Cinco roles activos compartidos por Go y Codex: orchestrator, writer, coder, database y dashboard-designer.
- Codex con Astra coordinador, Luna para documentación, Sol para código/datos y Terra para diseño.
- Perfiles separados del catálogo; prompts completos; modelos personalizados conservados al reexportar.
- Exportación nativa moderna y modo compatible para clientes antiguos, con previsualización sin escrituras, respaldos, huellas y conflictos.
- Migración de los agentes Go originales conocidos a cinco definiciones, conservando personalizaciones ajenas al framework.
- Dos skills de diseño instaladas localmente desde revisiones fijadas y verificadas; instalador reproducible para otros proyectos.
- Metadatos de ejecución y continuidad SQLite con respaldo previo a migración y recuperación probada.
- Correcciones de CI, instalación Windows/Unix y transporte MCP con timeout/correlación de respuestas.
- Actualizador que conserva configuración, skills, instrucciones y estado local.
- Guías de instalación, uso, mantenimiento y tareas de evaluación.

## Verificaciones observadas

| Comprobación | Resultado |
| --- | --- |
| Suite completa en Windows, Python 3.11.9 | 266 pruebas pasaron, 2 omitidas |
| Ruff, reglas E/F/W con excepción E501 | Sin errores |
| `python scripts/validate_agents.py --require-codex` | Correcto |
| Reexportación Go y Codex en modo dry-run | Sin cambios pendientes |
| Compilación Python | Correcta |
| Sintaxis Bash mediante Git Bash | Correcta |
| Parser nativo de Codex CLI 0.130.0, modo legacy | Correcto; multi_agent habilitado |
| Dashboard Rich a 40 y 80 columnas | Renderizado en memoria, sin recortes en las muestras |
| Migración SQLite y recuperación de respaldo | Cubiertas por pruebas locales |
| Revisión de código con Astra | Tres regresiones de selección/persistencia corregidas y cubiertas |
| Documentación con Luna y revisión del dashboard con Terra | Realizadas dentro de esta sesión de trabajo |

Las dos omisiones locales corresponden al launcher Unix que se ejecuta en CI Linux y a la creación de un symlink que requiere privilegios no disponibles en Windows. La matriz de CI está configurada para Windows y Ubuntu, Python 3.9–3.12; su resultado se consulta en los checks del PR y [GitHub Actions](https://github.com/visualiaconsulting/oh-my-agents/actions).

El parser CLI se comprobó con un proyecto y un perfil temporales sin autenticación. El CLI 0.130.0 rechazó las claves modernas de agentes; por eso existe `--codex-compat legacy`. El perfil personal instalado también presentaba una opción de servicio incompatible con ese CLI; se dejó intacto. El repositorio conserva el formato moderno como predeterminado y documenta la conversión explícita.

## Límites de la evidencia

Las pruebas no ejecutan una carga de trabajo completa a través de los archivos nativos de un nuevo cliente autenticado. Los modelos utilizados por los colaboradores de esta sesión no demuestran que todos los modelos estén habilitados en otra cuenta o versión del cliente.

No se han medido ahorros, cuotas ni rendimiento comparativo de modelos. Los prompts de `examples/tasks.md` permiten realizar esas evaluaciones en un proyecto de prueba y registrar los hechos mediante `--record-session`. La captura automática de conversaciones Codex mediante SDK es una ampliación posterior; el registro de esta entrega es explícito.

## Reproducir

```sh
python -m pip install -r requirements.txt ruff
python -m pytest tests/ -q
python -m ruff check . --select E,F,W --ignore E501
python scripts/validate_agents.py --require-codex
python main.py --runtime codex --profile chatgpt --export --dry-run
python main.py --runtime opencode --profile go --export --dry-run
```

Para comprobar compatibilidad de un cliente antiguo, usa un proyecto de prueba y exporta con `--codex-compat legacy`. El cambio de modo conserva los modelos, crea respaldo y queda registrado en el manifiesto.
