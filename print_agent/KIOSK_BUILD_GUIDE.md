# 🏪 YOGYA POS - Kiosk Mode Build Guide

Complete guide untuk build dan deploy POS dalam mode kiosk (standalone executable).

## 📋 Prerequisites

### Software Requirements

- **Python 3.10+** (recommended: 3.12 atau 3.14)
- **pip** (Python package manager)
- **Visual C++ Redistributable** (untuk pywebview di Windows)

### Python Packages

```bash
pip install -r requirements.txt
```

**Core packages untuk kiosk build:**
- `pywebview >= 4.0` - Native webview window
- `pyinstaller >= 6.0` - Python to executable converter
- `bottle` - Lightweight WSGI micro web-framework
- `proxy_tools` - Proxy utilities

## 🔧 Installation Steps

### 1. Install pywebview

**Windows (recommended):**
```bash
# Install without optional dependencies (skip pythonnet)
pip install pywebview --no-deps
pip install bottle proxy_tools
```

**Alternative (if above works):**
```bash
pip install pywebview
```

**Note:** `pythonnet` dependency may fail to compile on Windows - it's optional and not required for basic functionality.

### 2. Verify Installation

```bash
python -c "import webview; print('pywebview version:', webview.__version__)"
```

Expected output:
```
pywebview version: 6.1
```

## 🏗️ Building Process

### Step 1: Navigate to print_agent folder

```bash
cd D:\YOGYA-Kiosk\pos-django-htmx-main\print_agent
```

### Step 2: Run build script

```bash
python build_pos_exe.py
```

**Build time:** 2-5 minutes depending on your system

**Expected output:**
```
======================================================================
🏗️  BUILDING YOGYA POS LAUNCHER
======================================================================
📂 Script directory: D:\YOGYA-Kiosk\pos-django-htmx-main\print_agent
📂 Project root: D:\YOGYA-Kiosk\pos-django-htmx-main
🧹 Cleaning build folder...

📦 Starting PyInstaller build...
⏳ This may take several minutes...

... (build process) ...

======================================================================
✅ BUILD SUCCESSFUL!
======================================================================

📍 Output: D:\YOGYA-Kiosk\pos-django-htmx-main\print_agent\dist\pos.exe

📊 Executable size: 41.1 MB
```

### Step 3: Verify build output

After successful build, check `print_agent/dist/` folder:

```
print_agent/dist/
  ├── pos.exe                      (41 MB) ✅ NEW
  ├── PrintAgent.exe               (existing)
  └── PrintAgentDashboard.exe      (existing)
```

## 📦 Deployment

### Step 1: Create deployment folder

```bash
mkdir YOGYA-POS
cd YOGYA-POS
```

### Step 2: Copy executables

Copy **ALL** files from `print_agent/dist/`:

```
YOGYA-POS/
  ├── pos.exe                      ← from print_agent/dist/
  ├── PrintAgent.exe               ← from print_agent/dist/
  └── PrintAgentDashboard.exe      ← from print_agent/dist/
```

### Step 3: Copy config and data files

From project root:

```
YOGYA-POS/
  ├── pos.exe
  ├── PrintAgent.exe
  ├── PrintAgentDashboard.exe
  ├── print_agent_config.json      ← from print_agent/
  ├── db.sqlite3                   ← from root (or create new)
  ├── media/                       ← from root (product images)
  └── static/                      ← from root (CSS, JS, images)
```

**Optional:** Create fresh database
```bash
cd YOGYA-POS
python -c "import django; django.setup(); from django.core.management import call_command; call_command('migrate')"
```

### Step 4: Configure printer (if needed)

Edit `print_agent_config.json`:

```json
{
  "terminal_id": "YOGYA-001",
  "printer_name": "Your Printer Name",
  "printer_type": "win32",
  "api_url": "http://localhost:8000",
  "poll_interval": 3
}
```

## 🚀 Running POS Kiosk

### Simple launch

```bash
# Double-click pos.exe
```

Or from command line:
```bash
cd YOGYA-POS
pos.exe
```

### What happens when you run pos.exe?

1. ✅ **Django server auto-starts** on port 8000 (background)
2. ✅ **Print dashboard auto-starts** on port 5050 (background)
3. ✅ **POS window opens** in fullscreen kiosk mode
4. ✅ **Auto-loads** http://localhost:8000/pos/

### Console output

```
============================================================
🏪 YOGYA POS KIOSK LAUNCHER
============================================================
🚀 Starting Django server...
⏳ Waiting for Django server to start...
✅ Django server started successfully!
🖨️  Starting Print Dashboard from PrintAgentDashboard.exe...
✅ Print Dashboard started successfully!

⏳ Initializing services...

🌐 Opening POS application...
============================================================
ℹ️  Press F11 for fullscreen toggle
ℹ️  Close window to exit application
============================================================
```

