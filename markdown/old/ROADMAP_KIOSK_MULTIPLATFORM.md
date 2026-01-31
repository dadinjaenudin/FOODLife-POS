# 🗺️ ROADMAP: YOGYA POS Multi-Platform Kiosk

**Tanggal Dibuat:** 24 Januari 2026  
**Strategi:** Hybrid Approach (Desktop Native + Mobile PWA)  
**Platform Priority:** Windows → Linux → Mobile (PWA)

---

## 📋 RINGKASAN ARSITEKTUR

### Strategi 1: Hybrid Approach ✅ SELECTED

```
┌─────────────────────────────────────────────────────────┐
│                    YOGYA POS ECOSYSTEM                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  DESKTOP (Windows/Linux)                                │
│  ├── pos.exe / pos (PyInstaller + PyWebView)           │
│  ├── PrintAgent.exe (Separate service)                 │
│  ├── config.json (Unified configuration)               │
│  └── Full hardware access (printer, scanner, etc)      │
│                                                         │
│  MOBILE/TABLET (Android/iOS)                            │
│  ├── PWA (Progressive Web App)                         │
│  ├── API-only access                                   │
│  ├── No printer (cloud print atau bluetooth)           │
│  └── Responsive UI                                     │
│                                                         │
│  SERVER (Django Backend)                                │
│  ├── API endpoints untuk validasi                      │
│  ├── WebSocket untuk real-time updates                 │
│  └── Terminal management & authentication               │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 FASE 1: FOUNDATION (WINDOWS-FIRST)

### 1.1 Unified JSON Configuration ✅ HIGH PRIORITY

**File:** `config.json` (menggantikan `terminal-config.json` + `print_agent_config.json`)

**Struktur:**
```json
{
  "_comment": "Unified POS Configuration - Terminal + Printer + Kiosk",
  "version": "1.0",
  
  "terminal": {
    "terminal_code": "KIOSK-001",
    "terminal_name": "Kasir Depan 1",
    "terminal_type": "cashier",
    "brand_code": "AYAMGEPREK",
    "store_code": null,
    "company_code": null,
    "location": "Ground Floor - Front",
    "station_name": "Kasir 1"
  },
  
  "device": {
    "device_id": null,
    "ip_address": null,
    "mac_address": null,
    "hostname": null,
    "os": null,
    "registered_at": null
  },
  
  "printer": {
    "receipt_printer": {
      "enabled": true,
      "type": "win32",
      "name": "TP808",
      "brand": "HRPT",
      "model": "TP808-Thermal-80",
      "paper_width": 80,
      "auto_cut": true,
      "test_mode": false,
      "config": {
        "timeout": 30,
        "retry_on_error": true
      }
    },
    "kitchen_printer": {
      "enabled": true,
      "source": "server"
    }
  },
  
  "print_agent": {
    "enabled": true,
    "printer_role": "cashier",
    "job_types_accepted": [
      "receipt",
      "reprint",
      "report"
    ],
    "poll_interval": 2,
    "heartbeat_interval": 30,
    "error_handling": {
      "max_retry": 3,
      "backoff_seconds": [5, 10, 30],
      "critical_errors": [
        "PRINTER_OFFLINE",
        "USB_DISCONNECTED"
      ]
    }
  },
  
  "server": {
    "url": "http://localhost:8000",
    "api_endpoint": "/api/v1",
    "websocket_url": "ws://localhost:8000/ws",
    "api_key": null,
    "timeout": 30,
    "ssl_verify": true
  },
  
  "kiosk_mode": {
    "enabled": false,
    "fullscreen": true,
    "disable_navigation": true,
    "disable_right_click": true,
    "idle_timeout": 120,
    "home_url": "/pos/",
    "screensaver_url": "/qr-order/"
  },
  
  "security": {
    "require_validation": true,
    "validated": false,
    "validation_token": null,
    "last_validated": null,
    "auto_login": false
  },
  
  "ui": {
    "theme": "default",
    "language": "id",
    "font_size": "medium",
    "show_keyboard": false
  },
  
  "logging": {
    "level": "INFO",
    "log_file": "pos_kiosk.log",
    "max_size_mb": 10,
    "backup_count": 5,
    "print_agent_log": "print_agent.log"
  }
}
```

**Tasks:**
- [ ] Buat class `ConfigManager` untuk read/write config.json
- [ ] Migration dari `terminal_config.py` ke `ConfigManager`
- [ ] Migration dari `print_agent_config.json` ke unified config
- [ ] Validasi schema config.json (JSON Schema)
- [ ] Unit tests untuk ConfigManager

**Kitchen Printer (Database-Based):**
- [ ] Extend `KitchenPrinterConfig` model (network printers)
  - Fields: brand, station, name, ip_address, port, is_active, priority, backup_printer
- [ ] Add `kitchen_station` field to Product model (main, bar, grill, dessert)
- [ ] Create API endpoint `/api/v1/kitchen/printer/` untuk fetch config
- [ ] Routing logic: Group items by station → Fetch printer from DB → Create print job

---

### 1.2 Setup UI dalam WebView ✅ HIGH PRIORITY

**Opsi A: Setup via Django Template (RECOMMENDED)**

**Flow:**
```
pos.exe startup
    ↓
