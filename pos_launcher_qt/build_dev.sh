#!/bin/bash
# POS Launcher Qt - DEVELOPMENT BUILD (Linux)
# Quick build for local testing

echo ""
echo "============================================================="
echo "      POS LAUNCHER QT - DEVELOPMENT BUILD (LINUX)"
echo "============================================================="
echo ""
echo "For quick testing only - does NOT create release package"
echo "For production release, use: ./build_prod.sh"
echo ""

# Change to script directory
cd "$(dirname "$0")"

# Step 1: Check Python
echo "[1/8] Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found! Please install Python 3.8+"
    exit 1
fi
python3 --version
echo ""

# Step 2: Setup environment
echo "[2/8] Setting up build environment..."
echo "Working directory: $(pwd)"
echo ""

# Step 3: Install dependencies
echo "[3/8] Installing dependencies..."
echo "Installing from requirements.txt..."
python3 -m pip install -q -r requirements.txt
echo "Dependencies installed!"
echo ""

# Step 4: Install PyInstaller
echo "[4/8] Installing PyInstaller (compatible version)..."
python3 -m pip install -q pyinstaller==6.3.0
echo "PyInstaller 6.3.0 installed!"
echo ""

# Step 5: Clean previous build
echo "[5/8] Cleaning previous build artifacts..."
if [ -d "build" ]; then
    rm -rf build
    echo "Removed build/ directory"
fi
if [ -d "dist" ]; then
    rm -rf dist
    echo "Removed dist/ directory"
fi
echo "Clean complete!"
echo ""

# Step 6: Build with PyInstaller
echo "[6/8] Building executable with PyInstaller..."
echo ""
echo "============================================================="
echo "             PYINSTALLER BUILD OUTPUT"
echo "============================================================="
echo ""

python3 -m PyInstaller pos_launcher.spec --clean --noconfirm

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: PyInstaller build failed!"
    exit 1
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║          POS LAUNCHER BUILD CONFIGURATION                  ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "App Name:        POSLauncher"
echo "Output Folder:   dist/POSLauncher/"
echo "Executable:      dist/POSLauncher/POSLauncher"
echo ""
echo "Data Files:      7 items included"
echo "Hidden Imports:  25 modules"
echo ""
echo "Build Type:      Folder Distribution (--onedir)"
echo "Console Window:  Visible (for debugging)"
echo "Compression:     UPX Enabled"
echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  After build, run: ./package_release.sh to create TGZ     ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo ""
echo "Build completed successfully!"
echo ""

# Step 7: Copy config files
echo "[7/8] Copying config files to dist..."
if [ -f "config.json" ]; then
    cp config.json dist/POSLauncher/
    echo "✓ Copied config.json"
else
    echo "⚠ config.json not found"
fi
echo ""

# Step 8: Verify build output
echo "[8/8] Verifying build output..."
if [ -f "dist/POSLauncher/POSLauncher" ]; then
    echo "Executable created: dist/POSLauncher/POSLauncher"
    FILE_SIZE=$(stat -f%z "dist/POSLauncher/POSLauncher" 2>/dev/null || stat -c%s "dist/POSLauncher/POSLauncher")
    echo "Size: $FILE_SIZE bytes"
    # Make executable
    chmod +x dist/POSLauncher/POSLauncher
    echo "✓ Set executable permissions"
else
    echo "ERROR: Build output not found!"
    exit 1
fi
echo ""

echo ""
echo "============================================================="
echo "                 BUILD SUCCESSFUL!"
echo "============================================================="
echo ""
echo "Output Location:"
echo "  dist/POSLauncher/"
echo ""
echo "Executable:"
echo "  dist/POSLauncher/POSLauncher"
echo ""
echo "Next Steps:"
echo "  1. Test the executable locally:"
echo "     cd dist/POSLauncher"
echo "     ./POSLauncher"
echo ""
echo "  2. Package for distribution:"
echo "     ./package_release.sh"
echo ""
echo "  3. Deploy to target computer:"
echo "     - Copy entire POSLauncher folder"
echo "     - Run ./POSLauncher"
echo ""
