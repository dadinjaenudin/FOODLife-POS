# 🏢 EDGE SERVER ARCHITECTURE

**Updated:** 24 Januari 2026  
**Scope:** Multi-Brand Edge Server with Terminal Assignment Tracking

---

## 🎯 **EDGE SERVER TOPOLOGY**

### **Confirmed Architecture:**

```
┌─────────────────────────────────────────────────────────────┐
│              SINGLE EDGE SERVER (per Location)              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ✅ 1 COMPANY (SINGLETON)                                   │
│     └── YOGYA Group                                         │
│                                                             │
│  ✅ 1 STORE (SINGLETON)                                     │
│     └── Yogya BSD Store                                     │
│                                                             │
│  ✅ MULTIPLE BRANDS (N brands in 1 store)                   │
│     ├── Brand: AYAMGEPREK                                   │
│     │   ├── Terminal: KIOSK-GEPREK-01 → Device: PC-01      │
│     │   ├── Terminal: KASIR-GEPREK-01 → Device: PC-02      │
│     │   └── Terminal: KITCHEN-GEPREK  → Device: TABLET-01  │
│     │                                                       │
│     ├── Brand: NASGORENG                                    │
│     │   ├── Terminal: KIOSK-NASGR-01  → Device: PC-03      │
│     │   └── Terminal: KASIR-NASGR-01  → Device: PC-04      │
│     │                                                       │
│     └── Brand: MIEAYAM                                      │
│         ├── Terminal: KIOSK-MIE-01    → Device: PC-05      │
│         └── Terminal: KASIR-MIE-01    → Device: PC-06      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**KEY POINTS:**
- ✅ **1 Edge Server** = 1 Physical Location (e.g., BSD Mall)
- ✅ **1 Company per Edge** = Company data replicated/singleton
- ✅ **1 Store per Edge** = Store.get_current() always returns same store
- ✅ **Multiple Brands per Edge** = Different F&B concepts in same food court
- ✅ **Terminal Assignment** = Each terminal can only be assigned to 1 device

---

## 🔐 **TERMINAL ASSIGNMENT LOGIC**

### **Scenario 1: First-Time Setup (Terminal Belum Di-Assign)**

```python
# Client Request
POST /api/v1/terminal/validate/
{
    "terminal_code": "KIOSK-GEPREK-01",
    "brand_code": "AYAMGEPREK",
    "device_info": {
        "ip_address": "192.168.1.100",
        "mac_address": "00:1B:44:11:3A:B7",
        "hostname": "KASIR-PC-01"
    }
}

# Server Logic
terminal = Terminal.objects.get(
    terminal_code="KIOSK-GEPREK-01",
    brand__code="AYAMGEPREK"
)

# Check: device_id is NULL (belum di-assign)
if terminal.device_id is None:
    # ✅ ASSIGN to this device
    terminal.device_id = generate_device_id()  # "dev_abc123"
    terminal.device_ip = "192.168.1.100"
    terminal.device_mac = "00:1B:44:11:3A:B7"
    terminal.device_hostname = "KASIR-PC-01"
    terminal.assigned_at = timezone.now()
    terminal.last_seen = timezone.now()
    terminal.save()
    
    return {
        "valid": True,
        "message": "Terminal assigned successfully",
        "device_id": "dev_abc123"
    }
```

### **Scenario 2: Re-Validation (Same Device)**

```python
# Client Request (same device, re-validating after restart)
POST /api/v1/terminal/validate/
{
    "terminal_code": "KIOSK-GEPREK-01",
    "brand_code": "AYAMGEPREK",
    "device_info": {
        "device_id": "dev_abc123",  # Same device_id dari sebelumnya
        "ip_address": "192.168.1.100",
        "mac_address": "00:1B:44:11:3A:B7",
        "hostname": "KASIR-PC-01"
    }
}

# Server Logic
terminal = Terminal.objects.get(terminal_code="KIOSK-GEPREK-01")

# Check: device_id matches
if terminal.device_id == request.data['device_info']['device_id']:
    # ✅ SAME DEVICE - just update last_seen
    terminal.device_ip = "192.168.1.100"  # May have changed (DHCP)
    terminal.last_seen = timezone.now()
    terminal.save()
    
    return {
        "valid": True,
        "message": "Terminal re-validated successfully"
    }
