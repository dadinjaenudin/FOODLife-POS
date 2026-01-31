# Print Agent Setup Guide
## Remote Printing System for Web-Based POS

### 📋 Architecture

```
┌─────────────────┐
│  Django Server  │ (Cloud/Central Server)
│   Port: 8000    │
└────────┬────────┘
         │ HTTP API
         │
    ┌────┴────┬────────┬────────┐
    │         │        │        │
┌───┴──┐  ┌──┴───┐ ┌──┴───┐ ┌──┴───┐
│Print │  │Print │ │Print │ │Print │
│Agent │  │Agent │ │Agent │ │Agent │
│  #1  │  │  #2  │ │  #3  │ │  #4  │
└───┬──┘  └──┬───┘ └──┬───┘ └──┬───┘
    │        │        │        │
┌───┴──┐ ┌──┴───┐ ┌──┴───┐ ┌──┴───┐
│USB   │ │USB   │ │USB   │ │Network│
│58mm  │ │80mm  │ │80mm  │ │ LAN  │
└──────┘ └──────┘ └──────┘ └──────┘
KASIR-01 KASIR-02 KITCHEN   BAR
```

### ⚙️ Setup Instructions

#### 1. **Server Setup (Django)**

**1.1. Run Migration:**
```bash
python manage.py makemigrations
python manage.py migrate
```

**1.2. Configure API Key:**
Edit `apps/pos/print_api.py`:
```python
# Change this to your secret key
return api_key == 'your-secret-api-key-here'
```

**1.3. Update Print Functions:**
In your views, use print queue instead of direct print:
```python
# OLD (direct print)
from apps.pos.services import print_receipt
print_receipt(bill)

# NEW (queue for remote print)
from apps.pos.print_queue import queue_print_receipt
queue_print_receipt(bill, terminal_id='KASIR-01')
```

#### 2. **Print Agent Setup (Each Cashier PC)**

**2.1. Install Python:**
- Download Python 3.10+ from python.org
- Install with "Add to PATH" option checked

**2.2. Install Print Agent:**
```bash
# Navigate to print agent folder
cd print_agent

# Install dependencies
pip install -r requirements.txt

# Install USB driver (Windows)
# Download and install from: https://zadig.akeo.ie/
```

**2.3. Find Printer ID:**
```bash
# List all USB devices
python -m escpos.cli list

# Output example:
# Vendor ID: 0x04b8 (1208)
# Product ID: 0x0202 (514)
```

**2.4. Configure Agent:**
Edit `print_agent_config.json`:
```json
{
  "server_url": "http://your-server-ip:8000",
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

**2.5. Run Agent:**
```bash
# Run manually
python agent.py

# Or run as Windows Service (see below)
```

#### 3. **Running as Windows Service**

**Option A: Using NSSM (Recommended)**
```bash
# Download NSSM from: https://nssm.cc/download
nssm install PrintAgent "C:\Python310\python.exe" "C:\path\to\agent.py"
nssm start PrintAgent
```

**Option B: Using Task Scheduler**
1. Open Task Scheduler
2. Create Basic Task
3. Trigger: "At startup"
4. Action: "Start a program"
5. Program: `C:\Python310\python.exe`
6. Arguments: `C:\path\to\agent.py`
7. Check "Run whether user is logged in or not"

### 🔧 Configuration Examples

#### USB Thermal Printer (58mm/80mm)
```json
{
  "printer_type": "usb",
  "printer_config": {
    "usb": {
      "idVendor": 1208,
      "idProduct": 514
    }
  }
}
```

#### Network Printer (Ethernet/WiFi)
```json
{
  "printer_type": "network",
  "printer_config": {
    "network": {
      "host": "192.168.1.100",
      "port": 9100
    }
  }
}
```

#### Multiple Agents Configuration

**Cashier 1:**
```json
{
  "terminal_id": "KASIR-01",
  "printer_type": "usb"
}
```

**Cashier 2:**
```json
{
  "terminal_id": "KASIR-02",
  "printer_type": "usb"
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

### 📊 Usage in Django

#### Print Receipt
```python
from apps.pos.print_queue import queue_print_receipt

# Queue receipt for printing
queue_print_receipt(bill, terminal_id='KASIR-01')
```

#### Print Kitchen Order
```python
from apps.pos.print_queue import queue_print_kitchen

# Queue kitchen order
queue_print_kitchen(bill, station='kitchen', items=pending_items, terminal_id='KITCHEN-01')
```

#### Check Print Status
```python
from apps.pos.models import PrintJob

# Get pending jobs
pending = PrintJob.objects.filter(status='pending').count()

# Get failed jobs
failed = PrintJob.objects.filter(status='failed')
for job in failed:
    print(f"Job #{job.id} failed: {job.error_message}")
```

### 🔍 Troubleshooting

#### Agent Can't Connect to Server
```
⚠️  Cannot connect to server: Connection refused
```
**Solution:**
- Check server URL in config
- Ensure server is running
- Check firewall settings
- Verify API key is correct

#### Printer Not Found
```
❌ Failed to initialize printer: Device not found
```
**Solution:**
- Run `python -m escpos.cli list` to find printer
- Check USB cable connection
- Install Zadig USB driver (Windows)
- Update printer_config with correct IDs

#### Print Job Stuck in Pending
**Check Agent Status:**
```bash
# Agent should show:
✅ Terminal registered: KASIR-01
✅ Printer initialized: usb
📄 Processing job #123 - receipt
✅ Job #123 completed
```

**If not processing:**
- Restart print agent
- Check terminal_id matches
- Verify printer is powered on

### 📱 Admin Interface (Coming Soon)

View print jobs in Django Admin:
```
http://your-server:8000/admin/pos/printjob/
```

Features:
- ✅ View all print jobs
- ✅ Filter by status (pending/completed/failed)
- ✅ Retry failed jobs
- ✅ View error messages
- ✅ Print job statistics

### 🚀 Production Deployment

**Server:**
- Use Gunicorn/uWSGI for Django
- Setup PostgreSQL database
- Enable HTTPS with SSL certificate
- Configure firewall (port 8000 or 443)

**Print Agents:**
- Install on each cashier PC
- Run as Windows Service (auto-start)
- Configure static IP for network printers
- Setup logging to file for troubleshooting

**Network:**
- Place all terminals in same VLAN
- Configure static IPs for stability
- Setup VPN for remote locations
- Monitor network latency

### 📈 Scaling

**Multiple Stores:**
```python
# Each store has unique terminal IDs
STORE_01: KASIR-01, KASIR-02, KITCHEN-01
STORE_02: KASIR-03, KASIR-04, KITCHEN-02
```

**Load Balancing:**
- Use reverse proxy (Nginx)
- Multiple Django instances
- Shared database (PostgreSQL)
- Redis for session/cache

### ✅ Advantages

1. **Centralized Management**
   - All data in one place
   - Easy reporting across stores
   - Single codebase to maintain

2. **Flexible Deployment**
   - Server can be cloud or on-premise
   - Agents work offline (queue when reconnects)
   - Mix USB and network printers

3. **Scalable**
   - Add terminals easily
   - No limit on printer count
   - Multi-store ready

4. **Reliable**
   - Print jobs queued in database
   - Auto-retry on failure
   - Error logging and monitoring

### 🆘 Support

For issues or questions:
1. Check agent logs in terminal
2. View print jobs in Django admin
3. Check server logs: `python manage.py runserver`
4. Test printer: `python -m escpos.cli list`
