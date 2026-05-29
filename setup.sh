#!/bin/bash
# setup.sh — Bootstrap for Linux/Mac
# oh-my-agents — OpenCode Multi-Agent Framework

echo ""
echo "========================================"
echo "  oh-my-agents — Setup"
echo "========================================"
echo ""

# Change to the script's directory so relative paths work correctly
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Check Python
echo "[1/4] Checking Python..."
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "  ERROR: Python not found. Install Python 3.8+ from https://python.org"
        exit 1
    fi
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo "  OK: $PYTHON_VERSION"

# 2. Install dependencies
echo "[2/4] Installing dependencies..."
$PYTHON_CMD -m pip install -r "$SCRIPT_DIR"/requirements.txt --quiet
if [ $? -ne 0 ]; then
    echo "  ERROR: Failed to install dependencies"
    exit 1
fi
echo "  OK: Dependencies installed"

# 3. Check OpenCode CLI
echo "[3/4] Checking OpenCode CLI..."
if command -v opencode &> /dev/null; then
    echo "  OK: OpenCode CLI found"
else
    echo "  WARNING: OpenCode CLI not found"
    echo "  Install from: https://opencode.ai"
    echo ""
fi

# 4. Handle --uninstall flag (checked BEFORE running main.py)
if [ "$1" = "--uninstall" ]; then
    echo "========================================"
    echo "  oh-my-agents — Uninstall"
    echo "========================================"
    echo ""
    $PYTHON_CMD main.py --uninstall
    exit $?
fi

# 5. Handle --update flag (checked BEFORE running main.py)
if [ "$1" = "--update" ]; then
    echo "========================================"
    echo "  oh-my-agents — Update"
    echo "========================================"
    echo ""
    $PYTHON_CMD main.py --update
    exit $?
fi

# 6. Handle --install-global flag (checked BEFORE running main.py)
if [ "$1" = "--install-global" ]; then
    echo "[4/4] Installing globally..."
    TARGET="/usr/local/bin/oh-my-agents"

    # Fall back to ~/.local/bin if /usr/local/bin doesn't exist
    if [ ! -d "/usr/local/bin" ] && [ -d "$HOME/.local/bin" ]; then
        TARGET="$HOME/.local/bin/oh-my-agents"
    fi

    cat > "$TARGET" << GLOBALEOF
#!/bin/bash
cd "$SCRIPT_DIR" && $PYTHON_CMD main.py "\$@"
GLOBALEOF

    chmod +x "$TARGET"
    echo "  OK: 'oh-my-agents' installed at $TARGET"
    echo "  Usage: oh-my-agents"
    exit 0
fi

# 4. Run CLI (interactive mode)
echo "[4/4] Starting system..."
echo ""
$PYTHON_CMD main.py

# 5. Auto-session continuity
echo ""
echo "[5/5] Session continuity..."
echo ""
read -p "Enable auto-session saving? This keeps context between sessions. (Y/n): " ENABLE_AUTO
if [ "$ENABLE_AUTO" = "" ] || [ "$ENABLE_AUTO" = "y" ] || [ "$ENABLE_AUTO" = "Y" ]; then
    $PYTHON_CMD main.py --inject-context 2>/dev/null
    mkdir -p ".opencode"
    echo "# Auto-session saving enabled for $(basename $(pwd))" > ".opencode/.auto_session_enabled"
    echo "# Created: $(date '+%Y-%m-%d %H:%M:%S')" >> ".opencode/.auto_session_enabled"
    echo "  Auto-session enabled."
fi

# 6. Suggest global install for future use
echo ""
echo "========================================"
echo "  Tip: Install globally?"
echo "========================================"
echo ""
echo "Run the following to install oh-my-agents globally:"
echo ""
echo "  ./setup.sh --install-global"
echo ""
