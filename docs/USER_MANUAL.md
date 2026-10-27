# Manual de usuario

La versión 3 utiliza cinco agentes. La documentación vigente está en:

- [README](../README.md): inicio rápido, roles y perfiles.
- [Codex con ChatGPT](CODEX_CHATGPT.md): instalación, skills, comandos y sesiones.
- [Mantenimiento](MAINTENANCE.md): arquitectura, regeneración y recuperación.
- [Validación](VALIDATION.md): comprobaciones realizadas y límites observados.

## OpenCode Go

Desde un entorno Python 3.9+ con las dependencias de requirements.txt instaladas:

```sh
python main.py --runtime opencode --profile go --export --dry-run --dir PROJECT
python main.py --runtime opencode --profile go --export --dir PROJECT
```

Después abre OpenCode desde ese proyecto y utiliza orchestrator. También puedes
abrir python main.py para seleccionar proveedor, ver agentes configurados, sesiones
y herramientas. La exportación de proyecto es preferible para mantener separados
los modelos y la memoria de cada proyecto. --install-global instala explícitamente
los cinco agentes OpenCode en el perfil del usuario, con respaldo y conflictos.

LM Studio, Copilot y OpenRouter siguen disponibles desde el selector. Sus modelos
reales y credenciales se configuran en esos entornos; el archivo de perfil solo
contiene una asignación. Un intento cancelado o fallido conserva la selección previa.
