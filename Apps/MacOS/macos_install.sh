#!/bin/bash

set -e

echo "🔧 Installing Snap Rename..."

# ─────────────────────────────────────────────
# 1. Detect Python (NO system python)
# ─────────────────────────────────────────────
echo "🔍 Detecting Python..."

PYTHON_PATH=""

# 1. Official Python (preferred)
if [ -d "/Library/Frameworks/Python.framework/Versions" ]; then
    LATEST=$(ls /Library/Frameworks/Python.framework/Versions \
        | grep -E '^[0-9]+\.[0-9]+$' \
        | sort -V \
        | tail -n 1)

    if [ -n "$LATEST" ]; then
        PYTHON_PATH="/Library/Frameworks/Python.framework/Versions/$LATEST/bin/python3"
    fi
fi

# 2. Homebrew Python (fallback)
if [ -z "$PYTHON_PATH" ] && command -v brew &> /dev/null; then
    BREW_PREFIX=$(brew --prefix python 2>/dev/null || true)
    if [ -n "$BREW_PREFIX" ] && [ -x "$BREW_PREFIX/bin/python3" ]; then
        PYTHON_PATH="$BREW_PREFIX/bin/python3"
    fi
fi

# ❌ Do NOT fallback to /usr/bin/python3

# 3. If not found → fail
if [ -z "$PYTHON_PATH" ]; then
    echo "❌ No usable Python found."
    echo ""
    echo "👉 Install latest Python from:"
    echo "https://www.python.org/downloads/"
    echo ""
    exit 1
fi

# 4. Version check (>= 3.10)
if ! "$PYTHON_PATH" -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)"; then
    echo "❌ Python 3.10+ required."
    echo "👉 Install latest Python from:"
    echo "https://www.python.org/downloads/"
    exit 1
fi

echo "✅ Using Python: $PYTHON_PATH"

# Save config
echo "$PYTHON_PATH" > "$HOME/.srenameinfo"
echo "📄 Saved Python path → ~/.srenameinfo"

# ─────────────────────────────────────────────
# 2. Install dependencies
# ─────────────────────────────────────────────
echo "📦 Installing dependencies..."

"$PYTHON_PATH" -m pip install --upgrade pip >/dev/null 2>&1
"$PYTHON_PATH" -m pip install PyQt6 textual

echo "✅ Dependencies installed"

# ─────────────────────────────────────────────
# 3. Download app bundle
# ─────────────────────────────────────────────
echo "⬇️ Downloading Snap Rename..."

TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"

curl -L -o macos_app.zip \
https://github.com/Satvik-web/Snap-Rename/releases/download/v1.0.0/macos_app.zip

unzip macos_app.zip >/dev/null

echo "✅ Downloaded"

# ─────────────────────────────────────────────
# 4. Install app
# ─────────────────────────────────────────────
echo "📁 Installing app..."

sudo cp -R "Snap Rename.app" /Applications/

# ─────────────────────────────────────────────
# 5. Install CLI
# ─────────────────────────────────────────────
echo "🧩 Installing CLI..."

sudo cp srename.sh /usr/local/bin/srename.sh
sudo chmod +x /usr/local/bin/srename.sh
sudo ln -sf /usr/local/bin/srename.sh /usr/local/bin/srename

echo "✅ CLI installed"

# ─────────────────────────────────────────────
# 6. Install Finder Quick Action
# ─────────────────────────────────────────────
echo "⚡ Installing Finder Quick Action..."

mkdir -p "$HOME/Library/Services"
cp -R "Snap Rename.workflow" "$HOME/Library/Services/"

echo "✅ Quick Action installed"

# ─────────────────────────────────────────────
# 7. Cleanup
# ─────────────────────────────────────────────
cd "$HOME"
rm -rf "$TMP_DIR"

# ─────────────────────────────────────────────
# DONE
# ─────────────────────────────────────────────
echo ""
echo "🎉 Snap Rename installed successfully!"
echo ""
echo "👉 Usage:"
echo "  srename --gui"
echo "  srename -d ~/Downloads"
echo ""