```

### **Scenario 3: Already Assigned to Another Device** ⚠️

```python
# Client Request (different device trying to use same terminal)
POST /api/v1/terminal/validate/
{
    "terminal_code": "KIOSK-GEPREK-01",
    "brand_code": "AYAMGEPREK",
    "device_info": {
        "device_id": "dev_xyz789",  # DIFFERENT device_id
        "ip_address": "192.168.1.200",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "hostname": "KASIR-PC-99"
    }
}

# Server Logic
terminal = Terminal.objects.get(terminal_code="KIOSK-GEPREK-01")

# Check: device_id different
if terminal.device_id and terminal.device_id != "dev_xyz789":
    # ❌ ERROR: Already assigned to another device
    return {
        "valid": False,
        "error": "TERMINAL_ALREADY_ASSIGNED",
        "message": f"Terminal '{terminal.terminal_code}' sudah di-assign ke device lain",
        "current_assignment": {
            "device_id": terminal.device_id,
            "ip_address": terminal.device_ip,
            "hostname": terminal.device_hostname,
            "assigned_at": terminal.assigned_at.isoformat(),
            "last_seen": terminal.last_seen.isoformat()
        },
        "suggestion": "Unassign terminal dari device lama dulu, atau gunakan terminal code berbeda"
    }
```

### **Scenario 4: Brand Not Found in Edge Server**

```python
# Client Request
POST /api/v1/terminal/validate/
{
    "terminal_code": "KIOSK-BAKSO-01",
    "brand_code": "BAKSO",  # Brand tidak ada di edge server ini
    "device_info": {...}
}

# Server Logic
store = Store.get_current()
brands = store.brand.company.brands.filter(is_active=True)

if not brands.filter(code="BAKSO").exists():
    return {
        "valid": False,
        "error": "BRAND_NOT_FOUND",
        "message": "Brand 'BAKSO' tidak ada di edge server ini",
        "available_brands": list(brands.values_list('code', flat=True)),
        "suggestion": "Pastikan brand_code sesuai dengan brand yang ada"
    }
```

---

## 📊 **TERMINAL MODEL STRUCTURE**

### **Existing Terminal Model (to be Extended)**

```python
# apps/core/models.py

class Terminal(models.Model):
    """
    POS Terminal - Can be assigned to physical device
    Multiple terminals per brand (1 brand can have many terminals)
    """
    # Core Identity
    terminal_code = models.CharField(
        max_length=50, 
        unique=True,
        help_text="Unique terminal code (e.g., KIOSK-GEPREK-01)"
    )
    terminal_name = models.CharField(max_length=200)
    terminal_type = models.CharField(
        max_length=20,
        choices=[
            ('cashier', 'Kasir'),
            ('kiosk', 'Self-Service Kiosk'),
            ('kitchen', 'Kitchen Display'),
            ('waiter', 'Waiter Handheld'),
        ],
        default='cashier'
    )
    
    # Relationships
    brand = models.ForeignKey(
        'Brand', 
        on_delete=models.PROTECT, 
        related_name='terminals'
    )
    store = models.ForeignKey(
        'Store',
        on_delete=models.PROTECT,
        related_name='terminals',
        help_text="Auto-set to Store.get_current() on edge server"
    )
    
    # Device Assignment (NEW)
    device_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        unique=True,
        help_text="Unique device identifier (generated on first assignment)"
    )
    device_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Last known IP address"
    )
    device_mac = models.CharField(
        max_length=17,
        null=True,
        blank=True,
        help_text="MAC address (format: 00:1B:44:11:3A:B7)"
    )
    device_hostname = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Computer hostname"
    )
    device_os = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="OS info (e.g., Windows 10 Pro)"
    )
    assigned_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When terminal was first assigned to device"
    )
    last_seen = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last validation/heartbeat timestamp"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'core_terminal'
        ordering = ['brand', 'terminal_code']
        indexes = [
            models.Index(fields=['brand', 'terminal_code']),
            models.Index(fields=['device_id']),
        ]
    
    def __str__(self):
        return f"{self.brand.name} - {self.terminal_name} ({self.terminal_code})"
    
    def is_assigned(self):
        """Check if terminal is assigned to a device"""
        return self.device_id is not None
    
    def unassign(self):
        """Unassign terminal from current device"""
        self.device_id = None
        self.device_ip = None
        self.device_mac = None
        self.device_hostname = None
        self.device_os = None
        self.assigned_at = None
        self.save()
    
    def is_online(self, timeout_minutes=5):
        """Check if terminal is currently online (last_seen within timeout)"""
        if not self.last_seen:
            return False
        return (timezone.now() - self.last_seen).total_seconds() < (timeout_minutes * 60)
