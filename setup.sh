#!/usr/bin/env bash
# Run from the target project; paths resolve relative to this script.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

PYTHON_CMD=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && \
        "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 9))' 2>/dev/null; then
        PYTHON_CMD="$(command -v "$candidate")"
        break
    fi
done
if [ -z "$PYTHON_CMD" ]; then
    echo 'ERROR: Python 3.9+ not found. Install from https://python.org' >&2
    exit 1
fi

echo 'oh-my-agents - Setup'
"$PYTHON_CMD" --version
"$PYTHON_CMD" -m pip install -r "$SCRIPT_DIR/requirements.txt" --quiet

if [ "${1:-}" = '--install-global' ]; then
    # Installs the launcher only. It preserves the caller's project cwd.
    if [ -n "${OH_MY_AGENTS_BIN_DIR:-}" ]; then
        TARGET_DIR="$OH_MY_AGENTS_BIN_DIR"
        mkdir -p -- "$TARGET_DIR"
    elif [ -d /usr/local/bin ] && [ -w /usr/local/bin ]; then
        TARGET_DIR=/usr/local/bin
    else
        TARGET_DIR="$HOME/.local/bin"
        mkdir -p -- "$TARGET_DIR"
    fi
    TARGET="$TARGET_DIR/oh-my-agents"
    {
        printf '%s\n' '#!/usr/bin/env bash'
        printf 'exec %q %q "$@"\n' "$PYTHON_CMD" "$SCRIPT_DIR/main.py"
    } > "$TARGET"
    chmod +x -- "$TARGET"
    echo "Installed launcher at $TARGET (ensure $TARGET_DIR is on PATH)."
    exit 0
fi

# Forward explicit commands, including Codex runtime/profile/export flags.
if [ "$#" -gt 0 ]; then
    exec "$PYTHON_CMD" "$SCRIPT_DIR/main.py" "$@"
fi

"$PYTHON_CMD" "$SCRIPT_DIR/main.py"
read -r -p 'Enable OpenCode auto-session saving for this project? (Y/n): ' ENABLE_AUTO
if [ -z "$ENABLE_AUTO" ] || [[ "$ENABLE_AUTO" =~ ^[yY]$ ]]; then
    "$PYTHON_CMD" "$SCRIPT_DIR/main.py" --enable-auto-session
    "$PYTHON_CMD" "$SCRIPT_DIR/main.py" --inject-context
fi
echo 'Setup complete. Run python main.py --help for project commands.'
