# YOGYA POS Launcher - PyQt6 Edition

Cross-platform POS launcher with embedded Chromium engine. No external webview runtime required.

## Features

✅ **Dual Display Support**
- Main POS on primary monitor (fullscreen)
- Customer Display on secondary monitor (fullscreen)
- Automatic monitor detection

✅ **Local API Server**
- Flask server on `http://127.0.0.1:5000`
- Print to local printers (Windows & Linux)
- Real-time customer display updates via SSE

✅ **Cross-Platform**
- Windows (no WebView2 Runtime needed)
- Linux (no external dependencies)
- Bundle to single executable

✅ **Terminal Management**
- Auto-validate terminal with Edge Server
- Config-based deployment
- Session management

## Installation

### Windows

```bash
# Install Python 3.10+
# Install dependencies
pip install -r requirements.txt

# Run launcher
python pos_launcher_qt.py
```

### Linux

```bash
# Install Python 3.10+
# Install system dependencies
sudo apt install python3-pyqt6 python3-pyqt6.qtwebengine libcups2-dev

# Install Python dependencies
pip install -r requirements.txt

# Run launcher
python pos_launcher_qt.py
```

## Configuration

Edit `config.json`:

```json
{
  "terminal_code": "BOE-001",
  "company_code": "YOGYA",
  "brand_code": "BOE",
  "store_code": "KPT",
  "edge_server": "http://127.0.0.1:8001"
}
```

## API Endpoints

### Print Receipt
```bash
POST http://127.0.0.1:5000/api/print
Content-Type: application/json

{
  "type": "receipt",
  "printer_name": "TM-T88V",  // Optional, uses default if not specified
  "store_name": "YOGYA Store",
  "store_address": "Jl. Address",
  "items": [
    {"name": "Product 1", "quantity": 2, "price": 10000}
  ],
  "total": 20000
}
```

### Update Customer Display
```bash
POST http://127.0.0.1:5000/api/customer-display/update
Content-Type: application/json

{
  "total": 50000,
  "items": [
    {"name": "Product A", "quantity": 1, "price": 25000},
    {"name": "Product B", "quantity": 2, "price": 12500}
  ],
  "payment_method": "cash",
  "change": 10000
}
```

### Health Check
```bash
GET http://127.0.0.1:5000/health
```

## Bundle to Executable

### Windows

```bash
# Install PyInstaller
pip install pyinstaller

# Bundle
pyinstaller --onefile --windowed --name "YOGYA-POS" ^
  --add-data "config.json;." ^
  --add-data "customer_display.html;." ^
  --add-data "local_api.py;." ^
  pos_launcher_qt.py
```

### Linux

```bash
# Install PyInstaller
pip install pyinstaller

# Bundle
pyinstaller --onefile --windowed --name "YOGYA-POS" \
  --add-data "config.json:." \
  --add-data "customer_display.html:." \
  --add-data "local_api.py:." \
  pos_launcher_qt.py
```

## Architecture

```
┌─────────────────────────────────────────┐
│  pos_launcher_qt.py                     │
│  ┌───────────────────────────────────┐  │
│  │  1. Start Flask API (port 5000)   │  │
│  │  2. Validate terminal              │  │
│  │  3. Open Main POS (PyQt6)          │  │
│  │  4. Open Customer Display (PyQt6)  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
           ↓                    ↓
    ┌──────────┐         ┌──────────────┐
    │ Main POS │         │   Customer   │
    │ (Monitor │         │   Display    │
    │    1)    │         │  (Monitor 2) │
    └──────────┘         └──────────────┘
           ↓                    ↑
    ┌──────────────────────────────────┐
    │  Local API (Flask - port 5000)   │
    │  • Print receipts                │
    │  • Update customer display (SSE) │
    └──────────────────────────────────┘
```

## Troubleshooting

### Windows: Missing DLL
- Install Visual C++ Redistributable 2015-2022

### Linux: Qt not found
```bash
sudo apt install python3-pyqt6 python3-pyqt6.qtwebengine
```

### Printer not working (Windows)
```bash
pip install pywin32
python -m pywin32_postinstall
```

### Printer not working (Linux)
```bash
sudo apt install libcups2-dev
sudo systemctl start cups
```

## Size Comparison

- PyQt6 bundle: ~120MB (includes Chromium)
- Pywebview + WebView2 Runtime: ~70MB (requires external installer)
- CEFPython: ~100MB (unmaintained)

## License

Proprietary - YOGYA FoodLife POS System
