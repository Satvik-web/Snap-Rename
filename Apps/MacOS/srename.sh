#!/bin/bash

CONFIG="$HOME/.srenameinfo"
APP="/Applications/Snap Rename.app/Contents/Resources/main.py"

# ─────────────────────────────────────────────
# Get Python path from config
# ─────────────────────────────────────────────
if [ -f "$CONFIG" ]; then
    PYTHON=$(cat "$CONFIG")
else
    echo "❌ Python config not found."
    echo "👉 Run installer again."
    exit 1
fi

# ─────────────────────────────────────────────
# Validate Python path
# ─────────────────────────────────────────────
if [ ! -x "$PYTHON" ]; then
    echo "❌ Invalid Python path in ~/.srenameinfo"
    echo "👉 Run installer again."
    exit 1
fi

# ─────────────────────────────────────────────
# Validate app exists
# ─────────────────────────────────────────────
if [ ! -f "$APP" ]; then
    echo "❌ Snap Rename app not found in /Applications"
    echo "👉 Reinstall the app."
    exit 1
fi

# ─────────────────────────────────────────────
# Run app
# ─────────────────────────────────────────────
cd "/Applications/Snap Rename.app/Contents/Resources" || exit

exec "$PYTHON" "$APP" "$@"