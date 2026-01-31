# Print Agent Quick Start

## 🚀 5-Minute Setup

### Step 1: Install Dependencies
```bash
cd print_agent
pip install -r requirements.txt
```

### Step 2: Configure Agent
Edit `print_agent_config.json`:
```json
{
  "server_url": "http://127.0.0.1:8000",
  "terminal_id": "KASIR-01",
  "api_key": "your-secret-api-key-here"
}
```

**Note:** API key hanya diperlukan jika `PRINT_AGENT_AUTH_REQUIRED=True` di Django settings. 
Secara default (development mode), API key bisa di-skip.

### Step 3: Find Your Printer
```bash
python -m escpos.cli list
```

Copy the Vendor ID and Product ID to config:
```json
{
  "printer_config": {
    "usb": {
      "idVendor": 1208,
      "idProduct": 514
    }
  }
}
```

### Step 4: Run Agent
```bash
python agent.py
```

You should see:
```
🖨️  PRINT AGENT STARTING
✅ Terminal registered: KASIR-01
✅ Printer initialized: usb
✅ Print Agent is running...
```

### Step 5: Test Print
From Django server, create a test job:
```bash
python test_print_agent.py
```

Agent will automatically fetch and print!

## 📝 Common Printer IDs

**Epson TM-T82:**
- Vendor ID: 0x04b8 (1208)
- Product ID: 0x0202 (514)

**Epson TM-T88V:**
- Vendor ID: 0x04b8 (1208)
- Product ID: 0x0e15 (3605)

**Star TSP143:**
- Vendor ID: 0x0519 (1305)
- Product ID: 0x0002 (2)

**Xprinter XP-58:**
- Vendor ID: 0x0483 (1155)
- Product ID: 0x5743 (22339)

## ⚙️ Config Templates

### USB Printer (Default)
```json
{
  "server_url": "http://127.0.0.1:8000",
  "terminal_id": "KASIR-01",
  "api_key": "your-secret-api-key-here",
  "poll_interval": 2,
  "printer_type": "usb",
  "printer_config": {
    "usb": {
      "idVendor": 1208,
      "idProduct": 514
    }
  }
}
```

### Network Printer
```json
{
  "server_url": "http://192.168.1.10:8000",
  "terminal_id": "KITCHEN-01",
  "api_key": "your-secret-api-key-here",
  "poll_interval": 2,
  "printer_type": "network",
  "printer_config": {
    "network": {
      "host": "192.168.1.100",
      "port": 9100
    }
  }
}
```

### Multiple Cashiers Setup

**Terminal 1 (Kasir 1):**
```json
{
  "terminal_id": "KASIR-01",
  "printer_type": "usb",
  "printer_config": {
    "usb": {
      "idVendor": 1208,
      "idProduct": 514
    }
  }
}
```

**Terminal 2 (Kasir 2):**
```json
{
  "terminal_id": "KASIR-02",
  "printer_type": "usb",
  "printer_config": {
    "usb": {
      "idVendor": 1208,
      "idProduct": 3605
    }
  }
}
```

**Kitchen:**
```json
{
  "terminal_id": "KITCHEN-01",
  "printer_type": "network",
  "printer_config": {
    "network": {
      "host": "192.168.1.101",
      "port": 9100
    }
  }
}
```

## 🔧 Troubleshooting

### "Device not found"
```bash
# Windows: Install Zadig USB driver
# Download from: https://zadig.akeo.ie/
# 1. Run Zadig
# 2. Options → List All Devices
# 3. Select your printer
# 4. Choose "WinUSB" driver
# 5. Click "Replace Driver"
```

### "Cannot connect to server"
- Check server_url in config
- Ensure Django server is running
- Check firewall allows port 8000

### "Invalid API key"
- Update api_key in config
- Update api_key in Django `apps/pos/print_api.py`

## ✅ Testing

### Test 1: Connection
Agent shows:
```
✅ Terminal registered: KASIR-01
```

### Test 2: Printer
Agent shows:
```
✅ Printer initialized: usb
```

### Test 3: Print Job
From Django:
```bash
python test_print_agent.py
```

Agent shows:
```
📄 Processing job #1 - receipt
✅ Job #1 completed
```

Printer prints receipt!

## 🎯 Production Setup

### Run as Windows Service

**Using NSSM:**
```bash
# Download NSSM from nssm.cc
nssm install PrintAgent "C:\Python310\python.exe" ^
  "C:\path\to\print_agent\agent.py"

nssm set PrintAgent AppDirectory "C:\path\to\print_agent"
nssm start PrintAgent
```

**Using Task Scheduler:**
1. Task Scheduler → Create Basic Task
2. Name: "Print Agent - KASIR-01"
3. Trigger: "At startup"
4. Action: Start program
   - Program: `C:\Python310\python.exe`
   - Arguments: `C:\path\to\agent.py`
   - Start in: `C:\path\to\print_agent`
5. Settings:
   - ✅ Run whether user is logged in or not
   - ✅ Run with highest privileges
   - ✅ If task fails, restart every 1 minute

## 📊 Monitoring

### Check Agent Status
Agent terminal shows:
```
✅ Print Agent is running...
📄 Processing job #123 - receipt
✅ Job #123 completed
```

### Check Django Admin
Visit: `http://your-server:8000/admin/pos/printjob/`

See all print jobs:
- Pending (waiting for agent)
- Completed (successfully printed)
- Failed (with error message)

## 🆘 Need Help?

Check full documentation: `README.md`