Load config.json
    ↓
config.validated == false?
    ↓ YES
Open WebView → http://localhost:8000/setup/
    ↓
User fills: company_id, store_id, terminal_id, printer
    ↓
Submit → Validate to server
    ↓
Server returns: validation_token + config
    ↓
Save to config.json (validated=true)
    ↓
Restart → Main POS WebView
```

**Django URLs to Create:**
```python
# apps/core/urls.py
urlpatterns = [
    path('setup/', views_setup.setup_wizard, name='setup_wizard'),
    path('setup/step1/', views_setup.step1_terminal_info, name='setup_step1'),
    path('setup/step2/', views_setup.step2_printer_config, name='setup_step2'),
    path('setup/step3/', views_setup.step3_validation, name='setup_step3'),
    path('setup/complete/', views_setup.setup_complete, name='setup_complete'),
    
    # API untuk validasi
    path('api/v1/terminal/validate/', views_setup.validate_terminal, name='api_validate_terminal'),
]
```

**Templates to Create:**
```
templates/core/setup/
├── wizard.html           # Main setup wizard layout
├── step1_terminal.html   # Company, Store, Terminal ID
├── step2_printer.html    # Printer selection & test
├── step3_validation.html # Server validation
└── complete.html         # Setup success
```

**Tasks:**
- [ ] Create `views_setup.py` dengan setup wizard logic
- [ ] Create setup templates (responsive, kiosk-friendly)
- [ ] Implement API endpoint `/api/v1/terminal/validate/`
- [ ] JavaScript untuk submit form via AJAX
- [ ] Loading states & error handling
- [ ] Printer test functionality (send test print)

---

### 1.3 Server-Side Validation ✅ HIGH PRIORITY

**API Endpoint:** `POST /api/v1/terminal/validate/`

**Request:**
```json
{
  "terminal_code": "KIOSK-001",
  "terminal_type": "cashier",
  "brand_code": "AYAMGEPREK",
  "device_info": {
    "ip_address": "192.168.1.100",
    "mac_address": "00:1B:44:11:3A:B7",
    "hostname": "KASIR-PC-01",
    "os": "Windows 10 Pro"
  },
  "printer_name": "TP808"
}
```

**Response (Success):**
```json
{
  "valid": true,
  "validation_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "terminal": {
    "terminal_code": "KIOSK-001",
    "terminal_name": "Kasir Depan 1",
    "brand_code": "AYAMGEPREK",
    "brand_name": "Ayam Geprek Boedjangan",
    "store_code": "YGY-BSD",
    "store_name": "Yogyakarta BSD",
    "company_code": "YOGYA",
    "company_name": "YOGYA Group"
  },
  "device_assignment": {
    "device_id": "dev_abc123",
    "assigned_at": "2026-01-24T10:30:00Z",
    "ip_address": "192.168.1.100",
    "status": "active"
  },
  "permissions": [
    "pos.create_transaction",
    "pos.print_receipt",
    "pos.refund"
  ],
  "config": {
    "receipt_printer": {
      "name": "TP808",
      "paper_width": 80,
      "logo_url": "/media/company/logo.png"
    }
  }
}
```

**Response (Error - Terminal Not Found):**
```json
{
  "valid": false,
  "error": "TERMINAL_NOT_FOUND",
  "message": "Terminal 'KIOSK-001' tidak terdaftar di brand 'AYAMGEPREK'",
  "suggestion": "Terminal harus didaftarkan dulu di edge server. Hubungi administrator."
}
```

**Response (Error - Already Assigned):**
```json
{
  "valid": false,
  "error": "TERMINAL_ALREADY_ASSIGNED",
  "message": "Terminal 'KIOSK-001' sudah di-assign ke device lain",
  "current_assignment": {
    "device_id": "dev_xyz789",
    "ip_address": "192.168.1.50",
    "hostname": "KASIR-PC-02",
    "assigned_at": "2026-01-20T08:15:00Z"
  },
  "suggestion": "Terminal ini sudah digunakan di device lain. Unassign dulu atau gunakan terminal code berbeda."
}
```

**Response (Error - Brand Mismatch):**
```json
{
  "valid": false,
  "error": "BRAND_NOT_FOUND",
  "message": "Brand 'BAKSO' tidak ada di edge server ini",
  "available_brands": ["AYAMGEPREK", "NASGORENG", "MIEAYAM"],
  "suggestion": "Pastikan brand_code sesuai dengan brand yang ada di server ini"
}
```

**Server-Side Logic:**

**Tasks:**
- [ ] Extend `Terminal` model (existing model):
  - Add: `terminal_code` (CharField, unique)
  - Add: `brand` (ForeignKey to Brand)
  - Add: `device_id` (CharField, nullable - for assignment tracking)
  - Add: `device_ip` (GenericIPAddressField, nullable)
  - Add: `device_mac` (CharField, nullable)
  - Add: `device_hostname` (CharField, nullable)
  - Add: `assigned_at` (DateTimeField, nullable)
  - Add: `last_seen` (DateTimeField - for health monitoring)
- [ ] Create API view `validate_terminal()`
- [ ] Generate JWT token untuk terminal authentication
- [ ] Validation logic:
  1. **Get singleton store** from edge server (Store.get_current())
  2. **Check brand exists** in this edge server
  3. **Check terminal exists** with terminal_code + brand
  4. **Check terminal is active**
  5. **Check terminal assignment:**
     - If device_id is NULL → assign to this device (first-time setup)
     - If device_id matches current device → OK (same device re-validating)
     - If device_id different → ERROR: already assigned to another device
  6. **Extract device info:** IP, MAC, hostname from request
  7. **Update terminal assignment:** device_id, device_ip, assigned_at, last_seen
- [ ] Logging untuk audit trail (who, when, from where)
- [ ] Rate limiting untuk security (max 5 attempts per minute)

---

### 1.4 POS Launcher Enhancement

**Update:** `print_agent/pos_launcher.py`

**New Features:**
```python
class POSLauncher:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load()
        
    def start(self):
        # 1. Check config.json exists
        if not self.config_manager.exists():
            self.first_time_setup()
            
        # 2. Load config
        self.config = self.config_manager.load()
        
        # 3. Check if validated
        if not self.config['security']['validated']:
            self.run_setup_wizard()
        else:
            # Check if token still valid
            if not self.validate_token():
                self.run_setup_wizard()
            else:
                self.run_main_app()
    
    def first_time_setup(self):
        """Create default config.json"""
        self.config_manager.create_default()
        
    def run_setup_wizard(self):
        """Open Django setup wizard in webview"""
        self.start_django_server()
        self.open_webview(url="http://localhost:8000/setup/")
        
    def run_main_app(self):
        """Open main POS application"""
        self.start_django_server()
        
        if self.config['kiosk_mode']['enabled']:
            self.open_kiosk_mode()
        else:
            self.open_webview(url=self.config['kiosk_mode']['home_url'])