## 🔍 Troubleshooting

### Issue: "pywebview is not installed"

**Solution:**
```bash
pip install pywebview --no-deps
pip install bottle proxy_tools
```

### Issue: pythonnet compilation error

**This is NORMAL** - pythonnet is optional for .NET interop, not required.

**Solution 1 (Recommended):**
pos.exe has built-in fallback to default browser if pywebview fails.
No action needed - it will work automatically!

**Solution 2 (If you want native window):**
```bash
# Use Python 3.11 or earlier (pythonnet not compatible with Python 3.14)
pyenv install 3.11
pyenv local 3.11
pip install pywebview
```

**Solution 3 (Minimal install):**
```bash
pip install pywebview --no-deps
pip install bottle proxy_tools
# Will fall back to browser automatically
```

### Issue: "manage.py not found"

**Cause:** pos.exe is looking for Django files

**Solution:** Ensure folder structure is correct:
```
YOGYA-POS/
  ├── pos.exe
  ├── pos_fnb/           ← Django settings (embedded in exe)
  ├── apps/              ← Django apps (embedded in exe)
  ├── templates/         ← Templates (embedded in exe)
  ├── static/            ← Static files (MUST be present)
  └── db.sqlite3         ← Database
```

### Issue: Django server fails to start

**Check:**
1. Port 8000 is not in use: `netstat -ano | findstr :8000`
2. Database file exists: `db.sqlite3`
3. Static files exist: `static/` folder

**Solution:**
```bash
# Kill process on port 8000
taskkill /PID <PID> /F

# Create fresh database
python manage.py migrate
python manage.py setup_demo
```

### Issue: Print dashboard not found

**Cause:** PrintAgentDashboard.exe missing

**Solution:** Copy from `print_agent/dist/PrintAgentDashboard.exe`

### Issue: Window doesn't open in fullscreen

**Solution:** Press F11 or edit `pos_launcher.py`:
```python
window = webview.create_window(
    fullscreen=True,    # Change to True
    frameless=True,     # Remove window frame
)
```

Then rebuild:
```bash
python build_pos_exe.py
```

## 🎯 Testing Build

### Test 1: Django server
```bash
cd YOGYA-POS
# Open browser: http://localhost:8000
```

### Test 2: Print dashboard
```bash
# Open browser: http://localhost:5050
```

### Test 3: Full kiosk mode
```bash
# Run pos.exe and verify:
# ✓ Window opens fullscreen
# ✓ POS loads at localhost:8000/pos/
# ✓ Can create orders
# ✓ Can print receipts
```

## 📝 Build Customization

### Change window title

Edit `print_agent/pos_launcher.py`:
```python
window = webview.create_window(
    title='Your Company POS',  # Change this
    url='http://127.0.0.1:8000/pos/',
)
```

### Change icon

1. Create `icon.ico` file
2. Edit `build_pos_exe.py`:
```python
args = [
    '--icon=path/to/icon.ico',  # Add this
]
```

### Disable fullscreen by default

Edit `pos_launcher.py`:
```python
window = webview.create_window(
    fullscreen=False,  # Change to False
)
```

### Add splash screen

Edit `pos_launcher.py`:
```python
print("\n" + "="*60)
print("     WELCOME TO YOGYA POS")
print("     Version 1.0.0")
print("="*60 + "\n")
```

## 📊 Build Size Optimization

Current size: **41.1 MB**

### To reduce size:

1. **Exclude unused modules** in `build_pos_exe.py`:
```python
'--exclude-module=matplotlib',
'--exclude-module=numpy',
'--exclude-module=pandas',
'--exclude-module=test',
```

2. **Use UPX compression** (optional):
```bash
pip install pyinstaller[encryption]
```

Edit `build_pos_exe.py`:
```python
'--upx-dir=path/to/upx',
```

## 🔐 Security Notes

### Production deployment:

1. **Change SECRET_KEY** in Django settings
2. **Disable DEBUG** mode
3. **Use PostgreSQL** instead of SQLite
4. **Enable HTTPS** for production
5. **Set strong passwords** for admin accounts

### Create production build:

```bash
# Set environment variables
set DEBUG=False
set SECRET_KEY=your-secret-production-key

# Build
python build_pos_exe.py
```

## 📞 Support

For build issues, check:
1. Python version: `python --version`
2. Pip version: `pip --version`
3. PyInstaller version: `pyinstaller --version`
4. System PATH includes Python Scripts folder

## 🎓 References

- [pywebview documentation](https://pywebview.flowrl.com/)
- [PyInstaller documentation](https://pyinstaller.org/)
- [Django deployment guide](https://docs.djangoproject.com/en/stable/howto/deployment/)

---

**Build Date:** January 23, 2026  
**Version:** 1.0.0  
**Platform:** Windows 11
