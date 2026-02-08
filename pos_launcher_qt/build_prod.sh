#!/bin/bash
# Build POS Launcher Qt - PRODUCTION RELEASE (Linux)
# One-click script to build and package for deployment
# Creates TGZ file ready for customer distribution

echo ""
echo "============================================================="
echo "       POS LAUNCHER QT - PRODUCTION BUILD (LINUX)"
echo "============================================================="
echo ""
echo "This script will:"
echo "  1. Verify Python installation"
echo "  2. Install dependencies"
echo "  3. Build executable with PyInstaller"
echo "  4. Package into distributable TGZ for deployment"
echo ""

# Record start time
START_TIME=$(date +%s)

# Change to script directory
cd "$(dirname "$0")"

# Step 0: Check Python
echo "============================================================="
echo "  STEP 0: VERIFYING PYTHON INSTALLATION"
echo "============================================================="
echo ""
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found! Please install Python 3.8+"
    exit 1
fi
python3 --version
echo "Python OK!"
echo ""

# Step 1: Install dependencies
echo "============================================================="
echo "  STEP 1: INSTALLING DEPENDENCIES"
echo "============================================================="
echo ""

echo "Installing dependencies from requirements.txt..."
python3 -m pip install -q -r requirements.txt

echo "✓ Dependencies installed!"
echo ""

# Step 2: Build
echo "============================================================="
echo "  STEP 2: BUILDING EXECUTABLE"
echo "============================================================="
echo ""

bash build_dev.sh
if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Build failed!"
    exit 1
fi

# Step 3: Package
echo ""
echo ""
echo "============================================================="
echo "  STEP 3: PACKAGING RELEASE"
echo "============================================================="
echo ""

bash package_release.sh
if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Packaging failed!"
    exit 1
fi

# Calculate duration
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

# Final summary
echo ""
echo ""
echo "============================================================="
echo "             ALL DONE! READY FOR DEPLOYMENT"
echo "============================================================="
echo ""
echo "Build Time: ${MINUTES}m ${SECONDS}s"
echo ""

# Find latest TGZ
LATEST_TGZ=$(ls -t releases/*.tar.gz 2>/dev/null | head -1)

if [ -n "$LATEST_TGZ" ]; then
    echo "Release Package Location:"
    echo "  $LATEST_TGZ"
    FILE_SIZE=$(stat -f%z "$LATEST_TGZ" 2>/dev/null || stat -c%s "$LATEST_TGZ")
    SIZE_MB=$((FILE_SIZE / 1048576))
    echo "  Size: ${SIZE_MB} MB"
else
    echo "WARNING: TGZ file not found in releases folder"
fi

echo ""
echo "Next Steps:"
echo "  1. Test locally: cd releases/POSLauncher-v* && ./POSLauncher"
echo "  2. Transfer TGZ to target computer"
echo "  3. Extract and configure config.json"
echo "  4. Run ./POSLauncher"
echo ""
