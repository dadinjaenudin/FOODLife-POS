# POS Launcher, Terminal & Receipt Template Architecture

**Document Version:** 1.0.0  
**Last Updated:** February 9, 2026  
**Author:** System Architecture Documentation

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Components](#architecture-components)
3. [POS Launcher Qt Application](#pos-launcher-qt-application)
4. [Terminal Configuration System](#terminal-configuration-system)
5. [Receipt Template System](#receipt-template-system)
6. [Auto Print Implementation](#auto-print-implementation)
7. [Security & Validation](#security--validation)
8. [Data Flow Diagrams](#data-flow-diagrams)
9. [Code Examples](#code-examples)
10. [Troubleshooting Guide](#troubleshooting-guide)

---

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FoodLife POS System                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────┐         ┌──────────────┐                   │
│  │ Django Edge   │◄────────┤ PostgreSQL   │                   │
│  │ Server        │         │ Database     │                   │
│  │ (Port 8001)   │         │ fnb_edge_db  │                   │
│  └───────┬───────┘         └──────────────┘                   │
│          │                                                      │
│          │ HTTP/REST API                                       │
│          │                                                      │
│  ┌───────▼────────────────────────────────────────────┐       │
│  │         POS Launcher Qt (Kiosk App)               │       │
│  │  ┌──────────────────────────────────────────┐     │       │
│  │  │ PyQt6 WebEngine (Chromium)              │     │       │
│  │  │ - Loads Django POS Interface            │     │       │
│  │  │ - Injects terminal_code + brand_code    │     │       │
│  │  │ - Auto-hides browser UI (kiosk mode)    │     │       │
│  │  └──────────────────────────────────────────┘     │       │
│  │                                                     │       │
│  │  ┌──────────────────────────────────────────┐     │       │
│  │  │ Flask Local API (Port 5000)             │     │       │
│  │  │ - Receipt printing (ESC/POS)            │     │       │
│  │  │ - Checker receipt printing              │     │       │
│  │  │ - Customer display control              │     │       │
│  │  │ - Logo download & conversion            │     │       │
│  │  └──────────────────────────────────────────┘     │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐       │
│  │ Kitchen Printer Agent (Separate Service)           │       │
│  │ - Polls database for kitchen tickets               │       │
│  │ - Auto-prints to network/USB printers              │       │
│  │ - Runs independently per station                   │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Terminal as Identity**: Each POS station has a unique `POSTerminal` record with device-specific configuration
2. **Multi-Factor Security**: Terminal authentication uses `terminal_code` + `brand_code` + `company_code` + `store_code`
3. **Distributed Printing**: Receipt printer via Local API, Kitchen printer via Agent polling
4. **Template-Based Receipts**: Dynamic receipt layout from database template with logo support
5. **Offline-First Local API**: POS Launcher can print even if Django server is down
6. **Configuration Injection**: Terminal identity injected via localStorage after page load

---

## Architecture Components

### Component Relationship Matrix

| Component | Purpose | Dependencies | Communication |
|-----------|---------|--------------|---------------|
| **Django Edge Server** | Business logic, API, database | PostgreSQL | HTTP REST API |
| **POS Launcher Qt** | Kiosk application wrapper | Django API, Local API | HTTP, PyQt signals |
| **Flask Local API** | Hardware interface (printer) | ESC/POS drivers, OS printer API | HTTP POST/GET |
| **Kitchen Printer Agent** | Kitchen ticket auto-print | PostgreSQL, Network printers | Direct DB polling |
| **PostgreSQL Database** | Persistent data storage | None | psycopg2, Django ORM |

### Data Flow Priority

```
User Action → Frontend (JavaScript) → Django API → Database
                    ↓
              Terminal Config Check
                    ↓
          ┌─────────┴─────────┐
          ▼                   ▼
    Local API          Kitchen Agent
    (Receipt)          (Kitchen Ticket)
          ▼                   ▼
    Thermal Printer    Network Printer
```

---

## POS Launcher Qt Application

### 1. Application Structure

```
pos_launcher_qt/
├── pos_launcher_qt.py          # Main Qt application
├── local_api.py                # Flask printer/display API
├── config.json                 # Terminal configuration
├── customer_display.html       # Customer-facing display
├── assets/                     # Static resources
├── build/                      # PyInstaller build artifacts
└── releases/                   # Compiled executables
```

### 2. Configuration File (config.json)

**Location:** `pos_launcher_qt/config.json`

```json
{
  "terminal_code": "BOE-001",
  "company_code": "YOGYA",
  "brand_code": "BOE",
  "store_code": "KPT",
  "edge_server": "http://127.0.0.1:8001"
}
```

**Field Descriptions:**

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `terminal_code` | string | ✅ Yes | Unique terminal identifier | `BOE-001`, `KASIR-01` |
| `company_code` | string | ✅ Yes | Company identifier (security) | `YOGYA` |
| `brand_code` | string | ✅ Yes | Brand identifier (security) | `BOE`, `BURGER` |
| `store_code` | string | ✅ Yes | Store/outlet identifier (security) | `KPT`, `OUTLET-01` |
| `edge_server` | string | ✅ Yes | Django server base URL | `http://127.0.0.1:8001`, `http://192.168.1.100:8001` |

**Notes:**
- All fields are **required** for proper operation
- Config is simple flat JSON structure (no nested objects)
- `edge_server` should point to Django Edge Server (port 8001 by default)
- Terminal/company/brand/store codes must match database records exactly
- Used for multi-factor terminal validation and API authentication

### 3. Terminal Identity Injection

**Implementation:** `pos_launcher_qt/pos_launcher_qt.py`

```python
class POSWindow(QWebEngineView):
    def on_load_finished(self, success):
        """Called when page load finishes"""
        if success:
            # Extract codes from config.json
            terminal_code = self.config.get('terminal_code', '')
            company_code = self.config.get('company_code', '')
            brand_code = self.config.get('brand_code', '')
            store_code = self.config.get('store_code', '')
            
            # Inject all codes into browser localStorage
            js_code = f"""
                localStorage.setItem('kiosk_mode', '1');
                localStorage.setItem('terminal_code', '{terminal_code}');
                localStorage.setItem('company_code', '{company_code}');
                localStorage.setItem('brand_code', '{brand_code}');
                localStorage.setItem('store_code', '{store_code}');
                console.log('✅ Terminal identity injected');
            """
            self.page().runJavaScript(js_code)
```

**Why After Page Load?**
- JavaScript `localStorage` API not available until DOM ready
- Ensures browser context is fully initialized
- Prevents race conditions with frontend code

### 4. Local API (Flask Server)

**Port:** `5000` (localhost only)  
**Purpose:** Hardware interface for printers and customer display

**Endpoints:**

| Endpoint | Method | Purpose | Auto Print Flag |
|----------|--------|---------|----------------|
| `/api/print/receipt` | POST | Print payment receipt | `auto_print_receipt` |
| `/api/print/checker` | POST | Print checker receipt | `print_checker_receipt` |
| `/api/customer-display/update` | POST | Update customer display | N/A |
| `/api/customer-display/qr` | POST | Show QR code | N/A |

**Receipt Printing Flow:**

```python
@app.route('/api/print/receipt', methods=['POST'])
def api_print_receipt():
    """Print payment receipt to thermal printer"""
    
    # 1. Get terminal config from config.json
    config = load_config()
    terminal_code = config.get('terminal_code')
    brand_code = config.get('brand_code')
    edge_server = config.get('edge_server')
    
    # 2. Fetch terminal config from Django API (includes receipt template)
    response = requests.get(
        f"{edge_server}/api/terminal/config",
        params={
            'terminal_code': terminal_code,
            'brand_code': brand_code
        }
    )
    
    # 3. Get receipt template and logo URL
    template = response.json()['receipt_template']
    logo_url = template.get('logo_url')  # Relative path: /media/receipt_logos/...
    
    # 4. Download and convert logo to ESC/POS bitmap
    if logo_url:
        full_url = edge_server + logo_url
        logo_bitmap = download_and_process_logo(full_url, paper_width=576)
    
    # 5. Generate ESC/POS commands
    escpos_data = generate_receipt_escpos(receipt_data, logo_bitmap)
    
    # 6. Send to printer
    print_to_local_printer(escpos_data)
```

---

## Terminal Configuration System

### 1. Database Model

**Model:** `apps.core.models.POSTerminal`  
**Table:** `core_posterminal`

```python
class POSTerminal(models.Model):
    # Identity
    terminal_code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    
    # Relationships
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    receipt_template = models.ForeignKey(ReceiptTemplate, on_delete=models.SET_NULL)
    
    # Device Configuration
    edc_merchant_id = models.CharField(max_length=100)  # Payment terminal
    cash_drawer = models.CharField(max_length=100)      # DEPRECATED (now brand)
    
    # Printer Configuration
    receipt_printer_name = models.CharField(max_length=200)
    print_to = models.CharField(
        max_length=20,
        choices=[
            ('printer', 'Physical Printer'),
            ('file', 'Save to File (Testing)')
        ],
        default='printer'
    )
    
    # Auto Print Flags
    auto_print_receipt = models.BooleanField(default=True)
    auto_print_kitchen_order = models.BooleanField(default=True)
    print_checker_receipt = models.BooleanField(default=False)
    
    # Status
    is_active = models.BooleanField(default=True)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
```

### 2. Configuration API Endpoint

**Endpoint:** `GET /api/terminal/config`  
**Handler:** `apps.core.api_terminal.get_terminal_config()`

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `terminal_code` | string | ✅ Yes | Terminal identifier |
| `company_code` | string | ⚠️ Validation | Company code (security) |
| `brand_code` | string | ⚠️ Validation | Brand code (security) |
| `store_code` | string | ⚠️ Validation | Store code (security) |

**Response Structure:**

```json
{
  "success": true,
  "terminal": {
    "id": 1,
    "terminal_code": "BOE-001",
    "name": "Kasir Depan",
    "company": {"id": 1, "name": "YOGYA", "code": "YOGYA"},
    "brand": {"id": 1, "name": "Burger On Express", "code": "BOE"},
    "store": {"id": 1, "name": "Kaputren", "code": "KPT"}
  },
  "device_config": {
    "receipt_printer_name": "EPSON TM-T82",
    "print_to": "printer",
    "auto_print_receipt": true,
    "auto_print_kitchen_order": true,
    "print_checker_receipt": false,
    "edc_merchant_id": "1234567890",
    "logo_url": "/media/receipt_logos/YOGYA/BOE/20260209_143025_logo.png"
  },
  "receipt_template": {
    "id": 1,
    "name": "Burger On Express Standard",
    "header": "=== BURGER ON EXPRESS ===\nJl. Kaputren No. 123",
    "footer": "Thank you for your visit!",
    "paper_width": 58,
    "logo_url": "/media/receipt_logos/YOGYA/BOE/20260209_143025_logo.png"
  }
}
```

### 3. Multi-Factor Validation

**Security Implementation:**

```python
def get_terminal_config(request):
    """Get terminal configuration with multi-factor validation"""
    
    # Extract all validation parameters
    terminal_code = request.GET.get('terminal_code')
    company_code = request.GET.get('company_code')
    brand_code = request.GET.get('brand_code')
    store_code = request.GET.get('store_code')
    
    # Base query - find terminal by code
    terminal = POSTerminal.objects.filter(
        terminal_code=terminal_code,
        is_active=True
    ).first()
    
    if not terminal:
        return JsonResponse({
            'success': False,
            'error': 'Terminal not found'
        })
    
    # Multi-factor validation
    validation_errors = []
    
    if company_code and terminal.company.code != company_code:
        validation_errors.append('Company mismatch')
    
    if brand_code and terminal.brand.code != brand_code:
        validation_errors.append('Brand mismatch')
    
    if store_code and terminal.store.code != store_code:
        validation_errors.append('Store mismatch')
    
    if validation_errors:
        return JsonResponse({
            'success': False,
            'error': 'Validation failed: ' + ', '.join(validation_errors)
        })
    
    # Return configuration
    return JsonResponse({
        'success': True,
        'terminal': serialize_terminal(terminal),
        'device_config': serialize_device_config(terminal),
        'receipt_template': serialize_receipt_template(terminal.receipt_template)
    })
```

**Why Multi-Factor?**

| Factor | Purpose | Attack Prevention |
|--------|---------|-------------------|
| `terminal_code` | Primary identifier | Single-factor guessing |
| `brand_code` | Brand ownership validation | Cross-brand data access |
| `company_code` | Company boundary enforcement | Multi-tenant isolation |
| `store_code` | Physical location verification | Terminal relocation attacks |

### 4. Frontend Configuration Loading

**Implementation:** `templates/pos/main.html`

```javascript
// Global terminal configuration object
let terminalConfig = null;

/**
 * Load terminal configuration from server with multi-factor validation
 */
async function loadTerminalConfig() {
    try {
        // Get all codes from localStorage (injected by POS Launcher)
        let terminalCode = localStorage.getItem('terminal_code');
        let companyCode = localStorage.getItem('company_code');
        let brandCode = localStorage.getItem('brand_code');
        let storeCode = localStorage.getItem('store_code');
        
        // Fallback to URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        if (!terminalCode) terminalCode = urlParams.get('terminal');
        if (!companyCode) companyCode = urlParams.get('company');
        if (!brandCode) brandCode = urlParams.get('brand');
        if (!storeCode) storeCode = urlParams.get('store');
        
        if (!terminalCode) {
            console.warn('⚠️ Terminal code not found');
            return;
        }
        
        // Build API URL with all validation parameters
        let apiUrl = `/api/terminal/config?terminal_code=${terminalCode}`;
        if (companyCode) apiUrl += `&company_code=${companyCode}`;
        if (brandCode) apiUrl += `&brand_code=${brandCode}`;
        if (storeCode) apiUrl += `&store_code=${storeCode}`;
        
        console.log('📡 Loading terminal config with validation:', {
            terminal: terminalCode,
            company: companyCode,
            brand: brandCode,
            store: storeCode
        });
        
        const response = await fetch(apiUrl);
        const data = await response.json();
        
        if (data.success) {
            terminalConfig = data;
            console.log('✅ Terminal config loaded and validated');
            console.log('   Auto Print Receipt:', terminalConfig.device_config?.auto_print_receipt);
            console.log('   Auto Print Kitchen:', terminalConfig.device_config?.auto_print_kitchen_order);
            console.log('   Print Checker:', terminalConfig.device_config?.print_checker_receipt);
        } else {
            console.error('❌ Failed to load terminal config:', data.error);
        }
    } catch (error) {
        console.error('❌ Error loading terminal config:', error);
    }
}

// Load terminal config on page ready
document.addEventListener('DOMContentLoaded', function() {
    loadTerminalConfig();
});
```

---

## Receipt Template System

### 1. Database Model

**Model:** `apps.core.models.ReceiptTemplate`  
**Table:** `core_receipttemplate`

```python
class ReceiptTemplate(models.Model):
    # Identity
    name = models.CharField(max_length=100)
    
    # Relationships
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, null=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, null=True)
    
    # Content
    header = models.TextField(help_text="Header text (multi-line supported)")
    footer = models.TextField(help_text="Footer text (multi-line supported)")
    
    # Logo (ImageField with dynamic upload path)
    logo = models.ImageField(
        upload_to=receipt_logo_upload_path,
        null=True,
        blank=True,
        help_text="Logo image (JPG/PNG, max 2MB)"
    )
    
    # Settings
    paper_width = models.IntegerField(
        choices=[
            (58, '58mm (Small)'),
            (80, '80mm (Standard)')
        ],
        default=58
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    def save(self, *args, **kwargs):
        """Auto-cleanup old logo when uploading new one"""
        try:
            old_instance = ReceiptTemplate.objects.get(pk=self.pk)
            if old_instance.logo and old_instance.logo != self.logo:
                # Delete old logo file
                if os.path.isfile(old_instance.logo.path):
                    os.remove(old_instance.logo.path)
        except ReceiptTemplate.DoesNotExist:
            pass  # New instance, no cleanup needed
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Auto-cleanup logo when deleting template"""
        if self.logo:
            if os.path.isfile(self.logo.path):
                os.remove(self.logo.path)
        super().delete(*args, **kwargs)
```

### 2. Logo Upload Path Strategy

**Function:** `receipt_logo_upload_path(instance, filename)`

```python
def receipt_logo_upload_path(instance, filename):
    """
    Dynamic upload path for receipt logo with organized folder structure
    
    Path pattern:
    receipt_logos/{company_code}/{brand_code|store_name|company}/
                  {timestamp}_{filename}
    
    Examples:
    - receipt_logos/YOGYA/BOE/20260209_143025_logo.png
    - receipt_logos/YOGYA/store_KPT/20260209_143025_logo.png
    - receipt_logos/YOGYA/YOGYA/20260209_143025_logo.png
    
    Benefits:
    - Organized by hierarchy (company → brand/store)
    - Timestamped to prevent filename conflicts
    - Easy cleanup per company/brand
    - Supports brand-level, store-specific, or company-wide templates
    """
    from datetime import datetime
    
    # Build folder path
    company_code = instance.company.code if instance.company else 'default'
    
    if instance.brand:
        subfolder = instance.brand.code
    elif instance.store:
        subfolder = f"store_{instance.store.code}"
    else:
        subfolder = company_code
    
    # Add timestamp to filename to prevent conflicts
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    name, ext = os.path.splitext(filename)
    new_filename = f"{timestamp}_{name}{ext}"
    
    return f"receipt_logos/{company_code}/{subfolder}/{new_filename}"
```

**Folder Structure Example:**

```
media/
└── receipt_logos/
    ├── YOGYA/
    │   ├── BOE/
    │   │   ├── 20260209_143025_logo.png
    │   │   └── 20260209_150312_logo_v2.png
    │   ├── PIZZA/
    │   │   └── 20260209_144530_logo.png
    │   └── store_KPT/
    │       └── 20260209_145820_logo.png
    └── ACME/
        └── ACME/
            └── 20260209_151045_logo.png
```

### 3. Logo Processing Pipeline

**Step 1: API Returns Relative Path**

```python
# apps/core/api_terminal.py
def get_terminal_config(request):
    """Return relative logo path (not absolute URL)"""
    
    logo_url = None
    if terminal.receipt_template and terminal.receipt_template.logo:
        # Return relative path: /media/receipt_logos/...
        logo_url = terminal.receipt_template.logo.url
    
    return JsonResponse({
        'receipt_template': {
            'logo_url': logo_url  # "/media/receipt_logos/YOGYA/BURGER/..."
        }
    })
```

**Why Relative Path?**
- Allows POS Launcher to build full URL with correct `edge_server` from config.json
- Prevents hardcoded `localhost` or specific IP in database
- Supports dynamic network configurations

**Step 2: POS Launcher Downloads Logo**

```python
# pos_launcher_qt/local_api.py
def download_and_process_logo(logo_url, edge_server, paper_width=576):
    """
    Download logo from Django server and convert to ESC/POS bitmap
    
    Args:
        logo_url: Relative path (e.g., "/media/receipt_logos/YOGYA/BURGER/logo.png")
        edge_server: Base URL (e.g., "http://192.168.1.100:8001")
        paper_width: Printer paper width in pixels (576px for 80mm, 384px for 58mm)
    
    Returns:
        PIL.Image: Processed logo ready for ESC/POS conversion
    """
    import requests
    from PIL import Image
    from io import BytesIO
    
    # Build full URL
    if logo_url.startswith('/'):
        full_url = edge_server + logo_url
    else:
        full_url = logo_url
    
    print(f"[Logo] Downloading: {full_url}")
    
    # Download image
    response = requests.get(full_url, timeout=10)
    response.raise_for_status()
    
    # Load image with PIL
    image = Image.open(BytesIO(response.content))
    
    # Convert to grayscale
    image = image.convert('L')
    
    # Resize to fit paper width (maintain aspect ratio)
    max_width = paper_width - 40  # Padding
    if image.width > max_width:
        ratio = max_width / image.width
        new_height = int(image.height * ratio)
        image = image.resize((max_width, new_height), Image.LANCZOS)
    
    print(f"[Logo] Processed: {image.size[0]}x{image.size[1]}px")
    
    return image
```

**Step 3: Convert to ESC/POS Bitmap**

```python
def image_to_escpos_bitmap(image, max_width=576):
    """
    Convert PIL Image to ESC/POS bitmap format (24-dot double density)
    
    ESC/POS Format: ESC * 33 nL nH [bitmap data]
    - ESC * 33: 24-dot double density mode
    - nL nH: Width in bytes (little-endian)
    - Bitmap data: 3 bytes per column (24 dots = 3 bytes of 8 bits)
    
    Args:
        image: PIL.Image (grayscale)
        max_width: Maximum width in pixels
    
    Returns:
        bytes: ESC/POS bitmap commands
    """
    # Convert to black & white (threshold=128)
    bw_image = image.point(lambda x: 0 if x < 128 else 255, '1')
    
    width, height = bw_image.size
    
    # Ensure height is multiple of 24 (pad if needed)
    padded_height = ((height + 23) // 24) * 24
    if padded_height > height:
        new_image = Image.new('1', (width, padded_height), 255)
        new_image.paste(bw_image, (0, 0))
        bw_image = new_image
    
    # Convert to ESC/POS bitmap
    bitmap_data = bytearray()
    
    # Process in 24-dot strips
    for y in range(0, padded_height, 24):
        # ESC * 33 nL nH (24-dot double density)
        bitmap_data.extend(b'\x1b*\x21')
        bitmap_data.extend(width.to_bytes(2, 'little'))  # Width: nL nH
        
        # Process each column
        for x in range(width):
            # Collect 24 dots (3 bytes of 8 bits each)
            for byte_idx in range(3):
                byte_value = 0
                for bit_idx in range(8):
                    pixel_y = y + (byte_idx * 8) + bit_idx
                    if pixel_y < height:
                        pixel = bw_image.getpixel((x, pixel_y))
                        if pixel == 0:  # Black
                            byte_value |= (1 << (7 - bit_idx))
                
                bitmap_data.append(byte_value)
        
        # Line feed after each strip
        bitmap_data.extend(b'\x0a')
    
    return bytes(bitmap_data)
```

**Step 4: Insert into Receipt**

```python
def generate_receipt_escpos(receipt_data, logo_bitmap=None):
    """
    Generate complete ESC/POS receipt with logo
    
    Args:
        receipt_data: dict with bill/payment info
        logo_bitmap: bytes (ESC/POS bitmap commands) or None
    
    Returns:
        bytes: Complete ESC/POS command sequence
    """
    data = bytearray()
    
    # Reset printer
    data.extend(b'\x1b@')
    
    # Logo at top (center-aligned)
    if logo_bitmap:
        data.extend(b'\x1ba\x01')  # Center align
        data.extend(logo_bitmap)
        data.extend(b'\x0a\x0a')   # 2 line feeds
    
    # Header text
    data.extend(b'\x1ba\x01')      # Center align
    header = receipt_data.get('header', '')
    data.extend(header.encode('utf-8'))
    data.extend(b'\x0a\x0a')
    
    # Bill details...
    # (rest of receipt formatting)
    
    # Footer
    data.extend(b'\x1ba\x01')
    footer = receipt_data.get('footer', '')
    data.extend(footer.encode('utf-8'))
    data.extend(b'\x0a\x0a\x0a')
    
    # Cut paper
    data.extend(b'\x1dV\x00')
    
    return bytes(data)
```

### 4. Logo Display in Admin

**Template:** `templates/management/receipt_template_list.html`

```html
<!-- Logo Preview Column -->
<td class="px-6 py-4">
    {% if template.logo %}
        <div class="border-2 border-blue-400 rounded-lg p-2 inline-block bg-blue-50">
            <img src="{{ template.logo.url }}" 
                 alt="Logo" 
                 class="h-12 w-auto"
                 title="Logo: {{ template.logo.name }}">
        </div>
    {% else %}
        <span class="text-gray-400 text-sm">No logo</span>
    {% endif %}
</td>
```

---

## Auto Print Implementation

### 1. Feature Matrix

| Feature | Terminal Flag | Trigger Point | Handler | Printer |
|---------|--------------|---------------|---------|---------|
| **Auto Print Receipt** | `auto_print_receipt` | Payment complete | Frontend → Local API | POS Receipt Printer |
| **Auto Print Kitchen** | `auto_print_kitchen_order` | Send to Kitchen | Backend → Kitchen Agent | Kitchen Station Printer |
| **Print Checker Copy** | `print_checker_receipt` | Send to Kitchen | Backend → Local API | POS Receipt Printer |

### 2. Auto Print Receipt (Payment Complete)

**Flag:** `auto_print_receipt` (Boolean, default: `true`)  
**Trigger:** Payment button clicked, payment successful  
**Flow:** Frontend checks flag → Calls Local API

**Implementation:** `templates/pos/main.html`

```javascript
/**
 * Send receipt to local printer (via POS Launcher API)
 * Respects terminal auto_print_receipt flag
 */
async function sendReceiptToLocalPrinter(billId) {
    try {
        // Check auto_print_receipt flag from terminal config
        if (!terminalConfig?.device_config?.auto_print_receipt) {
            console.log('⏭️ Auto print receipt disabled - skipping');
            return;
        }
        
        console.log('🖨️ Auto print receipt enabled - printing...');
        
        // Fetch receipt data from Django API
        const receiptResponse = await fetch(`/api/pos/receipt/${billId}`);
        const receiptData = await receiptResponse.json();
        
        if (!receiptData.success) {
            console.error('❌ Failed to get receipt data:', receiptData.error);
            return;
        }
        
        // Send to local printer API
        const printResponse = await fetch('http://localhost:5000/api/print/receipt', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(receiptData.data)
        });
        
        const printResult = await printResponse.json();
        
        if (printResult.success) {
            console.log('✅ Receipt printed successfully');
            showNotification('Receipt printed', 'success');
        } else {
            console.error('❌ Print failed:', printResult.error);
            showNotification('Print failed: ' + printResult.error, 'error');
        }
        
    } catch (error) {
        console.error('❌ Print error:', error);
        showNotification('Print error: ' + error.message, 'error');
    }
}

// Called after successful payment
function onPaymentSuccess(billId) {
    // Other post-payment actions...
    
    // Auto print if enabled
    sendReceiptToLocalPrinter(billId);
}
```

**Key Points:**
- ✅ Frontend decision (fast, no server round-trip)
- ✅ Reads flag from `terminalConfig` loaded at page start
- ✅ Silent fail if Local API down (non-blocking)
- ✅ User gets immediate feedback

### 3. Auto Print Kitchen Order (Send to Kitchen)

**Flag:** `auto_print_kitchen_order` (Boolean, default: `true`)  
**Trigger:** "Send to Kitchen" button clicked  
**Flow:** Backend checks flag → Creates tickets → Kitchen Agent polls & prints

**Implementation:** `apps/pos/views.py`

```python
def send_to_kitchen(request, bill_id):
    """Send pending items to kitchen - HTMX endpoint"""
    
    bill = get_object_or_404(Bill, id=bill_id)
    pending_items = bill.items.filter(status='pending', is_void=False)
    
    if not pending_items.exists():
        # No items to send
        return render_bill_panel_with_notification(
            request, bill, 
            "No pending items", "warning"
        )
    
    try:
        # Update item status BEFORE ticket creation (prevent race condition)
        pending_item_ids = list(pending_items.values_list('id', flat=True))
        pending_items.update(status='sent')
        
        print(f"\n{'='*60}")
        print(f"[Send to Kitchen] Bill #{bill.bill_number}")
        print(f"[Send to Kitchen] Updated {len(pending_item_ids)} items to 'sent'")
        
        # Get terminal configuration
        terminal = get_terminal_from_request(request)
        
        # Check auto_print_kitchen_order flag
        tickets = []
        if terminal and terminal.auto_print_kitchen_order:
            print(f"[Auto Print Kitchen] ENABLED - Creating kitchen tickets")
            
            # Create tickets for Kitchen Printer Agent to poll
            from apps.kitchen.services import create_kitchen_tickets
            tickets = create_kitchen_tickets(bill, item_ids=pending_item_ids)
            
            print(f"[Auto Print Kitchen] Created {len(tickets)} ticket(s):")
            for ticket in tickets:
                print(f"  - Ticket #{ticket.id}: {ticket.printer_target} "
                      f"({ticket.items.count()} items)")
            
            # Kitchen Printer Agent will poll and print these tickets
            # No direct printing from Django - agent runs independently
        else:
            print(f"[Auto Print Kitchen] DISABLED - Skipping ticket creation")
            print(f"[Auto Print Kitchen] Items marked 'sent' but no auto printing")
        
        print(f"{'='*60}\n")
        
        # Log action
        BillLog.objects.create(
            bill=bill,
            action='send_kitchen',
            user=request.user,
            details={
                'items_count': len(pending_item_ids),
                'tickets_count': len(tickets),
                'tickets': [t.id for t in tickets],
                'auto_print_kitchen': terminal.auto_print_kitchen_order if terminal else False
            }
        )
        
        # Return updated bill panel
        return render_bill_panel_with_notification(
            request, bill,
            f"Sent {len(pending_item_ids)} items to {len(tickets)} station(s)",
            "success"
        )
        
    except Exception as e:
        print(f"[Send to Kitchen] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return HttpResponse(
            f'<div class="error">Error: {str(e)}</div>',
            status=500
        )
```

**Kitchen Printer Agent Flow:**

```
┌─────────────────────────────────────────────────────────────┐
│ Kitchen Printer Agent (Separate Python Process)            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  while True:                                                │
│      # Poll database every 2 seconds                        │
│      tickets = fetch_pending_tickets(station='kitchen')     │
│                                                             │
│      for ticket in tickets:                                 │
│          # Get printer config from database                 │
│          printer = get_station_printer(ticket.station)      │
│                                                             │
│          # Format ESC/POS commands                          │
│          data = format_kitchen_ticket(ticket)               │
│                                                             │
│          # Print to network/USB printer                     │
│          print_to_printer(data, printer)                    │
│                                                             │
│          # Update ticket status                             │
│          ticket.status = 'printed'                          │
│          ticket.printed_at = now()                          │
│          ticket.save()                                      │
│                                                             │
│      sleep(2)  # Wait before next poll                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Why Separate Agent?**

| Reason | Benefit |
|--------|---------|
| **Decoupled** | Django doesn't block on printer I/O |
| **Resilient** | Agent can retry failed prints independently |
| **Scalable** | One agent per station, parallel printing |
| **Network Independence** | Agent runs on kitchen subnet, direct printer access |
| **Fault Tolerance** | Web server crash doesn't stop kitchen printing |

### 4. Print Checker Receipt (Send to Kitchen)

**Flag:** `print_checker_receipt` (Boolean, default: `false`)  
**Trigger:** "Send to Kitchen" button clicked  
**Flow:** Backend checks flag → Calls Local API  
**Purpose:** Print checklist for kitchen staff to mark completed items

**Implementation:** `apps/pos/views.py`

```python
def send_to_kitchen(request, bill_id):
    """Send pending items to kitchen - HTMX endpoint"""
    
    # ... (previous code: update items, create tickets)
    
    # Print checker receipt if enabled
    try:
        terminal = get_terminal_from_request(request)
        
        if terminal and terminal.print_checker_receipt:
            print(f"[Checker Receipt] ENABLED - Printing checklist")
            
            # Get items that were just sent
            items_sent = bill.items.filter(id__in=pending_item_ids)
            
            print(f"[Checker Receipt] Sending {items_sent.count()} items "
                  f"to local printer")
            
            # Send to POSLauncher local API
            send_checker_receipt_to_local_printer(
                bill, 
                items_sent, 
                terminal_id=str(terminal.id)
            )
        else:
            print(f"[Checker Receipt] DISABLED - Skipping")
    
    except Exception as e:
        print(f"[Checker Receipt] ERROR: {e}")
        # Don't fail entire operation if checker print fails
        pass
    
    # ... (return response)
```

**Checker Receipt Function:**

```python
def send_checker_receipt_to_local_printer(bill, items_to_check, terminal_id=None):
    """
    Send checker receipt to local printer via POS Launcher API
    
    Format: Simple checklist with [ ] checkboxes for kitchen staff
    
    Args:
        bill: Bill instance
        items_to_check: QuerySet of BillItem objects to include
        terminal_id: Optional terminal ID for logging
    """
    import requests
    from datetime import datetime
    
    # Prepare checker receipt data
    checker_data = {
        'bill_number': bill.bill_number,
        'table_number': bill.table.number if bill.table else '',
        'date': datetime.now().strftime('%d/%m/%Y'),
        'time': datetime.now().strftime('%H:%M:%S'),
        'items': []
    }
    
    # Add items with checkbox format
    for item in items_to_check:
        checker_data['items'].append({
            'name': item.product.name if item.product else item.notes,
            'quantity': int(item.quantity),
            'notes': item.notes or ''
        })
    
    print(f"[Checker Receipt] Data prepared: {len(checker_data['items'])} items")
    
    # Send to local API (use host.docker.internal for Docker container)
    local_api_url = 'http://host.docker.internal:5000/api/print/checker'
    
    try:
        response = requests.post(
            local_api_url,
            json=checker_data,
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"[Checker Receipt] ✅ SUCCESS - Printed to {result.get('printer')}")
                return True
            else:
                print(f"[Checker Receipt] ❌ FAILED - {result.get('error')}")
                return False
        else:
            print(f"[Checker Receipt] ❌ HTTP {response.status_code}")
            return False
    
    except requests.exceptions.ConnectionError:
        print(f"[Checker Receipt] ⚠️ Local API not running")
        return False
    except requests.exceptions.Timeout:
        print(f"[Checker Receipt] ⚠️ Request timeout")
        return False
```

**Checker Receipt Format:**

```
==========================================
      CHECKER RECEIPT
    (Mark completed items)
==========================================

Bill     : 000123
Table    : 5
Time     : 09/02/2026 14:30:45

------------------------------------------

[ ]  2x Burger Deluxe
     Extra cheese, no onion

[ ]  1x French Fries
     Large size

[ ]  3x Iced Tea

------------------------------------------
         Total Items: 3
==========================================

     CHECK ALL ITEMS BEFORE SERVING
```

---

## Security & Validation

### 1. Multi-Factor Terminal Validation

**Validation Layers:**

```
Layer 1: Terminal Code (Primary)
   ↓
Layer 2: Brand Code (Ownership)
   ↓
Layer 3: Company Code (Tenant Isolation)
   ↓
Layer 4: Store Code (Location)
   ↓
✅ Access Granted
```

**Attack Scenarios Prevented:**

| Attack | Prevention | Validation Factor |
|--------|-----------|-------------------|
| Terminal Code Guessing | Brand must match | `brand_code` |
| Cross-Brand Access | Company boundary check | `company_code` |
| Terminal Relocation | Store location verification | `store_code` |
| Session Hijacking | All codes in localStorage | Multi-factor |

### 2. Token Storage Security

**Storage Location:** Browser `localStorage` (injected by POS Launcher)

**Why localStorage?**

| Aspect | Advantage | Risk Mitigation |
|--------|-----------|----------------|
| **Persistence** | Survives page refresh | Cleared on app restart |
| **Isolation** | Per-origin sandboxing | localhost + same-origin policy |
| **Access** | JavaScript-only | No external domain access |
| **Physical Security** | Kiosk mode = locked device | No user browser access |

**Security Checklist:**

- ✅ localStorage cleared on POS Launcher exit
- ✅ Kiosk mode prevents browser dev tools access
- ✅ HTTPS enforced in production (prevents MITM)
- ✅ Terminal codes validated on every API call
- ✅ Database logs all terminal access

### 3. API Security Best Practices

**Rate Limiting:**

```python
from django.core.cache import cache
from django.http import JsonResponse

def rate_limit_terminal_config(request):
    """Rate limit terminal config API to prevent brute force"""
    
    terminal_code = request.GET.get('terminal_code')
    cache_key = f'terminal_config_rate_{terminal_code}'
    
    # Check request count
    request_count = cache.get(cache_key, 0)
    
    if request_count > 100:  # 100 requests per hour
        return JsonResponse({
            'success': False,
            'error': 'Rate limit exceeded'
        }, status=429)
    
    # Increment counter
    cache.set(cache_key, request_count + 1, timeout=3600)
    
    # Continue with normal logic
    return get_terminal_config(request)
```

**Audit Logging:**

```python
class TerminalAccessLog(models.Model):
    """Log all terminal config API access for security auditing"""
    
    terminal = models.ForeignKey(POSTerminal, on_delete=models.CASCADE)
    accessed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    
    # Validation results
    company_validated = models.BooleanField(default=False)
    brand_validated = models.BooleanField(default=False)
    store_validated = models.BooleanField(default=False)
    
    # Request details
    request_params = models.JSONField()
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)

# Log every access
def get_terminal_config(request):
    terminal = POSTerminal.objects.get(terminal_code=request.GET['terminal_code'])
    
    # Create audit log
    TerminalAccessLog.objects.create(
        terminal=terminal,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT'),
        company_validated=validated_company,
        brand_validated=validated_brand,
        store_validated=validated_store,
        request_params=dict(request.GET),
        success=True
    )
    
    return JsonResponse({...})
```

---

## Data Flow Diagrams

### 1. Application Startup Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ POS LAUNCHER STARTUP                                            │
└─────────────────────────────────────────────────────────────────┘

1. Load config.json
   ├── terminal_code: "BOE-001"
   ├── company_code: "YOGYA"
   ├── brand_code: "BOE"
   ├── store_code: "KPT"
   └── edge_server: "http://127.0.0.1:8001"

2. Start Flask Local API (port 5000)
   ├── Background thread
   ├── /api/print/receipt
   ├── /api/print/checker
   └── /api/customer-display/*

3. Create PyQt6 WebEngine Window
   ├── URL: http://127.0.0.1:8001/pos/
   ├── Fullscreen (kiosk mode)
   └── Disable browser controls

4. Page Load Complete
   └── JavaScript: on_load_finished()

5. Inject Terminal Identity
   ├── localStorage.setItem('terminal_code', 'BOE-001')
   ├── localStorage.setItem('company_code', 'YOGYA')
   ├── localStorage.setItem('brand_code', 'BOE')
   ├── localStorage.setItem('store_code', 'KPT')
   └── localStorage.setItem('kiosk_mode', '1')

6. Frontend Initialization (DOMContentLoaded)
   └── loadTerminalConfig()

7. Fetch Terminal Config from API
   ├── GET /api/terminal/config?terminal_code=BOE-001&brand_code=BOE&company_code=YOGYA&store_code=KPT
   ├── Validate terminal + brand + company + store
   └── Return config + receipt template + logo URL

8. Store Global Config
   └── terminalConfig = { device_config: {...}, receipt_template: {...} }

✅ READY - POS Interface Active
```

### 2. Auto Print Receipt Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ AUTO PRINT RECEIPT (Payment Complete)                          │
└─────────────────────────────────────────────────────────────────┘

1. User clicks "Pay" button
   ├── Frontend JavaScript: processPayment()
   └── POST /pos/bill/{id}/payment

2. Django Backend
   ├── Create Payment record
   ├── Update Bill status = 'paid'
   ├── Close BillItems
   └── Return success response

3. Frontend: onPaymentSuccess(billId)
   └── Call sendReceiptToLocalPrinter(billId)

4. Check Terminal Config Flag
   ├── if (!terminalConfig.device_config.auto_print_receipt)
   │   └── SKIP (return early)
   └── else
       └── CONTINUE

5. Fetch Receipt Data
   ├── GET /api/pos/receipt/{billId}
   └── Response: {bill_number, items[], total, payment_method, ...}

6. Send to Local API
   ├── POST http://localhost:5000/api/print/receipt
   └── Body: receipt_data

7. Local API Processing
   ├── Load config.json (get edge_server)
   ├── Fetch terminal config from Django
   │   └── GET {edge_server}/api/terminal/config?terminal_code=...
   ├── Get receipt template + logo URL
   ├── Download logo (if exists)
   │   └── GET {edge_server}{logo_url}
   ├── Convert logo to ESC/POS bitmap
   ├── Format receipt text with template
   ├── Generate complete ESC/POS commands
   └── Send to thermal printer

8. Print Output
   ├── [LOGO IMAGE]
   ├── === BURGER HOUSE ===
   ├── Bill: 000123
   ├── Items: 2x Burger, 1x Fries
   ├── Total: Rp 95,000
   ├── Payment: Cash
   ├── Change: Rp 5,000
   └── Thank you!

✅ COMPLETE - Receipt Printed
```

### 3. Send to Kitchen Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ SEND TO KITCHEN (Multi-Print Decision)                         │
└─────────────────────────────────────────────────────────────────┘

1. User clicks "Send to Kitchen" button
   ├── HTMX: hx-post="/pos/bill/{id}/send-kitchen"
   └── POST /pos/bill/{id}/send-kitchen

2. Django Backend: send_to_kitchen(request, bill_id)
   ├── Get pending items (status='pending')
   └── if no pending items → return warning

3. Update Item Status
   ├── SELECT id FROM bill_items WHERE status='pending'
   ├── pending_item_ids = [1, 2, 3, 4]
   └── UPDATE bill_items SET status='sent' WHERE id IN (1,2,3,4)

4. Get Terminal Configuration
   ├── terminal = request.terminal or session['terminal_id']
   └── Read flags: auto_print_kitchen_order, print_checker_receipt

5. Decision: Auto Print Kitchen?
   ├── if terminal.auto_print_kitchen_order == True:
   │   ├── print("[Auto Print Kitchen] ENABLED")
   │   ├── create_kitchen_tickets(bill, item_ids=pending_item_ids)
   │   ├── Tickets created:
   │   │   ├── Ticket #101: 'kitchen' (2 items)
   │   │   ├── Ticket #102: 'bar' (1 item)
   │   │   └── Ticket #103: 'dessert' (1 item)
   │   └── Kitchen Printer Agent will poll & print
   └── else:
       ├── print("[Auto Print Kitchen] DISABLED")
       └── Skip ticket creation (items stay 'sent' without printing)

6. Decision: Print Checker Receipt?
   ├── if terminal.print_checker_receipt == True:
   │   ├── print("[Checker Receipt] ENABLED")
   │   ├── items_sent = bill.items.filter(id__in=pending_item_ids)
   │   ├── send_checker_receipt_to_local_printer(bill, items_sent)
   │   ├── POST http://host.docker.internal:5000/api/print/checker
   │   └── Print checklist with [ ] checkboxes
   └── else:
       ├── print("[Checker Receipt] DISABLED")
       └── Skip checker receipt

7. Create Bill Log
   └── BillLog(action='send_kitchen', details={tickets_count, auto_print_kitchen})

8. Return Response
   └── HX-Trigger: showNotification("Sent 4 items to 3 stations")

✅ COMPLETE - Items Sent (+ Auto Prints Triggered)

───────────────────────────────────────────────────────────────────

PARALLEL PROCESS: Kitchen Printer Agent (Separate Service)

Kitchen Agent Poll Loop (every 2 seconds):

1. Query Database
   └── SELECT * FROM kitchen_ticket WHERE status='pending' 
       AND printer_target='kitchen'

2. Found Ticket #101
   ├── Bill: 000123, Table: 5
   ├── Items: 2x Burger Deluxe, 1x French Fries
   └── printer_target: 'kitchen'

3. Get Printer Config
   └── SELECT * FROM kitchen_stationprinter 
       WHERE station='kitchen' AND brand_id=...

4. Format Kitchen Ticket
   ├── === KITCHEN ===
   ├── Bill: 000123
   ├── Table: 5
   ├── Time: 14:30
   ├── ─────────────
   ├── 2x Burger Deluxe
   ├──    Extra cheese
   ├── 1x French Fries
   └── ─────────────

5. Generate ESC/POS Commands
   └── format_kitchen_ticket(ticket) → bytes

6. Print to Network Printer
   ├── Connect: socket.connect(('192.168.1.50', 9100))
   ├── Send: socket.send(escpos_data)
   └── Close: socket.close()

7. Update Ticket Status
   ├── UPDATE kitchen_ticket SET status='printed', printed_at=NOW()
   └── COMMIT

✅ COMPLETE - Kitchen Ticket Printed

Loop continues forever...
```

---

## Code Examples

### 1. Complete Terminal Configuration Loading (Frontend)

```javascript
// Global terminal configuration
let terminalConfig = null;

/**
 * Load terminal configuration from server with multi-factor validation
 * Called on page ready (DOMContentLoaded)
 */
async function loadTerminalConfig() {
    try {
        // Get terminal identity from localStorage (injected by POS Launcher)
        const terminalCode = localStorage.getItem('terminal_code');
        const companyCode = localStorage.getItem('company_code');
        const brandCode = localStorage.getItem('brand_code');
        const storeCode = localStorage.getItem('store_code');
        
        if (!terminalCode) {
            console.warn('⚠️ Terminal code not found in localStorage');
            return;
        }
        
        // Build API URL with all validation parameters
        let apiUrl = `/api/terminal/config?terminal_code=${terminalCode}`;
        if (companyCode) apiUrl += `&company_code=${companyCode}`;
        if (brandCode) apiUrl += `&brand_code=${brandCode}`;
        if (storeCode) apiUrl += `&store_code=${storeCode}`;
        
        console.log('📡 Loading terminal config:', {
            terminal: terminalCode,
            company: companyCode,
            brand: brandCode,
            store: storeCode
        });
        
        // Fetch configuration
        const response = await fetch(apiUrl);
        const data = await response.json();
        
        if (data.success) {
            terminalConfig = data;
            
            console.log('✅ Terminal config loaded successfully');
            console.log('   Terminal:', terminalConfig.terminal.name);
            console.log('   Auto Print Receipt:', terminalConfig.device_config?.auto_print_receipt);
            console.log('   Auto Print Kitchen:', terminalConfig.device_config?.auto_print_kitchen_order);
            console.log('   Print Checker:', terminalConfig.device_config?.print_checker_receipt);
            console.log('   Print To:', terminalConfig.device_config?.print_to);
            console.log('   Printer:', terminalConfig.device_config?.receipt_printer_name);
            
            // Initialize features based on config
            initializeFeatures();
        } else {
            console.error('❌ Failed to load terminal config:', data.error);
            showNotification('Terminal configuration error: ' + data.error, 'error');
        }
    } catch (error) {
        console.error('❌ Error loading terminal config:', error);
        showNotification('Failed to load terminal configuration', 'error');
    }
}

/**
 * Initialize features after terminal config loaded
 */
function initializeFeatures() {
    // Update UI based on terminal capabilities
    updatePrinterStatus();
    
    // Show/hide features based on config
    if (!terminalConfig.device_config?.print_checker_receipt) {
        // Hide checker receipt button if disabled
        document.getElementById('checker-receipt-btn')?.classList.add('hidden');
    }
}

// Load on page ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 POS Interface Loading...');
    loadTerminalConfig();
});
```

### 2. Complete Local API Receipt Printing

```python
# pos_launcher_qt/local_api.py

@app.route('/api/print/receipt', methods=['POST'])
def api_print_receipt():
    """
    Print payment receipt to thermal printer
    
    Flow:
    1. Fetch terminal config (includes receipt template & logo)
    2. Download logo from Django server
    3. Convert logo to ESC/POS bitmap
    4. Format receipt with template
    5. Send to printer
    """
    try:
        # Get receipt data from request
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        print(f"\n{'='*60}")
        print(f"[Receipt Print] Starting for Bill #{data.get('bill_number')}")
        print(f"{'='*60}")
        
        # Load local configuration
        config_path = Path(os.getcwd()) / 'config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            local_config = json.load(f)
        
        edge_server = local_config.get('edge_server', 'http://127.0.0.1:8001')
        terminal_code = local_config.get('terminal_code')
        company_code = local_config.get('company_code')
        brand_code = local_config.get('brand_code')
        store_code = local_config.get('store_code')
        
        print(f"[Receipt Print] Edge server: {edge_server}")
        print(f"[Receipt Print] Terminal: {terminal_code}")
        
        # Fetch terminal config from Django API
        import requests
        params = {'terminal_code': terminal_code}
        if company_code:
            params['company_code'] = company_code
        if brand_code:
            params['brand_code'] = brand_code
        if store_code:
            params['store_code'] = store_code
        
        print(f"[Receipt Print] Fetching terminal config with validation...")
        response = requests.get(
            f"{edge_server}/api/terminal/config",
            params=params,
            timeout=10
        )
        
        if response.status_code != 200:
            error_msg = f"Failed to fetch terminal config: HTTP {response.status_code}"
            print(f"[Receipt Print] ❌ {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 500
        
        config_data = response.json()
        if not config_data.get('success'):
            error_msg = config_data.get('error', 'Unknown error')
            print(f"[Receipt Print] ❌ Config error: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 500
        
        print(f"[Receipt Print] ✅ Terminal config fetched successfully")
        
        # Extract receipt template and device config
        receipt_template = config_data.get('receipt_template', {})
        device_config = config_data.get('device_config', {})
        
        # Get logo URL (relative path from API)
        logo_url = receipt_template.get('logo_url')
        paper_width_mm = receipt_template.get('paper_width', 58)
        
        # Convert paper width to pixels (approx 8 pixels per mm)
        paper_width_px = 384 if paper_width_mm == 58 else 576
        
        print(f"[Receipt Print] Template: {receipt_template.get('name')}")
        print(f"[Receipt Print] Paper width: {paper_width_mm}mm ({paper_width_px}px)")
        print(f"[Receipt Print] Logo URL: {logo_url or 'None'}")
        
        # Download and process logo
        logo_bitmap = None
        if logo_url:
            try:
                print(f"[Receipt Print] Downloading logo...")
                logo_image = download_and_process_logo(
                    logo_url, 
                    edge_server, 
                    paper_width_px
                )
                
                print(f"[Receipt Print] Converting logo to ESC/POS bitmap...")
                logo_bitmap = image_to_escpos_bitmap(logo_image, paper_width_px)
                
                print(f"[Receipt Print] ✅ Logo processed: {len(logo_bitmap)} bytes")
            except Exception as e:
                print(f"[Receipt Print] ⚠️ Logo processing failed: {e}")
                # Continue without logo
        
        # Merge template into receipt data
        data['header'] = receipt_template.get('header', '')
        data['footer'] = receipt_template.get('footer', '')
        
        # Format receipt text
        receipt_text = format_receipt_text(data)
        print(f"[Receipt Print] Formatted receipt: {len(receipt_text)} chars")
        
        # Generate ESC/POS commands
        escpos_data = generate_receipt_escpos(
            data, 
            receipt_text,
            logo_bitmap=logo_bitmap
        )
        print(f"[Receipt Print] Generated ESC/POS: {len(escpos_data)} bytes")
        
        # Check print destination
        print_to = device_config.get('print_to', 'printer')
        
        if print_to == 'file':
            # Save to file for testing
            from datetime import datetime
            
            receipts_dir = Path(os.getcwd()) / 'receipts_output'
            receipts_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            bill_number = data.get('bill_number', 'UNKNOWN')
            filename = f"receipt_{bill_number}_{timestamp}.txt"
            filepath = receipts_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(receipt_text)
            
            print(f"[Receipt Print] ✅ SUCCESS - Saved to file: {filepath}")
            print(f"{'='*60}\n")
            
            return jsonify({
                'success': True,
                'print_to': 'file',
                'file_path': str(filepath)
            }), 200
        else:
            # Print to physical printer
            printer_name = device_config.get('receipt_printer_name') or data.get('printer_name')
            
            print(f"[Receipt Print] Printing to: {printer_name or 'default printer'}")
            
            print_data = {
                'type': 'receipt',
                'data': escpos_data,
                'printer_name': printer_name
            }
            
            result = print_to_local_printer(print_data)
            
            if result['success']:
                print(f"[Receipt Print] ✅ SUCCESS - Printed to {result.get('printer')}")
                print(f"{'='*60}\n")
                
                return jsonify({
                    'success': True,
                    'print_to': 'printer',
                    'printer': result.get('printer')
                }), 200
            else:
                print(f"[Receipt Print] ❌ FAILED - {result.get('error')}")
                print(f"{'='*60}\n")
                
                return jsonify(result), 500
    
    except Exception as e:
        print(f"[Receipt Print] ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")
        
        return jsonify({'success': False, 'error': str(e)}), 500


def download_and_process_logo(logo_url, edge_server, paper_width=576):
    """
    Download logo from Django server and prepare for ESC/POS printing
    
    Args:
        logo_url: Relative URL path (e.g., "/media/receipt_logos/YOGYA/BOE/logo.png")
        edge_server: Base server URL (e.g., "http://192.168.1.100:8001")
        paper_width: Printer paper width in pixels (384 for 58mm, 576 for 80mm)
    
    Returns:
        PIL.Image: Processed grayscale image ready for bitmap conversion
    """
    import requests
    from PIL import Image
    from io import BytesIO
    
    # Build full URL
    if logo_url.startswith('/'):
        full_url = edge_server + logo_url
    else:
        full_url = logo_url
    
    print(f"[Logo] Downloading from: {full_url}")
    
    # Download image
    response = requests.get(full_url, timeout=10)
    response.raise_for_status()
    
    # Load with PIL
    image = Image.open(BytesIO(response.content))
    print(f"[Logo] Original size: {image.size[0]}x{image.size[1]}px, mode: {image.mode}")
    
    # Convert to grayscale
    image = image.convert('L')
    
    # Resize to fit paper width (maintain aspect ratio)
    max_width = paper_width - 40  # 20px padding on each side
    if image.width > max_width:
        ratio = max_width / image.width
        new_height = int(image.height * ratio)
        image = image.resize((max_width, new_height), Image.LANCZOS)
        print(f"[Logo] Resized to: {image.size[0]}x{image.size[1]}px")
    else:
        print(f"[Logo] No resize needed (within {max_width}px)")
    
    return image


def image_to_escpos_bitmap(image, max_width=576):
    """
    Convert PIL Image to ESC/POS bitmap commands
    
    Uses ESC * 33 format (24-dot double density)
    """
    # Convert to black & white
    bw_image = image.point(lambda x: 0 if x < 128 else 255, '1')
    width, height = bw_image.size
    
    # Pad height to multiple of 24
    padded_height = ((height + 23) // 24) * 24
    if padded_height > height:
        new_image = Image.new('1', (width, padded_height), 255)
        new_image.paste(bw_image, (0, 0))
        bw_image = new_image
    
    bitmap_data = bytearray()
    
    # Process in 24-dot vertical strips
    for y in range(0, padded_height, 24):
        # ESC * 33 nL nH (24-dot double density mode)
        bitmap_data.extend(b'\x1b*\x21')
        bitmap_data.extend(width.to_bytes(2, 'little'))
        
        # Process each column (left to right)
        for x in range(width):
            # Collect 24 vertical dots into 3 bytes
            for byte_idx in range(3):
                byte_value = 0
                for bit_idx in range(8):
                    pixel_y = y + (byte_idx * 8) + bit_idx
                    if pixel_y < height:
                        pixel = bw_image.getpixel((x, pixel_y))
                        if pixel == 0:  # Black dot
                            byte_value |= (1 << (7 - bit_idx))
                
                bitmap_data.append(byte_value)
        
        # Line feed after each strip
        bitmap_data.extend(b'\x0a')
    
    return bytes(bitmap_data)
```

---

## Troubleshooting Guide

### Common Issues & Solutions

#### 1. Terminal Config Not Loading

**Symptoms:**
- Console error: "Terminal code not found"
- Auto print features not working
- Logo not appearing

**Diagnosis:**
```javascript
// Check localStorage in browser console
console.log('terminal_code:', localStorage.getItem('terminal_code'));
console.log('brand_code:', localStorage.getItem('brand_code'));
console.log('kiosk_mode:', localStorage.getItem('kiosk_mode'));
```

**Solutions:**

| Problem | Solution |
|---------|----------|
| **localStorage empty** | POS Launcher not injecting codes. Check `on_load_finished()` in pos_launcher_qt.py |
| **config.json missing** | Create config.json in pos_launcher_qt folder with required fields |
| **API validation failing** | Check brand_code matches terminal's brand in database |
| **Network error** | Verify edge_server URL in config.json is reachable (http://127.0.0.1:8001) |

#### 2. Logo Not Printing

**Symptoms:**
- Receipt prints but no logo
- Error in local_api logs: "Logo processing failed"

**Diagnosis:**
```bash
# Check logo file exists in Django
ls -lh media/receipt_logos/YOGYA/BOE/

# Check Django API response
curl "http://localhost:8001/api/terminal/config?terminal_code=BOE-001&brand_code=BOE"

# Check logo URL in response
# Should be: "/media/receipt_logos/YOGYA/BOE/20260209_143025_logo.png"
```

**Solutions:**

| Problem | Solution |
|---------|----------|
| **Logo file missing** | Upload logo in Terminal management page |
| **Logo URL absolute** | API should return relative path, not full URL with hostname |
| **Download timeout** | Increase timeout in download_and_process_logo() |
| **Image format error** | Use JPG/PNG only, check file not corrupted |
| **Printer memory** | Logo too large, reduce resolution before upload |

#### 3. Auto Print Not Working

**Symptoms:**
- Checkbox enabled in terminal config
- Payment completes but no print
- Send to Kitchen but no kitchen print

**Diagnosis:**
```javascript
// Check frontend flag
console.log('Config loaded:', terminalConfig);
console.log('Auto print receipt:', terminalConfig?.device_config?.auto_print_receipt);

// Check browser console for errors
// Look for: "Auto print receipt enabled - printing..." 
// or "Auto print receipt disabled - skipping"
```

**Solutions:**

| Feature | Checklist |
|---------|-----------|
| **Auto Print Receipt** | ✅ Flag enabled in terminal config<br>✅ terminalConfig loaded in frontend<br>✅ Local API running on port 5000<br>✅ Printer configured correctly |
| **Auto Print Kitchen** | ✅ Flag enabled in terminal config<br>✅ Kitchen tickets created (check kitchen_ticket table)<br>✅ Kitchen Printer Agent running<br>✅ Agent monitoring correct station codes |
| **Print Checker** | ✅ Flag enabled in terminal config<br>✅ Local API running<br>✅ Printer accessible from POSLauncher |

#### 4. Multi-Factor Validation Failing

**Symptoms:**
- API returns "Validation failed: Brand mismatch"
- Terminal config not loading despite correct terminal_code

**Diagnosis:**
```sql
-- Check terminal in database
SELECT 
    terminal_code,
    company.code as company_code,
    brand.code as brand_code,
    store.code as store_code,
    is_active
FROM core_posterminal terminal
JOIN core_company company ON terminal.company_id = company.id
JOIN core_brand brand ON terminal.brand_id = brand.id
LEFT JOIN core_store store ON terminal.store_id = store.id
WHERE terminal_code = 'BOE-001';
```

**Solutions:**

| Validation Error | Fix |
|-----------------|-----|
| **Company mismatch** | Update company_code in config.json to match database |
| **Brand mismatch** | Update brand_code in config.json to match database |
| **Store mismatch** | Update store_code in config.json or set to null if not required |
| **Terminal inactive** | Set is_active=True in database |

#### 5. Kitchen Printer Agent Not Printing

**Symptoms:**
- Tickets created in database (status='pending')
- Agent running but not printing
- Agent logs: "No pending tickets"

**Diagnosis:**
```bash
# Check agent is running
ps aux | grep kitchen_agent

# Check agent logs
tail -f kitchen_printer_agent/kitchen_agent.log

# Check database for pending tickets
docker-compose exec edge_db psql -U postgres -d fnb_edge_db -c \
  "SELECT id, bill_id, printer_target, status, created_at 
   FROM kitchen_ticket 
   WHERE status='pending' 
   ORDER BY created_at DESC 
   LIMIT 5;"
```

**Solutions:**

| Problem | Solution |
|---------|----------|
| **Agent not monitoring station** | Add station code to kitchen_agent_config.json → station_codes array |
| **Brand filter mismatch** | Check brand_ids in config matches ticket's bill brand |
| **Printer offline** | Check network printer IP reachable, test with ping |
| **Database connection failed** | Verify database credentials in kitchen_agent_config.json |
| **Tickets stuck 'printing'** | Reset status: `UPDATE kitchen_ticket SET status='pending' WHERE status='printing'` |

---

## Summary & Key Takeaways

### Architecture Principles

1. **Terminal-Centric Design**: Every POS station is uniquely identified by a POSTerminal record containing all device-specific configuration
2. **Multi-Factor Security**: Terminal authentication uses 4 validation factors (terminal + brand + company + store) to prevent unauthorized access
3. **Distributed Printing**: Receipt printing via Local API (immediate), Kitchen printing via Agent polling (autonomous)
4. **Template-Based Receipts**: Dynamic receipt layout from database with logo support and organized file storage
5. **Configuration Injection**: Terminal identity injected into browser localStorage after page load for seamless integration

### Critical Implementation Details

| Component | Key Feature | Implementation |
|-----------|-------------|----------------|
| **POS Launcher** | Terminal identity injection | localStorage.setItem() after page load |
| **Terminal Config** | Multi-factor validation | terminal_code + brand_code + company_code + store_code |
| **Receipt Template** | Dynamic logo upload path | receipt_logos/{company}/{brand}/{timestamp}_{file} |
| **Logo Processing** | ESC/POS bitmap conversion | PIL → grayscale → resize → 24-dot bitmap |
| **Auto Print** | Flag-based decision | Frontend checks flag before calling Local API |
| **Kitchen Print** | Autonomous agent polling | Separate service polls database, prints independently |

### Development Best Practices

1. **Always use relative paths** for media URLs (logo_url) - allows dynamic edge_server configuration
2. **Inject codes after page load** - JavaScript localStorage requires DOM ready
3. **Multi-factor validation always** - never trust terminal_code alone
4. **Fail gracefully** - printer errors should not block POS operations
5. **Log extensively** - all print operations logged for debugging and auditing
6. **Test with print_to='file'** - saves receipts to file system for testing without printer

### Future Enhancement Opportunities

- **Terminal Heartbeat**: Auto-detect offline terminals, show status in management
- **Logo Caching**: Cache downloaded logos in Local API to reduce network calls
- **Print Queue**: Queue failed prints for retry when printer comes back online
- **Multi-Language**: Support dynamic language in receipt templates
- **Receipt Analytics**: Track print success rate, average print time per terminal

---

**End of Documentation**

This document should be considered the single source of truth for understanding the POS Launcher, Terminal Configuration, and Receipt Template architecture in the FoodLife POS System.
