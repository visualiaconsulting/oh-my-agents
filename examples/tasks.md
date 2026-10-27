# Evaluar el equipo de cinco agentes

Ejecuta estas tareas en un proyecto de prueba con cambios revisables. Conserva la misma base y requisitos al comparar una sesión principal con el equipo. Los ejemplos son solicitudes, no resultados ya obtenidos.

## Código y pruebas

> Orquestador: pide a coder reproducir y corregir una regresión concreta del proyecto. Define el comportamiento esperado y las pruebas pertinentes. Revisa el diff y los resultados. Pide a writer un informe con causa, solución y limitaciones.

## Datos e integración

> Orquestador: encarga a database una migración aditiva sobre una copia local de SQLite, con respaldo y validación de filas existentes. Coder prepara la integración después de fijar el contrato. Revisa integridad y recuperación antes de cerrar.

## Diseño de dashboards

> Orquestador: pide a dashboard-designer inspeccionar el panel existente y mejorar su jerarquía, gráficos, legibilidad y estados vacíos. Debe usar las skills aplicables y respetar la tecnología actual. Coder se encarga de los cambios de integración en archivos distintos. Comprueba tamaños de pantalla y funcionamiento.

## Documentación e informes

> Orquestador: writer debe documentar los comandos realmente disponibles y producir un informe con fuentes y pendientes. Contrasta sus ejemplos con la ayuda del CLI antes de darlo por terminado.

## Tarea integrada

> Orquestador: añade una métrica al dashboard. Database define la consulta y su contrato; dashboard-designer define presentación y estados; coder integra y prueba. Cuando la implementación esté comprobada, writer actualiza el manual y resume el resultado. Asigna propietarios de archivos, secuencia dependencias y revisa la entrega completa.

## Qué registrar

Guarda objetivo, base Git, cambios, tiempo observado, revisiones necesarias, evidencia y comandos con sus estados reales. Registra el modelo solo si fue observado. El estado de una ejecución no terminada es partial. Usa el formato examples/session-record.json y guarda cada ejecución en una base de proyecto de prueba.

La disponibilidad de los cuatro modelos debe comprobarse en el cliente que realizará la tarea. Estas evaluaciones no requieren introducir claves de API en el repositorio.
