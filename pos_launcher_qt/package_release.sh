#!/bin/bash
# Package POS Launcher Qt for distribution (Linux)

echo ""
echo "============================================================="
echo "       POS LAUNCHER QT - PACKAGE RELEASE SCRIPT (LINUX)"
echo "============================================================="
echo ""

# Change to script directory
cd "$(dirname "$0")"

# Step 1: Verify build exists
echo "[1/5] Verifying build output..."
if [ ! -f "dist/POSLauncher/POSLauncher" ]; then
    echo "ERROR: Build not found! Run ./build_dev.sh first."
    exit 1
fi
echo "Build found: dist/POSLauncher/POSLauncher"
echo ""

# Step 2: Create release directory
echo "[2/5] Creating release directory..."
mkdir -p releases

# Generate version string
DATE_STR=$(date +%Y-%m-%d)
RELEASE_NAME="POSLauncher-v${DATE_STR}"
RELEASE_DIR="releases/${RELEASE_NAME}"

if [ -d "$RELEASE_DIR" ]; then
    rm -rf "$RELEASE_DIR"
fi
mkdir -p "$RELEASE_DIR"
echo "Created: $RELEASE_DIR"
echo ""

# Step 3: Copy files
echo "[3/5] Copying files..."
cp -r dist/POSLauncher/* "$RELEASE_DIR/"
echo "Copied executable and dependencies"
echo ""

# Step 4: Create config template and README
echo "[4/5] Creating configuration files..."

# Create config.json template
cat > "$RELEASE_DIR/config.json" << 'EOF'
{
  "terminal_code": "BOE-001",
  "company_code": "YOGYA",
  "brand_code": "BOE",
  "store_code": "KPT",
  "edge_server": "http://127.0.0.1:8001"
}
EOF
echo "Created: config.json"

# Create README.txt
cat > "$RELEASE_DIR/README.txt" << 'EOF'
POS LAUNCHER QT - DEPLOYMENT GUIDE (LINUX)
===========================================

CONTENTS:
  - POSLauncher           : Main application (executable)
  - _internal/            : Required libraries
  - config.json           : Configuration file
  - customer_display.html : Customer display page
  - print_monitor.html    : Print monitoring dashboard
  - assets/               : Images and resources

INSTALLATION:
  1. Extract this folder to target computer
  2. Edit config.json:
     - terminal_code: Terminal identifier (e.g., BOE-001)
     - company_code: Company code (e.g., YOGYA)
     - brand_code: Brand code (e.g., BOE)
     - store_code: Store code (e.g., KPT)
     - edge_server: Django Edge Server URL

CONFIGURATION EXAMPLE:
  {
      "terminal_code": "BOE-001",
      "company_code": "YOGYA",
      "brand_code": "BOE",
      "store_code": "KPT",
      "edge_server": "http://192.168.1.100:8001"
  }

  - terminal_code: Unique terminal identifier
  - edge_server: URL of Django Edge Server
  - Customer display settings managed from database/API

FIRST RUN:
  1. Make executable: chmod +x POSLauncher
  2. Run: ./POSLauncher
  3. Local API will start on port 5000
  4. Browser will open POS interface

SYSTEM REQUIREMENTS:
  - Ubuntu 20.04+ / Debian 11+ / CentOS 8+
  - Python 3.8+ (if running from source)
  - Qt 6.x libraries (included in _internal/)
  - Network connectivity to Edge Server

PRINTER SETUP:
  - Receipt Printer: Configure in Terminal settings
  - Linux: Uses CUPS (default printer)
  - Set printer name in Terminal configuration
  - Install printer drivers: apt install cups

CUSTOMER DISPLAY:
  - Access: http://localhost:5000/customer-display
  - Fullscreen on second monitor recommended
  - Auto-refresh enabled
  - Managed from Edge API settings

PRINT MONITOR:
  - Access: http://localhost:5000/print-monitor
  - Monitor print job status
  - Retry failed jobs
  - Real-time statistics

TROUBLESHOOTING:
  - Check launcher_debug.log for errors
  - Verify Django Edge Server is accessible
  - Check firewall settings for port 5000
  - Ensure printer is connected and configured in CUPS
  - Run with: ./POSLauncher to see console output
  - Check permissions: chmod +x POSLauncher

AUTOSTART (OPTIONAL):
  Create systemd service:
  
  1. Create service file: /etc/systemd/system/poslauncher.service
     
     [Unit]
     Description=YOGYA POS Launcher
     After=network.target
     
     [Service]
     Type=simple
     User=pos
     WorkingDirectory=/opt/poslauncher
     ExecStart=/opt/poslauncher/POSLauncher
     Restart=always
     RestartSec=10
     
     [Install]
     WantedBy=multi-user.target
  
  2. Enable and start:
     sudo systemctl enable poslauncher
     sudo systemctl start poslauncher

SUPPORT:
  For issues, check the logs or contact support.

EOF
echo "Created: README.txt"
echo ""

# Step 5: Create TGZ archive
echo "[5/5] Creating TGZ archive..."
cd releases
tar -czf "${RELEASE_NAME}.tar.gz" "$RELEASE_NAME"
if [ $? -eq 0 ]; then
    echo "Created: releases/${RELEASE_NAME}.tar.gz"
    
    # Get TGZ file size
    FILE_SIZE=$(stat -f%z "${RELEASE_NAME}.tar.gz" 2>/dev/null || stat -c%s "${RELEASE_NAME}.tar.gz")
    SIZE_MB=$((FILE_SIZE / 1048576))
    echo "Size: ${SIZE_MB} MB"
else
    echo "WARNING: Could not create TGZ archive"
    echo "You can manually compress the folder: $RELEASE_DIR"
fi
cd ..
echo ""

# Success summary
echo ""
echo "============================================================="
echo "              PACKAGING COMPLETE!"
echo "============================================================="
echo ""
echo "Release Package:"
echo "  releases/${RELEASE_NAME}.tar.gz"
echo ""
echo "Folder Contents:"
echo "  releases/${RELEASE_NAME}/"
echo ""
echo "Deployment Steps:"
echo "  1. Transfer TGZ to target computer"
echo "  2. Extract: tar -xzf ${RELEASE_NAME}.tar.gz"
echo "  3. Edit config.json with server URL"
echo "  4. Make executable: chmod +x POSLauncher"
echo "  5. Run: ./POSLauncher"
echo ""
echo "Ready for deployment!"
echo ""