```

**Tasks:**
- [ ] Implement `ConfigManager` class
- [ ] Update `pos_launcher.py` dengan startup flow baru
- [ ] Handle Django server startup (check port availability)
- [ ] Handle webview creation (PyWebView configuration)
- [ ] Error handling & logging
- [ ] Graceful shutdown

---

## 🎯 FASE 2: PRINT AGENT INTEGRATION

### 2.1 Unified Config untuk Print Agent

**Goal:** Print Agent baca dari `config.json` yang sama

**Receipt Printer (Local - from config.json):**
- [ ] Update `print_agent/agent_v2.py` untuk baca `config.json`
- [ ] Map receipt printer config dari unified config
- [ ] Backward compatibility (if needed)

**Kitchen Printer (Network - from Database):**
- [ ] Print Agent fetch kitchen printer config dari server API
- [ ] Support network printer (IP + port)
- [ ] Implement retry & fallback logic (primary → backup printer)
- [ ] Health monitoring (track success/error count)

**Kitchen Printer Flow:**
```
1. Setup (Django Admin):
   ├── Create KitchenPrinterConfig
   │   ├── Brand: AYAMGEPREK
   │   ├── Station: bar
   │   ├── IP: 192.168.1.102
   │   └── Port: 9100
   └── Update Product
       └── "Es Teh" → kitchen_station = "bar"