```

---

## 🔑 **DEVICE ID GENERATION**

### **Strategy: Hybrid Identifier**

```python
import hashlib
import uuid
from datetime import datetime

def generate_device_id(mac_address, hostname, ip_address):
    """
    Generate unique device ID based on hardware info
    Format: dev_[8-char-hash]
    
    Example: dev_a1b2c3d4
    """
    # Combine hardware identifiers
    unique_string = f"{mac_address}_{hostname}_{ip_address}_{uuid.uuid4()}"
    
    # Hash to create stable ID
    hash_obj = hashlib.sha256(unique_string.encode())
    device_hash = hash_obj.hexdigest()[:8]
    
    return f"dev_{device_hash}"

# Usage in validation:
device_id = generate_device_id(
    mac_address="00:1B:44:11:3A:B7",
    hostname="KASIR-PC-01",
    ip_address="192.168.1.100"
)
# Result: "dev_a1b2c3d4"
```

**Alternative: Simple UUID**
```python
def generate_device_id():
    return f"dev_{uuid.uuid4().hex[:12]}"
```

---

## 🛠️ **SETUP WIZARD FLOW (Updated)**

### **Step 1: Input Terminal Info**

```
┌─────────────────────────────────────┐
│     Terminal Setup - Step 1/3      │
├─────────────────────────────────────┤
│                                     │
│  Brand Code: [AYAMGEPREK      ]    │
│              ↑ Manual input         │
│                                     │
│  Terminal Code: [KIOSK-GEPREK-01]  │
│                 ↑ Manual input      │
│                                     │
│  Terminal Type: [Cashier ▼]        │
│                                     │
│  [Next →]                           │
└─────────────────────────────────────┘
```

**JavaScript:**
```javascript
// Auto-detect device info
const deviceInfo = {
    hostname: await getHostname(),
    os: navigator.platform,
    screen: `${screen.width}x${screen.height}`
};

// IP & MAC will be detected server-side from request
```

### **Step 2: Printer Configuration**

```
┌─────────────────────────────────────┐
│     Terminal Setup - Step 2/3      │
├─────────────────────────────────────┤
│                                     │
│  Receipt Printer: [TP808      ▼]   │
│  Paper Width: [80mm ▼]              │
│                                     │
│  [Test Print]  [Next →]             │
└─────────────────────────────────────┘
```

### **Step 3: Validation**

```
┌─────────────────────────────────────┐
│     Terminal Setup - Step 3/3      │
├─────────────────────────────────────┤
│                                     │
│  ⏳ Validating with server...       │
│                                     │
│  Brand: AYAMGEPREK                  │
│  Terminal: KIOSK-GEPREK-01          │
│  Device: KASIR-PC-01                │
│  IP: 192.168.1.100                  │
│                                     │
│  [Validating...]                    │
└─────────────────────────────────────┘
```

**Success:**
```
┌─────────────────────────────────────┐
│         Setup Complete! ✅          │
├─────────────────────────────────────┤
│                                     │
│  Terminal: KIOSK-GEPREK-01          │
│  Brand: Ayam Geprek Boedjangan      │
│  Store: Yogya BSD                   │
│  Device ID: dev_a1b2c3d4            │
│                                     │
│  [Start POS →]                      │
└─────────────────────────────────────┘
```

**Error: Already Assigned:**
```
┌─────────────────────────────────────┐
│          Warning! ⚠️                │
├─────────────────────────────────────┤
│                                     │
│  Terminal sudah digunakan di:       │
│                                     │
│  Device: KASIR-PC-02                │
│  IP: 192.168.1.50                   │
│  Assigned: 2026-01-20 08:15         │
│  Last Seen: 5 minutes ago           │
│                                     │
│  [Use Different Terminal]           │
│  [Contact Admin]                    │
└─────────────────────────────────────┘
```

---

## 📡 **HEARTBEAT & MONITORING**

### **Keep Terminal "Online"**

```python
# Client-side (pos_launcher.py)
import schedule
import time

