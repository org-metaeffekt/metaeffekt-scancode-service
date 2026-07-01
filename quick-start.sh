#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_NAME="scancode-extensions"
VENV_PATH="$SCRIPT_DIR/$VENV_NAME"
DATA_DIR="$SCRIPT_DIR/.scancode-service"

# Detect python command (python3 preferred, then python)
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &> /dev/null; then
        PYTHON="$cmd"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "Error: Neither python3 nor python found. Please install Python 3."
    exit 1
fi

"$PYTHON" -m pip install build --quiet
"$PYTHON" -m build

# Dynamically resolve the .whl file from the dist directory
WHL_FILE=$(ls "$SCRIPT_DIR/dist"/scancode_service-*.whl 2>/dev/null | head -1)
if [ -z "$WHL_FILE" ] || [ ! -f "$WHL_FILE" ]; then
    echo "Error: No .whl file found in $SCRIPT_DIR/dist/"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_PATH" ]; then
    "$PYTHON" -m venv "$VENV_NAME"
fi

. "$VENV_PATH/bin/activate"
"$PYTHON" -m pip install "$WHL_FILE"

# Create local data directories (project-local instead of ~/scancode-service/
# to avoid needing broad permissions in the home directory)
mkdir -p "$DATA_DIR"/{temp,cache,lcache}
chmod 777 "$DATA_DIR" "$DATA_DIR"/{temp,cache,lcache}

export SCANCODE_TEMP="$DATA_DIR/temp"
export SCANCODE_CACHE="$DATA_DIR/cache"
export SCANCODE_LICENSE_INDEX_CACHE="$DATA_DIR/lcache"

exec scancode-service
