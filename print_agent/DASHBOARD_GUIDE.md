# Print Agent Dashboard & Executable Guide

## 📊 Web-Based Dashboard

Dashboard untuk monitoring dan maintenance printer secara real-time via web browser.

### Features

✅ **Real-time Monitoring**
- Status printer (OK, Offline, Disconnected)
- Status agent (Running/Stopped dengan PID)
- Print history count
- Live logs (auto-refresh setiap 3 detik)

✅ **Maintenance Tools**
- Test Print - Cek printer dengan print test receipt
- Clear History - Hapus printed_jobs.json
- Refresh Status - Manual refresh data

✅ **User-Friendly**
- Modern UI dengan gradient background
- Color-coded status badges
- Responsive design
- Auto-refresh logs

---

## 🚀 Cara Menjalankan Dashboard

### Method 1: Python Script

```bash
cd D:\YOGYA-Kiosk\pos-django-htmx-main\print_agent
python dashboard.py
```

Atau double-click: `start_dashboard.bat`

**Access**: http://localhost:5050

### Method 2: Standalone Executable (Tanpa Python)

Setelah build executable:
```bash
cd dist
PrintAgentDashboard.exe
```

**Access**: http://localhost:5050

---

## 🏗️ Build Standalone Executable

**Tujuan**: Agent bisa jalan di komputer POS tanpa install Python.

### Step 1: Install PyInstaller

```bash
pip install -r requirements_dashboard.txt
```

### Step 2: Run Build Script

```bash
python build_executable.py
```

**Output**:
```
dist/
├── PrintAgent.exe              # Main agent executable
├── PrintAgentDashboard.exe     # Dashboard executable (optional)
├── print_agent_config.json     # Configuration
└── README.txt                  # Deployment guide
```

### Step 3: Deploy ke Komputer POS

1. Copy folder `dist/` ke komputer POS
2. Edit `print_agent_config.json`:
   - `terminal_id`: ID terminal (e.g., "POS-002")
   - `printer.name`: Nama printer Windows
   - `printer.brand`: Brand printer (HRPT, Epson, XPrinter)
3. Double-click `PrintAgent.exe`

**No Python installation required!** ✅

---

## 📋 Dashboard Features Detail

### 1. Printer Status Card

**Displays**:
- Printer status (OK/Offline/Disconnected)
- Printer name (e.g., TP808)
- Printer brand (e.g., HRPT)

**Actions**:
- **Test Print**: Print test receipt untuk validasi printer

### 2. Agent Status Card

**Displays**:
- Agent running status (Running/Stopped)
- Terminal ID
- Process ID (PID)

**Actions**:
- **Refresh**: Manual refresh semua status

### 3. Print History Card

**Displays**:
- Total jobs di history
- History file location

**Actions**:
- **Clear History**: Hapus printed_jobs.json (confirmation required)

### 4. Live Logs

**Features**:
- Last 50 log lines
- Auto-refresh toggle (default: ON, every 3s)
- Auto-scroll to bottom
- Monospace font untuk readability

---

## 🔧 API Endpoints

Dashboard menyediakan REST API:

### GET `/api/status`

Status lengkap sistem:
```json
{
  "timestamp": "2026-01-23T16:30:00",
  "terminal_id": "POS-001",
  "printer": {
    "name": "TP808",
    "brand": "HRPT",
    "status": "OK",
    "message": "Printer tersedia dan siap"
  },
  "agent": {
    "running": true,
    "pid": 12345
  },
  "jobs": {
    "history_count": 150
  }
}
```

### GET `/api/logs?lines=50`

Recent log entries:
```json
{
  "logs": [
    "2026-01-23 16:30:00 | INFO | [OK] Printed successfully",
    "..."
  ]
}
```

### POST `/api/test-print`

Test print receipt:
```json
{
  "success": true,
  "message": "Test print berhasil!"
}
```

### POST `/api/clear-history`

Clear printed jobs history:
```json
{
  "success": true,
  "message": "History berhasil dihapus"
}
```

---

## 💻 Development Mode

**Run dashboard in debug mode**:

