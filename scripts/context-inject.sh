#!/bin/bash
# context-inject.sh — Context Injector for oh-my-agents (Linux/Mac)
# Run before `opencode` to inject session continuity context.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MAIN_PY="$PROJECT_ROOT/main.py"

if [ ! -f "$MAIN_PY" ]; then
    echo "[context-inject] ERROR: main.py not found at $MAIN_PY"
    exit 1
fi

# Step 1: Inject context and show banner
echo ""
python3 "$MAIN_PY" --inject-context 2>&1
echo ""

# Step 2: Check/ask for auto-session enablement
AUTO_FLAG="$PROJECT_ROOT/.opencode/.auto_session_enabled"
if [ ! -f "$AUTO_FLAG" ]; then
    read -p "Enable auto-session saving for this project? (y/N): " ENABLE
    if [ "$ENABLE" = "y" ] || [ "$ENABLE" = "Y" ]; then
        python3 "$MAIN_PY" --plan go 2>/dev/null
        mkdir -p "$PROJECT_ROOT/.opencode"
        echo "# Auto-session saving enabled" > "$AUTO_FLAG"
        echo "[context-inject] Auto-session enabled."
    fi
fi
