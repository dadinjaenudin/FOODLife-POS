#!/bin/bash
# Kitchen Printer Agent - Linux Deployment Script
# Usage: sudo bash deploy_linux.sh

set -e

echo "=============================================="
echo "Kitchen Printer Agent - Linux Deployment"
echo "=============================================="

# Configuration
INSTALL_DIR="/opt/foodlife/kitchen_printer_agent"
ENV_FILE="/opt/foodlife/.env"
SERVICE_FILE="/etc/systemd/system/kitchen-agent.service"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (sudo)"
    exit 1
fi

echo ""
echo "[1/7] Creating directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "/opt/foodlife"

echo "[2/7] Copying files..."
cp -v kitchen_agent.py "$INSTALL_DIR/"
cp -v kitchen_agent_config.json "$INSTALL_DIR/"
cp -v requirements.txt "$INSTALL_DIR/"

echo "[3/7] Setting up Python virtual environment..."
cd "$INSTALL_DIR"
python3 -m venv venv
source venv/bin/activate

echo "[4/7] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[5/7] Building executable with PyInstaller..."
pip install pyinstaller

# Build executable
pyinstaller --onefile \
    --name=KitchenAgent \
    --add-data=kitchen_agent_config.json:. \
    --collect-data=escpos \
    --hidden-import=psycopg2 \
    --hidden-import=escpos.printer \
    --clean \
    --noconfirm \
    kitchen_agent.py

# Copy executable to install dir
cp -v dist/KitchenAgent "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/KitchenAgent"

echo "[6/7] Setting up environment file..."
if [ ! -f "$ENV_FILE" ]; then
    cat > "$ENV_FILE" << 'EOF'
# Kitchen Printer Agent - Environment Variables
DB_HOST=localhost
DB_PORT=5433
DB_NAME=fnb_edge_db
DB_USER=postgres
DB_PASSWORD=postgres
AGENT_NAME=Kitchen-Agent-1
STATION_IDS=1,2,3
EOF
    echo "✅ Created default .env file: $ENV_FILE"
    echo "⚠️  Please edit this file with your actual database credentials!"
else
    echo "✅ Environment file already exists: $ENV_FILE"
fi

echo "[7/7] Installing systemd service..."
cp -v kitchen-agent.service "$SERVICE_FILE"

# Update service file with correct paths
sed -i "s|WorkingDirectory=.*|WorkingDirectory=$INSTALL_DIR|g" "$SERVICE_FILE"
sed -i "s|EnvironmentFile=.*|EnvironmentFile=$ENV_FILE|g" "$SERVICE_FILE"
sed -i "s|ExecStart=.*|ExecStart=$INSTALL_DIR/KitchenAgent|g" "$SERVICE_FILE"

# Reload systemd
systemctl daemon-reload

echo ""
echo "=============================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=============================================="
echo ""
echo "Installed to: $INSTALL_DIR"
echo "Executable: $INSTALL_DIR/KitchenAgent"
echo "Config: $INSTALL_DIR/kitchen_agent_config.json"
echo "Environment: $ENV_FILE"
echo "Service: $SERVICE_FILE"
echo ""
echo "⚠️  IMPORTANT: Edit environment file before starting:"
echo "   nano $ENV_FILE"
echo ""
echo "Commands:"
echo "  Start:   sudo systemctl start kitchen-agent"
echo "  Stop:    sudo systemctl stop kitchen-agent"
echo "  Status:  sudo systemctl status kitchen-agent"
echo "  Enable:  sudo systemctl enable kitchen-agent"
echo "  Logs:    sudo journalctl -u kitchen-agent -f"
echo ""
echo "=============================================="