```bash
python dashboard.py
```

Flask debug mode enabled (auto-reload on code changes).

---

## 📦 Deployment Checklist

### For Dev Environment (With Python)

- [x] Install dependencies: `pip install -r requirements_dashboard.txt`
- [x] Configure `print_agent_config.json`
- [x] Run dashboard: `python dashboard.py`
- [x] Run agent: `python agent_v2.py`
- [x] Access: http://localhost:5050

### For Production (POS Computers, No Python)

**Preparation**:
- [x] Run `python build_executable.py` on dev machine
- [x] Test executable locally

**Deployment**:
- [x] Copy `dist/` folder to POS computer
- [x] Edit `print_agent_config.json` untuk setiap terminal
- [x] Run `PrintAgent.exe` on startup
- [x] Run `PrintAgentDashboard.exe` untuk monitoring (optional)

---

## 🛠️ Troubleshooting

### Dashboard tidak bisa akses

**Check**:
1. Dashboard running? Look for: `Running on http://0.0.0.0:5050`
2. Port 5050 blocked? Try different port:
   ```python
   app.run(host='0.0.0.0', port=5051)
   ```
3. Firewall? Allow Python/executable through Windows Firewall

### Test Print tidak keluar

**Check**:
1. Printer status di dashboard: harus "OK"
2. Printer name di config match dengan Windows printer name
3. Printer cable terhubung dan powered on
4. Check Windows print queue: `Control Panel > Devices and Printers`

### Agent status "Stopped" tapi agent sedang running

**Solution**:
- Install `psutil`: `pip install psutil`
- Restart dashboard

### Build executable error

**Common issues**:
1. PyInstaller not installed: `pip install pyinstaller`
2. Path issues: Run build script dari print_agent directory
3. Missing dependencies: Install all requirements

---

## 🎨 Customization

### Change Dashboard Port

Edit `dashboard.py`:
```python
app.run(host='0.0.0.0', port=5555)  # Custom port
```

### Change UI Colors

Edit `templates/dashboard.html`:
```css
body {
    background: linear-gradient(135deg, #YOUR_COLOR 0%, #YOUR_COLOR 100%);
}
```

### Add Custom Maintenance Actions

Edit `dashboard.py`, tambahkan endpoint:
```python
@app.route('/api/your-action', methods=['POST'])
def your_action():
    # Your code here
    return jsonify({'success': True})
```

---

## 📊 System Requirements

### For Dashboard

- **Python**: 3.8+
- **OS**: Windows 10/11
- **RAM**: 50MB
- **Disk**: 10MB

### For Executable

- **OS**: Windows 10/11 (64-bit)
- **RAM**: 50MB
- **Disk**: 20MB (executable) + 10MB (runtime)
- **Python**: Not required! ✅

---

## 🚦 Status Codes

### Printer Status

| Status | Color | Meaning |
|--------|-------|---------|
| OK | Green | Printer ready |
| OFFLINE | Yellow | Printer offline atau digunakan app lain |
| USB_DISCONNECTED | Red | Printer tidak terhubung |
| ERROR | Red | Error lain |

### Agent Status

| Status | Color | Meaning |
|--------|-------|---------|
| Running | Green | Agent active |
| Stopped | Red | Agent not running |

---

## 📞 Support

**Need help?**
1. Check logs: `print_agent.log`
2. Check dashboard logs: Live logs section
3. Test printer manually: Windows Devices & Printers

---

## 🎯 Best Practices

1. **Always test executable locally** sebelum deploy
2. **Backup configuration** sebelum update
3. **Monitor logs regularly** untuk detect issues early
4. **Use dashboard** untuk quick health checks
5. **Run agent as Windows Service** untuk auto-start on boot (optional)

---

## 📝 Changelog

### v2.0 (January 23, 2026)
- ✅ Web-based dashboard
- ✅ Build executable support
- ✅ Real-time monitoring
- ✅ Maintenance tools (test print, clear history)
- ✅ Live logs dengan auto-refresh

---

**Made with ❤️ for easy deployment and monitoring**