2. Terminal Runtime (config.json):
   ├── kitchen_printer.enabled = true
   └── kitchen_printer.source = "server"

3. Order Flow:
   Order "Es Teh" → Send to kitchen
       ↓
   Django: Product.kitchen_station = "bar"
       ↓
   Fetch: KitchenPrinterConfig(brand, station="bar")
       → Result: IP=192.168.1.102, Port=9100
       ↓
   Create PrintJob in Queue
       ↓
   Print Agent: Pick job → Send to 192.168.1.102:9100
       ↓
   Update job status (success/failed)
       ↓
   If failed: Retry 3x → Try backup_printer → Alert admin
```

**Benefits:**
- ✅ Terminal config minimal (hanya enable/disable)
- ✅ Kitchen printer centralized di database
- ✅ Update IP tanpa redeploy terminal
- ✅ Support multi-station (bar, grill, main, dessert)
- ✅ Automatic fallback & retry

---

### 2.2 Print Agent Auto-Discovery

**Goal:** POS launcher auto-detect & start print agent

**Flow:**
```
pos.exe startup
    ↓
Check config.printer.enabled
    ↓ YES
Check PrintAgent.exe exists in same directory
    ↓ YES
Start PrintAgent.exe as subprocess
    ↓
Monitor PrintAgent status
```

**Tasks:**
- [ ] Process management untuk PrintAgent
- [ ] Auto-restart on crash
- [ ] Health check endpoint
- [ ] Status indicator di UI

---

## 🎯 FASE 3: KIOSK MODE ENHANCEMENT

### 3.1 Kiosk Mode Features

**Features:**
- [ ] Fullscreen mode (no window border)
- [ ] Disable keyboard shortcuts (Alt+F4, Ctrl+W, etc)
- [ ] Disable right-click context menu
- [ ] Auto-restart on crash
- [ ] Idle timeout → return to home screen
- [ ] Screensaver mode

**Implementation:**
```python
# pos_launcher.py
def open_kiosk_mode(self):
    webview.create_window(
        title="YOGYA POS Kiosk",
        url=self.config['kiosk_mode']['home_url'],
        fullscreen=self.config['kiosk_mode']['fullscreen'],
        frameless=True,  # No window border
        easy_drag=False,  # Disable drag
        confirm_close=True,  # Prevent accidental close
        js_api=KioskAPI(self)  # Custom JS API
    )
```

---

## 🎯 FASE 4: WINDOWS DEPLOYMENT

### 4.1 Build Process

**PyInstaller Configuration:**
```python
# build_pos_exe.py
PyInstaller.__main__.run([
    'pos_launcher.py',
    '--name=YOGYA-POS',
    '--onefile',
    '--windowed',  # No console window
    '--icon=assets/icon.ico',
    '--add-data=config.json.example;.',
    '--add-data=static;static',
    '--add-data=templates;templates',
    '--hidden-import=win32print',
    '--hidden-import=webview',
])
```

**Tasks:**
- [ ] Update `build_pos_exe.py`
- [ ] Include default config.json.example
- [ ] Include assets (icons, images)
- [ ] Test on clean Windows machine
- [ ] Create installer (NSIS or Inno Setup)

---

### 4.2 Installer Features

**Installer Should:**
- [ ] Install WebView2 Runtime (if not exists)
- [ ] Create desktop shortcut
- [ ] Create Start Menu entry
- [ ] Set auto-start on boot (optional)
- [ ] Create `config.json` from template
- [ ] Ask for server URL during installation

---

## 🎯 FASE 5: LINUX SUPPORT

### 5.1 Linux Build

**Platform Differences:**
```python
# platform_utils.py
import platform

def get_printer_driver():
    if platform.system() == "Windows":
        return "win32"
    elif platform.system() == "Linux":
        return "cups"
    else:
        return "unknown"
