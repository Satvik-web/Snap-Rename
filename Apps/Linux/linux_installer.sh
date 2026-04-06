#!/bin/bash

set -e

APP_DIR="$HOME/.SnapRename"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"

ZIP_URL="https://github.com/Satvik-web/Snap-Rename/releases/download/v1.0.0/linux_app.zip"
ZIP_FILE="/tmp/snaprename.zip"

echo "=== Snap Rename Installer ==="

# ─────────────────────────────
# 1. Check Python
# ─────────────────────────────
echo "[1/8] Checking Python..."

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python3 not found!"
    echo ""
    echo "Install it using:"
    echo "Debian/Ubuntu: sudo apt install python3 python3-venv python3-pip"
    echo "Fedora:        sudo dnf install python3 python3-venv python3-pip"
    echo "Arch:          sudo pacman -S python python-pip"
    exit 1
fi

echo "Python found"

# ─────────────────────────────
# 2. Download app
# ─────────────────────────────
echo "[2/8] Downloading Snap Rename..."

mkdir -p "$APP_DIR"

if command -v curl >/dev/null 2>&1; then
    curl -L "$ZIP_URL" -o "$ZIP_FILE"
elif command -v wget >/dev/null 2>&1; then
    wget "$ZIP_URL" -O "$ZIP_FILE"
else
    echo "Neither curl nor wget found!"
    echo ""
    echo "Install one of them:"
    echo "Debian/Ubuntu: sudo apt install curl"
    echo "Fedora:        sudo dnf install curl"
    echo "Arch:          sudo pacman -S curl"
    exit 1
fi

echo "Downloaded"

# ─────────────────────────────
# 3. Extract
# ─────────────────────────────
echo "[3/8] Extracting..."

unzip -o "$ZIP_FILE" -d "$APP_DIR"

echo "✔ Extracted to $APP_DIR"

# ─────────────────────────────
# 4. Create venv
# ─────────────────────────────
echo "[4/8] Creating virtual environment..."

python3 -m venv "$APP_DIR/env"

echo "✔ venv created"

# ─────────────────────────────
# 5. Install dependencies
# ─────────────────────────────
echo "[5/8] Installing dependencies..."

"$APP_DIR/env/bin/pip" install --upgrade pip
"$APP_DIR/env/bin/pip" install --only-binary=:all: PyQt6 textual

echo "Dependencies installed"

# ─────────────────────────────
# 6. Setup CLI (srename)
# ─────────────────────────────
echo "[6/8] Setting up CLI..."

mkdir -p "$BIN_DIR"

cat > "$APP_DIR/srename.sh" << 'EOF'
#!/bin/bash
exec "$HOME/.SnapRename/env/bin/python" "$HOME/.SnapRename/main.py" "$@"
EOF

chmod +x "$APP_DIR/srename.sh"

ln -sf "$APP_DIR/srename.sh" "$BIN_DIR/srename"

echo "CLI installed (srename)"

# ─────────────────────────────
# 7. Desktop entry
# ─────────────────────────────
echo "[7/8] Creating app launcher..."

mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_DIR/snap-rename.desktop" << EOF
[Desktop Entry]
Name=Snap Rename
Exec=$HOME/.SnapRename/env/bin/python $HOME/.SnapRename/main.py --gui
Icon=$HOME/.SnapRename/logo.png
Type=Application
Categories=Utility;
Terminal=false
EOF

chmod +x "$DESKTOP_DIR/snap-rename.desktop"

echo "✔ App launcher created"

# ─────────────────────────────
# 8. Ensure ~/.local/bin is in PATH
# ─────────────────────────────
echo "[8/8] Configuring PATH..."

SHELL_RC=""

if [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
else
    SHELL_RC="$HOME/.bashrc"
fi

# Only add if not already present
if ! grep -q 'export PATH="$HOME/.local/bin:$PATH"' "$SHELL_RC" 2>/dev/null; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
    echo "✔ Added ~/.local/bin to PATH in $SHELL_RC"
else
    echo "✔ PATH already configured"
fi

echo ""
echo "Installation complete!"
echo ""
echo "Run:"
echo "  srename"
echo ""
echo "Restart your terminal or run:"
echo "source $SHELL_RC"
echo ""
echo "Or, launch Snap Rename from Start Menu."
