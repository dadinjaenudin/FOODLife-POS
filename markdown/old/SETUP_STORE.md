# EDGE SERVER SETUP GUIDE
### Quick run
| URL | Purpose | Run When |
|-----|---------|----------|
| `/setup/` | Edge Server setup (Company, Brand, Store) | **Once per Edge Server** |
| `/setup/terminal/` | Terminal registration | **Per terminal device** |
| `/setup/reset/` | Reset configuration (superuser) | When reconfiguring |

atau bisa pake script 
python reset_multi_tenant.py

## 🎯 Overview: Two-Phase Setup

## 📋 Phase 1: Edge Server Setup (One-Time)

### **Step 1: Reset Database (Optional - Fresh Start)**
```bash
python reset_multi_tenant.py
```
Type `RESET` to confirm deletion of all Company, Brand, Store data.

### **Step 2: Access Setup Wizard**
```
http://127.0.0.1:8000/setup/
```

### **Phase 1: Edge Server Configuration** (One-time)
**URL**: http://127.0.0.1:8000/setup/
**Purpose**: Configure Company ID, Brand ID, and Store for this Edge Server
**Run Once**: Setup dilakukan sekali per Edge Server

### **Phase 2: Terminal Registration** (Per Terminal)
**URL**: http://127.0.0.1:8000/setup/terminal/
**Purpose**: Register each POS/Tablet/Kiosk terminal
**Run Multiple**: Setup dilakukan di **masing-masing terminal** secara terpisah

---

### **Step 3: Create Company**
**Form Fields:**
- **Company Code**: YOGYA (uppercase, unique)
- **Company Name**: YOGYA DEPARTMENT STORE
- **Timezone**: Asia/Jakarta

**Result**: Company created, redirects to Brand setup

### **Step 4: Create Brand/Outlet**
**Form Fields:**
- **Brand Code**: YOGYA-001 (or YOGYA001)
- **Brand Name**: Ayam Geprek Express (your business concept)
- **Address**: Head office address
- **Phone**: Contact number
- **Tax ID**: NPWP (optional)
- **Tax Rate**: 11% (PPN)
- **Service Charge**: 5%

**Result**: Brand created, redirects to Store setup

### **Step 5: Configure Store**
**Form Fields:**
- **Select Brand**: Choose from dropdown (YOGYA-001)
- **Store Code**: YOGYA001-BSD (unique per store)
- **Store Name**: Cabang BSD City
- **Address**: Store physical address (optional)
- **Phone**: Store phone number (optional)

**Result**: ✅ **Edge Server Configured!** Shows status page.

---

## 💻 Phase 2: Terminal Registration (Per Terminal)

### **Important**: 
- **Dilakukan di MASING-MASING terminal** (POS, Tablet, Kiosk)
- Setiap device fisik harus register sendiri
- Bisa register banyak terminal untuk 1 store

### **How to Register Terminal:**

**1. Buka browser di terminal yang ingin diregister:**
```
http://127.0.0.1:8000/setup/terminal/
```

**2. Isi form registration:**
- **Terminal Code**: BSD-POS1 (unique per terminal)
- **Terminal Name**: Kasir 1
- **Device Type**: 
  - `pos` - Main cashier POS
  - `tablet` - Waiter tablet
  - `kiosk` - Self-service kiosk
  - `kitchen_display` - Kitchen display screen

**3. Submit form:**
- Terminal ID disimpan di browser session
- IP address dan device info otomatis tercatat
- Terminal siap digunakan untuk POS

### **Example: Multiple Terminals**
```
Terminal 1 (Kasir 1):
  http://192.168.1.10:8000/setup/terminal/
  Code: BSD-POS1, Name: Kasir 1, Type: pos

Terminal 2 (Kasir 2):
  http://192.168.1.11:8000/setup/terminal/
  Code: BSD-POS2, Name: Kasir 2, Type: pos

Terminal 3 (Waiter Tablet):
  http://192.168.1.12:8000/setup/terminal/
  Code: BSD-TAB1, Name: Tablet Waiter 1, Type: tablet

Terminal 4 (Kitchen Display):
  http://192.168.1.13:8000/setup/terminal/
  Code: BSD-KDS1, Name: Kitchen Display, Type: kitchen_display
```

---

## 🔄 Setup Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│         PHASE 1: EDGE SERVER (One-Time)                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Step 1: Create Company                                 │
│    └─> YOGYA DEPARTMENT STORE (YOGYA)                   │
│                                                          │
│  Step 2: Create Brand/Outlet                            │
│    └─> Ayam Geprek Express (YOGYA-001)                  │
│                                                          │
│  Step 3: Configure Store                                │
│    └─> Cabang BSD (YOGYA001-BSD)                        │
│                                                          │
│  ✅ Edge Server Ready                                    │
│                                                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│         PHASE 2: TERMINALS (Per Device)                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Terminal 1 (192.168.1.10):                             │
│    Register: BSD-POS1 (Kasir 1)                         │
│                                                          │
│  Terminal 2 (192.168.1.11):                             │
│    Register: BSD-POS2 (Kasir 2)                         │
│                                                          │
│  Terminal 3 (192.168.1.12):                             │
│    Register: BSD-TAB1 (Tablet Waiter 1)                 │
│                                                          │
│  Terminal 4 (192.168.1.13):                             │
│    Register: BSD-KDS1 (Kitchen Display)                 │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 🔐 URLs Summary

| URL | Purpose | Run When |
|-----|---------|----------|
| `/setup/` | Edge Server setup (Company, Brand, Store) | **Once per Edge Server** |
| `/setup/terminal/` | Terminal registration | **Per terminal device** |
| `/setup/reset/` | Reset configuration (superuser) | When reconfiguring |

---

## ✅ Verification

### **Check Edge Server Configuration:**
```
http://127.0.0.1:8000/setup/
```
Should show status page with:
- ✅ Company: YOGYA DEPARTMENT STORE
- ✅ Brand: Ayam Geprek Express  
- ✅ Store: Cabang BSD
- 📋 List of registered terminals

### **Check Terminal Registration:**
```python
from apps.core.models import POSTerminal
terminals = POSTerminal.objects.all()
for t in terminals:
    print(f"{t.terminal_code}: {t.terminal_name} ({t.device_type})")
```

---

## 📝 Best Practices

### **Edge Server Setup:**
✅ DO:
- Run setup once per physical store location
- Use descriptive store codes (e.g., YOGYA001-BSD, not STORE1)
- Document company/brand/store hierarchy

❌ DON'T:
- Create multiple stores on same Edge Server (singleton pattern)
- Use same store code for different locations

### **Terminal Registration:**
✅ DO:
- Register each physical device separately
- Use location-based terminal codes (BSD-POS1, BSD-POS2)
- Register terminals from their actual IP addresses
- Keep terminal codes unique across all stores

❌ DON'T:
- Share terminal IDs between devices
- Register all terminals from one computer
- Use generic names like "POS1", "POS2" (add location prefix)

---