def send_heartbeat():
    """Send heartbeat every 1 minute"""
    response = requests.post(
        f"{config['server']['url']}/api/v1/terminal/heartbeat/",
        json={
            "terminal_code": config['terminal']['terminal_code'],
            "device_id": config['device']['device_id'],
            "ip_address": get_local_ip()
        },
        headers={"Authorization": f"Bearer {config['security']['validation_token']}"}
    )

# Run every 1 minute
schedule.every(1).minutes.do(send_heartbeat)

while True:
    schedule.run_pending()
    time.sleep(1)
```

### **Server-side Heartbeat Endpoint**

```python
# apps/core/views_setup.py

@api_view(['POST'])
def terminal_heartbeat(request):
    """Update terminal last_seen timestamp"""
    terminal_code = request.data.get('terminal_code')
    device_id = request.data.get('device_id')
    
    terminal = Terminal.objects.get(
        terminal_code=terminal_code,
        device_id=device_id
    )
    
    terminal.last_seen = timezone.now()
    terminal.device_ip = get_client_ip(request)  # May have changed
    terminal.save(update_fields=['last_seen', 'device_ip'])
    
    return Response({"status": "ok"})
```

---

## 🔓 **UNASSIGN TERMINAL (Admin Function)**

### **Django Admin Action**

```python
# apps/core/admin.py

@admin.action(description='Unassign selected terminals from devices')
def unassign_terminals(modeladmin, request, queryset):
    count = 0
    for terminal in queryset:
        if terminal.is_assigned():
            terminal.unassign()
            count += 1
    
    modeladmin.message_user(
        request,
        f"{count} terminal(s) unassigned successfully"
    )

class TerminalAdmin(admin.ModelAdmin):
    list_display = ['terminal_code', 'brand', 'terminal_type', 'device_hostname', 'device_ip', 'is_online', 'last_seen']
    list_filter = ['brand', 'terminal_type', 'is_active']
    search_fields = ['terminal_code', 'terminal_name', 'device_hostname', 'device_ip']
    actions = [unassign_terminals]
    
    def is_online(self, obj):
        return obj.is_online()
    is_online.boolean = True
    is_online.short_description = 'Online'
```

---

## ✅ **VALIDATION CHECKLIST**

### **Edge Server Setup Requirements:**

- [ ] Store configured (Store.get_current() exists)
- [ ] At least 1 Brand created
- [ ] Terminal records created in Django admin (terminal_code + brand)
- [ ] Terminals marked as is_active=True

### **Client Setup Requirements:**

- [ ] config.json exists with terminal_code + brand_code
- [ ] Network connectivity to edge server
- [ ] Printer configured and accessible
- [ ] Device can send MAC address (may need elevated permissions)

### **Validation Success Criteria:**

- [ ] Brand exists in edge server
- [ ] Terminal exists with matching terminal_code + brand
- [ ] Terminal is_active=True
- [ ] Terminal not assigned to another device (or matches current device)
- [ ] Device info captured (IP, MAC, hostname)
- [ ] Validation token generated
- [ ] config.json updated with device_id

---

## 🚀 **MIGRATION PLAN**

### **Phase 1: Database Migration**

```bash
python manage.py makemigrations core
python manage.py migrate
```

### **Phase 2: Data Migration**

```python
# Create terminals for each brand
for brand in Brand.objects.all():
    Terminal.objects.get_or_create(
        terminal_code=f"KASIR-{brand.code}-01",
        brand=brand,
        store=Store.get_current(),
        defaults={
            'terminal_name': f'Kasir {brand.name} 1',
            'terminal_type': 'cashier',
            'is_active': True
        }
    )
```

### **Phase 3: Config Migration**

```python
# Update existing config.json files
# Add brand_code, remove company_id/store_id
```

---

**Status:** 📋 ARCHITECTURE DOCUMENTED  
**Next:** Implement Terminal validation API  
**Contact:** Development Team
