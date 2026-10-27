# Plan de evolución de oh-my-agents: Go + Codex con ChatGPT

Fecha: 27 de octubre de 2026.

Estado: planificación aprobada, implementada en la rama `codex/chatgpt-five-agents`. Los cinco bloques se agrupan en una entrega revisable. Consulta [VALIDATION.md](VALIDATION.md) para las comprobaciones y limitaciones observadas; las secciones siguientes conservan el plan acordado.

## Objetivo y alcance

Adaptar el sistema actual de OpenCode Go para trabajar también en Codex con la cuenta de ChatGPT del usuario, usando Sol, Terra, Luna y Astra. Consolidar el catálogo activo en cinco agentes: orquestador, documentación e informes, código, bases de datos y diseño de dashboards. Reutilizar la coordinación, el historial y la continuidad del proyecto.

La primera versión usará el entorno y la autenticación de Codex. El desarrollo de una aplicación independiente con la API queda para una ampliación posterior.

## Base revisada

Repositorio: https://github.com/visualiaconsulting/oh-my-agents

Referencia de la revisión anterior: `f72fafafd32e224fa15b9686d5d43ae5743c58d1`. Antes de implementar, volver a comprobar la rama principal y los cambios posteriores.

- `plan_manager.py`: 21 roles, modelos por plan, permisos, persistencia del plan y generación de agentes.
- `.opencode/agents/`: instrucciones y configuración de especialistas.
- `main.py` y `cli/`: selección de proveedor, instalación, diagnóstico y dashboard.
- `project_db.py`, `session_manager.py` y `continuity.py`: sesiones y reentrada al proyecto.
- `wrappers/opencode_logger.py`: captura de ejecución ligada actualmente a OpenCode.

Hay dos puntos adicionales que debe resolver el diseño: el generador reemplaza el contenido de los agentes por instrucciones mínimas y el constructor de `PlanManager` mezcla proveedor, perfil y formato de salida.

## Decisiones de diseño

1. Mantener una única definición de cada rol y producir configuraciones para cada entorno.
2. Separar entorno de ejecución, perfil de modelos y política de delegación. Go es un perfil de OpenCode; Codex necesita su propio adaptador.
3. Definir exactamente cinco roles activos: un orquestador y cuatro especialistas. Los antiguos roles se consolidan en ellos; la hoja de ruta no contempla volver a ampliar el catálogo a 21 agentes.
4. Usar inicialmente un coordinador y hasta tres especialistas simultáneos, sujeto al límite efectivo del cliente.
5. Limitar la delegación inicial a un nivel. Los especialistas solicitan nuevas subtareas al coordinador.
6. Activar los modelos mediante identificadores explícitos y validación de disponibilidad. Un modelo ausente produce diagnóstico; las alternativas deberán estar configuradas y quedar registradas.

