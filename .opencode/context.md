# oh-my-agents — contexto del proyecto

Repositorio: https://github.com/visualiaconsulting/oh-my-agents

El sistema activo tiene exactamente cinco roles: orchestrator, writer, coder,
database y dashboard-designer. Las fuentes comunes viven en agents/catalog.yaml,
agents/prompts/ y profiles/; los adaptadores generan los formatos de Go y Codex.

## Responsabilidades

- orchestrator: coordinar tareas, asignar archivos, integrar y revisar resultados.
- writer: documentación, informes, resúmenes y continuidad.
- coder: implementación, depuración, pruebas, automatización y CI.
- database: esquemas, SQL, migraciones, integridad y rendimiento.
- dashboard-designer: diseño de interfaces, gráficos, accesibilidad y comprobación visual.

Investiga lo necesario para tu tarea, respeta el alcance y conserva las personalizaciones.
El orquestador delega trabajo independiente y secuencia dependencias. Cada especialista
entrega evidencia real y el resultado de las comprobaciones pertinentes. Un archivo
tiene un único autor activo. No añadas roles para tareas auxiliares.

Los modelos Go están en profiles/go.yaml. El perfil Codex con ChatGPT está en
profiles/codex-chatgpt.yaml y utiliza Astra, Sol, Terra y Luna. No deduzcas la
 disponibilidad real de un modelo ni cuotas de cuenta a partir de los archivos.

La continuidad conserva .opencode/project.db y las sesiones anteriores. El registro
Codex es explícito con --record-session; --resume-context recupera los hechos guardados.
Lee AGENTS.md, README.md y docs/CODEX_CHATGPT.md para instalación y mantenimiento.