```

**Tasks:**
- [ ] Test PyWebView on Linux (GTK backend)
- [ ] Test printer support (CUPS)
- [ ] Build on Linux VM
- [ ] Create .deb package (Debian/Ubuntu)
- [ ] Create .rpm package (RedHat/Fedora)
- [ ] Test on different distros

---

### 5.2 Linux-Specific Config

**config.json additions:**
```json
{
  "printer": {
    "receipt_printer": {
      "driver": "cups",  // auto-detect based on OS
      "cups_printer_name": "TP808",
      "cups_server": "localhost:631"
    }
  }
}
```

---

## 🎯 FASE 6: MOBILE PWA

### 6.1 Progressive Web App Setup

**Features:**
- [ ] Service Worker untuk offline support
- [ ] App manifest untuk "Add to Home Screen"
- [ ] Responsive design (mobile-first)
- [ ] Touch-friendly UI
- [ ] Camera access (QR scan)
- [ ] Push notifications

**Files to Create:**
```
static/
├── manifest.json
├── service-worker.js
└── icons/
    ├── icon-192.png
    └── icon-512.png
```

---

### 6.2 Mobile-Specific Features

**UI Adaptations:**
- [ ] Bottom navigation (instead of sidebar)
- [ ] Larger touch targets
- [ ] Swipe gestures
- [ ] Pull-to-refresh
- [ ] Haptic feedback

**API Enhancements:**
- [ ] Mobile authentication (QR code login)
- [ ] Simplified transaction flow
- [ ] Cloud print integration (optional)

---

## 📊 PRIORITAS & TIMELINE

### Sprint 1: Foundation (2 minggu)
- ✅ Unified JSON Config
- ✅ ConfigManager implementation
- ✅ Setup wizard UI
- ✅ Server validation API

### Sprint 2: Integration (1 minggu)
- ✅ POS Launcher update
- ✅ Print Agent integration
- ✅ Testing & bug fixes

### Sprint 3: Windows Deployment (1 minggu)
- ✅ Build process refinement
- ✅ Installer creation
- ✅ Documentation
- ✅ User acceptance testing

### Sprint 4: Kiosk Mode (1 minggu)
- ✅ Kiosk features implementation
- ✅ Security hardening
- ✅ Testing

### Sprint 5: Linux Support (2 minggu)
- ✅ Linux build & testing
- ✅ Package creation
- ✅ Cross-platform testing

### Sprint 6: Mobile PWA (2 minggu)
- ✅ PWA setup
- ✅ Mobile UI redesign
- ✅ Testing on devices

**Total Estimasi:** 9 minggu (2.25 bulan)

---

## ✅ SUCCESS METRICS

### Technical:
- [ ] Single executable < 100MB
- [ ] Startup time < 5 seconds
- [ ] Config validation < 500ms
- [ ] Zero-touch deployment (minimal setup)
- [ ] 99.9% uptime (auto-restart on crash)

### User Experience:
- [ ] Setup wizard < 3 minutes
- [ ] No technical knowledge required
- [ ] Clear error messages
- [ ] Multi-language support

### Platform Coverage:
- [ ] Windows 10/11 support
- [ ] Ubuntu 20.04+ support
- [ ] Mobile browser (Chrome, Safari)

---

## 🚨 RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| PyInstaller size bloat | HIGH | Use --exclude-module, optimize dependencies |
| Cross-platform bugs | HIGH | Extensive testing on each platform |
| WebView2 not installed | MEDIUM | Auto-install in installer |
| Printer driver issues | HIGH | Provide driver detection & troubleshooting guide |
| Network validation fails | MEDIUM | Offline mode with manual activation code |

---

## 📝 NOTES

- **Config Schema Version:** Include version field untuk future migrations
- **Backward Compatibility:** Support old config format selama migration period
- **Security:** Store validation token encrypted (not plaintext)
- **Logging:** Comprehensive logging untuk troubleshooting
- **Documentation:** User manual + admin guide + developer docs

---

## 🔄 FUTURE ENHANCEMENTS

- [ ] Auto-update mechanism
- [ ] Cloud config sync
- [ ] Multi-terminal management dashboard
- [ ] A/B testing framework
- [ ] Analytics integration
- [ ] Backup & restore functionality

---

**Status:** 📋 ROADMAP READY FOR REVIEW  
**Next Step:** Review & approval → Start Sprint 1  
**Contact:** Development Team