Codex admite agentes de proyecto en `.codex/agents/*.toml` y ajustes generales en `.codex/config.toml`. Las instrucciones comunes se llevarán a `AGENTS.md`. La configuración propuesta se validará con la versión instalada antes de adoptarla. [Documentación de subagentes](https://learn.chatgpt.com/docs/agent-configuration/subagents).

## Los cinco agentes

Esta tabla es una propuesta de enrutamiento que debe evaluarse; no es una clasificación absoluta de calidad por especialidad.

| Agente | Modelo principal | Responsabilidad | Razonamiento inicial |
| --- | --- | --- | --- |
| `orchestrator` | Astra — `gpt-6-astra` | Entender el objetivo, dividir trabajo, coordinar, revisar e integrar | `medium`; `high` en problemas difíciles |
| `writer` | Luna — `gpt-6-luna` | Documentación, informes, manuales, resúmenes y bitácora | `medium` |
| `coder` | Sol — `gpt-6.1-sol` | Código, APIs, depuración, pruebas, automatización y CI | `medium`; `high` en cambios complejos |
| `database` | Sol — `gpt-6.1-sol` | Modelado, SQL, migraciones, integridad y rendimiento | `high` |
| `dashboard-designer` | Terra — `gpt-6.1-terra` | UX/UI de dashboards, jerarquía visual, componentes, gráficos y accesibilidad | `medium` |

La selección sigue las orientaciones generales de OpenAI: Sol para trabajo complejo equilibrado, Terra para tareas visuales y acotadas, Luna para trabajo delimitado y Astra para análisis exigente. Los niveles finales se elegirán con pruebas representativas. [Selección de modelos](https://developers.openai.com/api/docs/guides/model-selection).

El orquestador es la sesión principal; los otros cuatro roles son subagentes. La concurrencia limita cuántos trabajan simultáneamente, no cuántos roles existen. Con un máximo de tres especialistas simultáneos, el cuarto espera o se ejecuta en otra etapa.

### Consolidación del catálogo actual

- `writer` absorbe documentación, resúmenes, informes y notas de versión.
- `coder` absorbe programación, formatos estructurados, APIs, pruebas, DevOps, automatización, Git y cambios de ML cuando formen parte del código.
- `database` absorbe arquitectura de datos, consultas, migraciones y análisis de rendimiento.
- `dashboard-designer` absorbe diseño frontend y visualización de datos; coordina con `coder` los contratos e integraciones.
- `orchestrator` absorbe arquitectura general, investigación transversal, revisión de código, seguridad y validación final.

Cada especialista investiga su dominio y verifica su trabajo. El orquestador revisa cambios sensibles y evidencia de pruebas. Si una tarea supera al especialista, se devuelve al orquestador con lo probado y la decisión pendiente. Elevar el razonamiento o reasignar una tarea no crea un nuevo rol.

### Contratos de salida

- `writer`: documento o informe con fuentes, hechos comprobados, conclusiones y pendientes diferenciados.
- `coder`: cambios de código, pruebas pertinentes y explicación breve del resultado.
- `database`: esquema o consulta, migración cuando corresponda, validación de integridad y recuperación prevista.
- `dashboard-designer`: cambios visuales implementados, estados de carga/vacío/error, adaptación de tamaños y evidencia visual cuando haya herramientas disponibles.
- `orchestrator`: resultado integrado, comprobaciones realizadas y pendientes reales.

## Skills del agente de diseño

Selección inicial revisada en la red el 27 de octubre de 2026:

| Skill | Fuente | Uso previsto | Adopción observada |
| --- | --- | --- | --- |
| `frontend-design` | Anthropic, `anthropics/skills` | Dirección visual, tipografía, composición y diseño específico del producto | Aproximadamente 1 millón de instalaciones en skills.sh |
| `web-design-guidelines` | Vercel, `vercel-labs/agent-skills` | Revisión de interfaz, accesibilidad y UX | Aproximadamente 792 mil instalaciones en skills.sh |

Fuentes consultadas: [frontend-design](https://www.skills.sh/anthropics/skills/frontend-design), [web-design-guidelines](https://www.skills.sh/vercel-labs/agent-skills/web-design-guidelines). También se leyeron sus archivos `SKILL.md` en los repositorios oficiales; estos superaban las 184 mil y 33 mil estrellas respectivamente al revisarlos. Las cifras son una señal de adopción, no una garantía de calidad.

Comandos de referencia para la fase de implementación; no ejecutados al redactar el plan:

```sh
npx skills add https://github.com/anthropics/skills --skill frontend-design
npx skills add https://github.com/vercel-labs/agent-skills --skill web-design-guidelines
```

La instalación se dirigirá al proyecto y al entorno Codex. Se registrarán fuente, revisión y licencia; se aplicará cada skill solo cuando corresponda al proyecto. Se aprovecharán `dashboard-builder` y `tailwindcss` ya disponibles cuando coincidan con la tecnología utilizada. El catálogo de skills no debe convertirse en una lista de agentes adicionales.

Flujo del diseñador: inspeccionar la interfaz y sus usuarios, definir el lenguaje visual, implementar componentes y gráficos, comprobar interacción y tamaños de pantalla, revisar accesibilidad y entregar evidencia. Para un dashboard existente se respetará su sistema de diseño salvo que la tarea solicite rediseñarlo.

El dashboard de administración actual del repositorio es una interfaz de terminal. Las skills web se orientan a los dashboards web de los proyectos atendidos; convertir la administración del framework en una aplicación web sería un alcance adicional.

## Flujo de trabajo

1. El coordinador identifica el objetivo, las restricciones y cómo comprobar el resultado.
2. Divide únicamente el trabajo independiente y asigna a cada especialista una salida concreta.
3. Cada asignación especifica archivos permitidos, dependencias, modelo, esfuerzo y pruebas esperadas.
4. Los especialistas devuelven evidencia, cambios y pendientes al coordinador.
5. El coordinador integra y revisa los resultados; puede pedir comprobaciones cruzadas entre los cuatro especialistas según su dominio.
6. Se ejecutan las verificaciones necesarias, se conserva el estado y se presenta el resultado.

Reglas operativas propuestas:

- Una tarea pequeña puede resolverse en la sesión principal.
- Las tareas independientes se ejecutan en paralelo. Los cambios dependientes se secuencian.
- Un archivo tiene un único autor activo. Si es imprescindible modificarlo desde varias tareas, se serializan o se usan worktrees con integración posterior.
- El orquestador documenta los hallazgos de revisión con archivo, línea, impacto y reproducción.
- Ante un bloqueo, el especialista informa lo probado y solicita ayuda; no repite indefinidamente el mismo intento.
- Astra coordina desde la sesión principal; los especialistas reciben contexto acotado y una condición de salida.
- El coordinador conserva la responsabilidad de completar y verificar el trabajo.

Los subagentes heredan los permisos de la sesión principal; escribir «solo lectura» en un prompt no crea aislamiento. Las reglas de conducta y los controles efectivos se documentarán por separado. [Permisos de subagentes](https://learn.chatgpt.com/docs/agent-configuration/subagents#approvals-and-sandbox-controls).

## Estructura propuesta

```text
AGENTS.md                         # Reglas comunes y delegación autorizada
agents/
  catalog.yaml                    # Exactamente cinco roles y sus contratos
  prompts/                        # Una definición por cada uno de los cinco roles
profiles/
  go.yaml                         # Modelos actuales de OpenCode Go
  codex-chatgpt.yaml               # Sol, Terra, Luna y Astra
adapters/
  opencode.py                     # Exportación al formato de OpenCode
  codex.py                        # Exportación al formato de Codex
.codex/
  config.toml                     # Configuración generada y revisable
  agents/                         # Cuatro especialistas TOML generados
docs/
  CODEX_CHATGPT.md                 # Instalación, uso y diagnóstico
tests/
  test_agent_exports.py
  test_codex_profile.py
  test_continuity_migration.py
```

Los nombres de archivos nuevos son propuestos. El comando de exportación tendrá modo de previsualización, copia de seguridad y combinación de configuración para conservar personalizaciones.

## Plan de actualización en GitHub

### PR 1 — Recuperar una base verificable

Rama propuesta: `codex/fix-bootstrap-ci`.

- Corregir el YAML de CI y retirar el Python incrustado frágil a un script.
- Separar ejecutable y argumentos del lanzador de Python en Windows.
- Conservar el directorio del proyecto en el wrapper global de Unix.
- Corregir la invocación a `--inject-context` y comprobar el resultado antes de anunciar activación.
- Registrar el defecto de timeout y correlación de respuestas MCP; repararlo antes de anunciar soporte MCP en el perfil Codex, en un cambio independiente si fuera necesario.

Aceptación: workflow válido y comprobaciones de instalación que no modifiquen el entorno global de pruebas. Suite existente y lint pasando, o fallos anteriores reproducidos y resueltos de forma explícita.

### PR 2 — Catálogo y perfiles reutilizables

Rama propuesta: `codex/agent-catalog-profiles`.

- Consolidar los 21 roles anteriores en los cinco roles acordados, conservando sus responsabilidades útiles.
- Extraer las asignaciones Go y Codex a perfiles del catálogo reducido. Usar modelos Go ya registrados y validar su disponibilidad al implementar.
- Conservar sesiones y configuración previa con una migración revisable. Los archivos antiguos generados se retirarán o archivarán para que no aparezcan como agentes activos; preservar personalizaciones ajenas al generador.
- Incorporar el perfil Codex con los cuatro modelos y el esfuerzo por rol.
- Evitar que la regeneración elimine instrucciones especializadas.
- Hacer que `PlanManager` use el catálogo y delegue la exportación al adaptador.
- Añadir diagnóstico de roles desconocidos, modelos ausentes y opciones incompatibles.

Aceptación: el catálogo contiene exactamente cinco roles; cada perfil asigna un modelo a cada rol; exportar dos veces produce el mismo resultado; Go sigue siendo utilizable con el catálogo reducido.

### PR 3 — MVP de agentes nativos en Codex

Rama propuesta: `codex/chatgpt-agents-mvp`.

- Crear el adaptador Codex, `AGENTS.md` y cuatro especialistas: `writer`, `coder`, `database` y `dashboard-designer`.
- Configurar Astra para la sesión coordinadora, Sol para código y datos, Terra para diseño y Luna para documentación.
- Incorporar las skills de diseño seleccionadas al flujo del especialista y comprobar que el entorno puede encontrarlas.
- Incorporar los contratos de tarea, resultado y revisión al contenido de los agentes.
- Proponer un máximo inicial de tres especialistas simultáneos.
- Adaptar dashboard, ayuda y diagnóstico para seleccionar entorno y perfil.
- Añadir una exportación revisable: propuesta de comando `python main.py --runtime codex --profile chatgpt --export --dry-run`.
- Documentar cómo abrir el proyecto en Codex y solicitar una tarea con delegación.

Aceptación: Astra coordina una tarea real que incluye un informe con Luna, un cambio de código con Sol, una consulta o migración con Sol y una mejora visual con Terra. Los especialistas entregan evidencia y el orquestador verifica el resultado integrado. Ejecutar por lotes si la concurrencia disponible es menor. La selección debe verificarse en el registro o interfaz que exponga el cliente.

### PR 4 — Continuidad y trazabilidad

Rama propuesta: `codex/agent-continuity`.

- Añadir al esquema de SQLite: entorno, perfil, modelo, rol, tarea padre, estado, evidencias y comprobaciones.
- Migrar sin pérdida las sesiones existentes; comprobar copia de seguridad y recuperación.
- Mantener temporalmente la base en su ubicación actual para evitar una migración doble.
- Guardar un resumen compacto: objetivo, decisiones, cambios, pruebas, bloqueos y siguiente acción.
- La versión inicial admitirá registrar el cierre de sesión mediante el CLI; no prometer captura automática a partir de los logs de OpenCode.
- Evaluar el SDK oficial de Codex para ejecución y captura programática si la automatización de sesiones resulta necesaria.

El SDK de Python permite controlar y reanudar sesiones locales de Codex. Se tratará como dependencia opcional de una integración posterior, con el requisito de Python correspondiente, sin elevar accidentalmente los requisitos del perfil Go. [Codex SDK](https://learn.chatgpt.com/docs/codex-sdk).

Aceptación: cerrar una tarea, reabrir el proyecto y recuperar decisiones y pendientes. Los registros parciales deben indicarse como tales; nunca inventar métricas o pruebas.

### PR 5 — Evaluación y publicación

Rama propuesta: `codex/evals-release`.

- Evaluar una corrección de backend, un cambio visual, documentación, una regresión de pruebas y una decisión de arquitectura.
- Comparar una sesión de Astra sin delegación con Astra coordinando a los cuatro especialistas sobre las mismas tareas.
- Medir resultado correcto, pruebas, tiempo, retrabajo y uso cuando el cliente lo exponga.
- Ajustar enrutamiento y concurrencia a partir de evidencia.
- Ajustar instrucciones, skills y asignaciones dentro de los cinco roles acordados.
- Actualizar README, manual, ejemplos, compatibilidad y notas de versión.

Aceptación: instalaciones reproducibles en Windows y Linux; ejemplo completo con cinco roles y cuatro modelos; continuidad comprobada; comportamiento de Go validado tras la consolidación. La publicación de una versión se realizará después de integrar los PRs aprobados y confirmar la versión que corresponda.

## Compatibilidad y límites

- Comprobar disponibilidad de modelos en la cuenta y versión del cliente durante la instalación. No convertir los límites de Go en cuotas ficticias de ChatGPT.
- El cliente nativo administra las llamadas al modelo. No copiar a Codex el campo `temperature: 0.2` del exportador OpenCode. Si se implementa una integración API futura, validar sus parámetros por modelo y nivel de razonamiento. [Migración GPT-6](https://developers.openai.com/api/docs/guides/latest-model#migration-quickstart).
- Traducir las instrucciones actuales de eficiencia: retirar límites arbitrarios de dos líneas, diez turnos y la prohibición de explicar planes. Priorizar contexto suficiente, delegación útil y comprobación del resultado.
- Definir timeouts y reintentos del componente de ejecución solo donde exista control programático; un archivo de instrucciones no garantiza su cumplimiento.
- Ofrecer un modo de diagnóstico para comprobar formatos, modelos y herramientas antes de ejecutar tareas reales.

## Resultado esperado

El repositorio reutiliza la base del sistema Go y añade un perfil Codex instalable y verificable. El catálogo activo queda reducido a cinco agentes. El usuario trabaja desde Codex con su cuenta de ChatGPT; Astra coordina cuatro especialistas, revisa los resultados y conserva el contexto del proyecto.

La primera entrega implementable es PR 1 + PR 2 + PR 3. La continuidad avanzada se incorpora después de comprobar que la delegación nativa funciona en el entorno del usuario. La evolución posterior añade capacidades mediante skills e instrucciones dentro de los cinco roles existentes.
