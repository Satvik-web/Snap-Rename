#!/bin/bash

# Snap Rename launcher (Linux with venv)

PYTHON_BIN="$HOME/.SnapRename/env/bin/python"
SCRIPT="$HOME/.SnapRename/main.py"

# Check venv python
if [ ! -f "$PYTHON_BIN" ]; then
    echo "Snap Rename venv not found at $PYTHON_BIN"
    exit 1
fi

# Check main script
if [ ! -f "$SCRIPT" ]; then
    echo "Snap Rename not found at $SCRIPT"
    exit 1
fi

# Run with all arguments
exec "$PYTHON_BIN" "$SCRIPT" "$@"
