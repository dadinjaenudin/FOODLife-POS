# 🏗️ Arsitektur Teknis POS Launcher

## 📋 Daftar Isi

1. [Stack Teknologi](#stack-teknologi)
2. [Struktur File](#struktur-file)
3. [Database Schema](#database-schema)
4. [API Endpoints](#api-endpoints)
5. [Session Management](#session-management)
6. [Payment Modal Deep Dive](#payment-modal-deep-dive)
7. [Bill Panel Integration](#bill-panel-integration)

---

## 🛠️ Stack Teknologi

### Backend Stack

```yaml
Framework: Django 5.2.10
  - Web Framework: Full-featured
  - ORM: Django ORM (untuk database)
  - Template: Django Template Language
  - Server: Daphne (ASGI server)
  - Port: 8001

Database: PostgreSQL 16
  - Container: Docker (postgres:16-alpine)
  - Port: 5433
  - Purpose: Main data storage

Cache: Redis 7
  - Container: Docker (redis:7-alpine)
  - Port: 6380
  - Purpose: Session, cache, celery broker

Storage: MinIO
  - Port: 9002 (API), 9003 (Console)
  - Purpose: Media files (images)

Task Queue: Celery
  - Workers: Default & Low Priority
  - Purpose: Async tasks (reports, sync)
```

### Frontend Stack

```yaml
Launcher: PyQt6 6.10.2
  - WebEngine: QtWebEngineWidgets
  - Purpose: Dual display management
  - Runtime: Python 3.14

Local API: Flask 3.0.0
  - Server: Built-in development server
  - Port: 5000
  - Purpose: Bridge communication

Customer Display:
  - HTML5 + CSS3
  - Alpine.js: Reactive framework
  - Tailwind CSS: Styling
  - SSE: Real-time updates
```

### DevOps Stack

```yaml
Containerization: Docker + Docker Compose
  - Services: 5 containers
  - Network: Bridge (172.18.0.0/16)
  - Volumes: Persistent data

Version Control: Git
  - Repository: GitHub
  - Branch: main
```

---

## 📁 Struktur File

### Directory Tree

```
FoodLife-POS/
│
├── apps/                          # Django apps
│   ├── core/                      # Core functionality
│   │   ├── views.py              # ⭐ Login, logout, setup
│   │   ├── views_terminal.py     # Terminal management
│   │   ├── api_terminal.py       # Terminal API validation
│   │   ├── urls.py               # Core routes
│   │   └── urls_api.py           # API routes
│   │
│   ├── pos/                       # POS main app
│   │   ├── views.py              # ⭐⭐ Main POS view (CRITICAL)
│   │   ├── urls.py               # POS routes
│   │   ├── models.py             # Bill, BillItem, POSTerminal
│   │   └── templatetags/         # Custom filters
│   │
│   ├── kitchen/                   # Kitchen display
│   ├── management/                # Management dashboard
│   ├── promotions/                # Promo engine
│   ├── qr_order/                  # QR ordering
│   └── tables/                    # Table management
│
├── pos_launcher_qt/               # ⭐⭐⭐ POS Launcher (MAIN FOCUS)
│   ├── pos_launcher_qt.py        # Main launcher application
│   ├── local_api.py              # Flask API server
│   ├── customer_display.html     # Customer display HTML
│   ├── config.json               # Terminal configuration
│   ├── customer_display_config.json  # Display settings
│   ├── requirements.txt          # Python dependencies
│   │
│   └── docs/                      # Documentation (THIS FILE)
│       ├── 01_KONSEP_DASAR.md
│       ├── 02_ARSITEKTUR_TEKNIS.md (YOU ARE HERE)
│       ├── 03_DUAL_DISPLAY_SYNC.md
│       └── 04_TROUBLESHOOTING.md
│
├── templates/                     # Django templates
│   ├── pos/
│   │   ├── main.html             # Main POS interface
│   │   └── partials/
│   │       ├── bill_panel.html   # ⭐ Bill sidebar
│   │       ├── payment_modal.html # ⭐⭐ Payment modal (v2.1)
│   │       ├── product_grid.html
│   │       └── ... (other partials)
│   │
│   └── core/
│       ├── login.html            # Login screen
│       └── terminal_setup.html   # Terminal configuration
│
├── static/                        # Static files
│   ├── css/
│   │   ├── output.css            # Tailwind compiled
│   │   └── tailwind.css          # Production copy
│   └── js/
│       ├── alpine.min.js
│       └── htmx.min.js
│
├── docker-compose.yml             # Docker orchestration
├── Dockerfile                     # Django container
├── manage.py                      # Django CLI
└── requirements.txt               # Python dependencies
```

### File Ownership Map

| File | Purpose | Owner | Called By |
|------|---------|-------|-----------|
| `pos_launcher_qt.py` | Main launcher | PyQt6 | User (startup) |
| `local_api.py` | Flask bridge | Flask | pos_launcher_qt.py |
| `views.py` (core) | Login/logout | Django | Browser |
| `views.py` (pos) | Main POS logic | Django | Browser |
| `bill_panel.html` | Bill display | Django | HTMX auto-refresh |
| `payment_modal.html` | Payment UI | Django | User click "Bayar" |
| `customer_display.html` | Customer view | Static HTML | pos_launcher_qt.py |

---

## 🗄️ Database Schema

### Critical Tables

#### 1. POSTerminal
```python
class POSTerminal(models.Model):
    id = models.UUIDField(primary_key=True)
    terminal_code = models.CharField(max_length=20, unique=True)  # e.g., "BOE-001"
    terminal_name = models.CharField(max_length=100)              # e.g., "Kasir 1"
    store = models.ForeignKey('Store')
    is_active = models.BooleanField(default=True)
    
    # Session token untuk auth
    session_token = models.UUIDField()
    token_expires_at = models.DateTimeField()
```

**Relasi:**
- Terminal → Store (Many-to-One)
- Terminal → Bill (One-to-Many)

#### 2. Bill
```python
class Bill(models.Model):
    id = models.UUIDField(primary_key=True)
    bill_number = models.CharField(max_length=50)    # e.g., "INV-2026-0001"
    terminal = models.ForeignKey('POSTerminal')
    status = models.CharField(max_length=20)         # 'active', 'paid', 'hold', 'void'
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('User')
```

**Relasi:**
- Bill → BillItem (One-to-Many)
- Bill → Payment (One-to-Many)
- Bill → POSTerminal (Many-to-One)

#### 3. BillItem
```python
class BillItem(models.Model):
    id = models.UUIDField(primary_key=True)
    bill = models.ForeignKey('Bill', related_name='items')
    product = models.ForeignKey('Product')
    
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Modifiers (extra cheese, no ice, etc.)
    modifiers = models.JSONField(default=list)
    
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20)  # 'pending', 'void', 'served'
```

#### 4. Payment
```python
class Payment(models.Model):
    id = models.UUIDField(primary_key=True)
    bill = models.ForeignKey('Bill', related_name='payments')
    
    payment_method = models.CharField(max_length=20)  # 'cash', 'qris', 'card', etc.
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # For cash
    cash_paid = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    change_due = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    
    # For card/digital
    reference_number = models.CharField(max_length=100, blank=True)
    
    paid_at = models.DateTimeField(auto_now_add=True)
    paid_by = models.ForeignKey('User')
```

### ER Diagram

```
                    ┌─────────────┐
                    │   Store     │
                    └──────┬──────┘
                           │
                           │ 1:N
                           │
                    ┌──────▼──────┐
             ┌─────►│ POSTerminal │◄─────┐
             │      └──────┬──────┘      │
             │             │             │
             │ 1:N         │ 1:N         │ 1:N
             │             │             │
      ┌──────┴──────┐ ┌───▼────┐  ┌─────▼─────┐
      │   User      │ │  Bill  │  │   Shift   │
      └──────┬──────┘ └───┬────┘  └───────────┘
             │            │
             │ 1:N        │ 1:N
             │            │
      ┌──────▼──────┐ ┌──▼────────┐
      │  Payment    │ │ BillItem  │
      └─────────────┘ └───┬───────┘
                          │
                          │ N:1
                          │
                    ┌─────▼─────┐
                    │  Product  │
                    └───────────┘
```

---

## 🌐 API Endpoints

### Django Endpoints (Port 8001)

#### Authentication
```http
POST /login/
  Request: username, password
  Response: Redirect to /pos/ or /pin-login/

GET /logout/
  Action: Clear session (preserve launcher_terminal_code)
  Response: Redirect to /login/

POST /api/terminal/validate
  Request: { "terminal_code": "BOE-001", "session_token": "uuid" }
  Response: { "valid": true, "terminal": {...} }
```

#### POS Main
```http
GET /pos/?terminal=BOE-001&token=xxx&kiosk=1
  Description: Main POS interface
  Authentication: Required (or auto-login in kiosk mode)
  Response: HTML (main.html)

GET /pos/bill-panel/
  Description: Bill sidebar (auto-refresh via HTMX)
  Response: HTML (bill_panel.html)
  Update Interval: Every 2 seconds

POST /pos/add-item/
  Request: { "product_id": "uuid", "quantity": 1 }
  Response: HTML (updated bill_panel.html)

POST /pos/payment/
  Request: { "payment_method": "cash", "amount": 50000 }
  Response: HTML (payment_success.html) or modal with errors
```

#### Shift Management
```http
POST /pos/shift/open/
  Request: { "cashier_name": "John", "opening_cash": 1000000 }
  Response: Redirect to /pos/

POST /pos/shift/close/
  Request: { "closing_cash": 1500000, "notes": "..." }
  Response: Print reconciliation + redirect
```

### Flask Endpoints (Port 5000)

#### Health Check
```http
GET /
  Response: { "status": "ok", "message": "FoodLife POS Customer Display API" }

GET /api/customer-display/config
  Response: {
    "enabled": true,
    "show_images": true,
    "slideshow_interval": 5000,
    ...
  }
```

#### Bill Updates
```http
POST /api/customer-display/update-bill
  Request: {
    "bill_id": "uuid",
    "items": [
      { "name": "Nasi Goreng", "quantity": 1, "price": 25000 }
    ],
    "subtotal": 25000,
    "tax": 2750,
    "total": 27750
  }
  Response: { "status": "success", "message": "Bill updated" }
  Side Effect: Emit SSE event to customer display
```

#### Modal Sync
```http
POST /api/customer-display/show-modal
  Request: {
    "modal_type": "payment",
    "html": "<div>...</div>",
    "data": { "total": 27750, "method": "cash" }
  }
  Response: { "status": "success" }

POST /api/customer-display/hide-modal
  Request: { "modal_type": "payment" }
  Response: { "status": "success" }
```

#### Real-time Stream
```http
GET /api/customer-display/stream
  Type: Server-Sent Events (text/event-stream)
  Description: Push real-time updates to customer display
  
  Event Format:
    event: bill-update
    data: { "bill_id": "...", "items": [...], "total": 27750 }
    
    event: modal-show
    data: { "modal_type": "payment", "html": "..." }
    
    event: modal-hide
    data: { "modal_type": "payment" }
    
    event: clear
    data: { "reason": "payment_success" }

  Keep-Alive: Every 30 seconds
  Reconnect: Client auto-reconnect after 3 seconds on disconnect
```

#### Actions
```http
POST /api/customer-display/clear
  Description: Clear customer display (back to blank/slideshow)
  Response: { "status": "success" }

POST /api/customer-display/slideshow
  Request: { "action": "start" | "stop" | "next" }
  Response: { "status": "success", "current_index": 0 }
```

---

## 🔐 Session Management

### Django Session Keys

```python
# Session structure setelah login
request.session = {
    # User authentication
    '_auth_user_id': '123',
    '_auth_user_backend': 'django.contrib.auth.backends.ModelBackend',
    '_auth_user_hash': 'abcd1234',
    
    # Terminal information
    'terminal_code': 'BOE-001',           # ⚠️ Cleared on logout
    'terminal_id': 'uuid-string',         # ⚠️ Cleared on logout
    'launcher_terminal_code': 'BOE-001',  # ✅ PERSISTENT (preserved on logout)
    
    # Active bill
    'active_bill_id': 'uuid-string',      # Current bill being worked on
    
    # Shift information
    'shift_id': 'uuid-string',
    'shift_opened_at': '2026-02-07T10:00:00',
}
```

### Session Lifecycle

```python
# 1. Startup (dari URL parameter)
if request.GET.get('terminal'):
    request.session['launcher_terminal_code'] = request.GET.get('terminal')
    # Stored persistently ✅

# 2. Login (authentication)
user = authenticate(username=username, password=password)
login(request, user)
# Django otomatis set _auth_user_id, _auth_user_backend, _auth_user_hash

# 3. Terminal detection
if 'launcher_terminal_code' in request.session:
    terminal = POSTerminal.objects.get(
        terminal_code=request.session['launcher_terminal_code']
    )
    request.session['terminal_code'] = terminal.terminal_code
    request.session['terminal_id'] = str(terminal.id)
    # Now terminal is active ✅

# 4. Usage (normal operations)
# Session dibaca di setiap request
terminal_code = request.session.get('terminal_code')
active_bill = request.session.get('active_bill_id')

# 5. Logout (CRITICAL)
def logout_view(request):
    # ⚠️ BACKUP launcher_terminal_code
    launcher_terminal = request.session.get('launcher_terminal_code')
    
    # Django logout (clear user auth)
    auth_logout(request)
    
    # Clear ALL session data
    request.session.flush()
    
    # ✅ RESTORE launcher_terminal_code
    if launcher_terminal:
        request.session['launcher_terminal_code'] = launcher_terminal
        request.session.save()
    
    return redirect('core:login')

# 6. Login lagi (second time)
# launcher_terminal_code masih ada! ✅
# Tidak perlu setup terminal lagi
```

### Cookie Management (PyQt6)

```python
# pos_launcher_qt.py - Lines 176-182
# Clear cookies on startup = force login
profile = QWebEngineProfile.defaultProfile()
cookie_store = profile.cookieStore()
cookie_store.deleteAllCookies()

# Result: Session di browser cleared
# Django akan redirect ke login screen
# launcher_terminal_code tetap ada di session server ✅
```

---

## 💳 Payment Modal Deep Dive

### File: `templates/pos/partials/payment_modal.html`

#### Architecture: Configuration-Driven v2.1

**Konsep**: Modal payment dibangun dari konfigurasi, bukan hardcoded.

```python
# Configuration object
PAYMENT_CONFIG = {
    'methods': {
        'cash': {
            'enabled': True,
            'icon': '💵',
            'label': 'Cash',
            'requires_amount_input': True,
            'show_change': True,
            'primary': True
        },
        'qris': {
            'enabled': True,
            'icon': '📱',
            'label': 'QRIS',
            'requires_amount_input': False,
            'show_qr_code': True,
            'primary': False
        },
        'card': {
            'enabled': True,
            'icon': '💳',
            'label': 'Debit/Credit Card',
            'requires_amount_input': False,
            'requires_reference': True,
            'primary': False
        },
        # ... other methods
    },
    
    'features': {
        'split_payment': True,
        'custom_discount': True,
        'round_payment': True,
        'print_receipt': True
    },
    
    'customer_display': {
        'sync': True,
        'readonly': True,
        'show_buttons': False,
        'whitelist_fields': ['total', 'payment_method', 'amount_paid', 'change']
    }
}
```

#### Modal Structure

```html
<!-- Top-level container -->
<div id="paymentModal"
     x-data="paymentModalData()"
     x-show="$store.modal.payment"
     data-sync-to-customer="true"
     data-customer-readonly="true"
     data-modal-type="payment">
     
    <!-- Header -->
    <div class="modal-header">
        <h3>💰 Payment - Bill #{{ bill.bill_number }}</h3>
        <button @click="closeModal()">✕</button>
    </div>
    
    <!-- Bill Summary -->
    <div class="bill-summary">
        <div class="line-item">
            <span>Subtotal:</span>
            <span>{{ bill.subtotal|currency }}</span>
        </div>
        <div class="line-item">
            <span>Tax (11%):</span>
            <span>{{ bill.tax|currency }}</span>
        </div>
        <div class="line-item discount" x-show="discount > 0">
            <span>Discount:</span>
            <span class="text-red">-{{ discount|currency }}</span>
        </div>
        <div class="line-item total">
            <span>TOTAL:</span>
            <span class="text-xl font-bold">{{ bill.total|currency }}</span>
        </div>
    </div>
    
    <!-- Payment Method Tabs -->
    <div class="payment-methods">
        {% for method_key, method in PAYMENT_CONFIG.methods.items %}
        {% if method.enabled %}
        <button @click="selectMethod('{{ method_key }}')"
                :class="{ 'active': selectedMethod === '{{ method_key }}' }">
            <span>{{ method.icon }}</span>
            <span>{{ method.label }}</span>
        </button>
        {% endif %}
        {% endfor %}
    </div>
    
    <!-- Method-specific forms -->
    
    <!-- Cash Form -->
    <div x-show="selectedMethod === 'cash'" class="payment-form">
        <label>Amount Paid:</label>
        <input type="number"
               x-model.number="cashPaid"
               @input="calculateChange()"
               placeholder="Enter amount"
               :disabled="$store.isCustomerDisplay">
        
        <!-- Quick amount buttons -->
        <div class="quick-amounts" x-show="!$store.isCustomerDisplay">
            <button @click="cashPaid = exactAmount()">Exact</button>
            <button @click="cashPaid = 50000">50K</button>
            <button @click="cashPaid = 100000">100K</button>
            <button @click="cashPaid = roundUp(total)">Round Up</button>
        </div>
        
        <!-- Change display -->
        <div class="change-display" x-show="change >= 0">
            <span>Change:</span>
            <span class="text-2xl font-bold text-green"
                  x-text="formatCurrency(change)"></span>
        </div>
    </div>
    
    <!-- QRIS Form -->
    <div x-show="selectedMethod === 'qris'" class="payment-form">
        <div class="qr-code-container">
            <img :src="qrisUrl" alt="QRIS Code">
        </div>
        <p>Scan QR code with mobile banking app</p>
        <div class="qris-status" x-show="qrisStatus === 'waiting'">
            <div class="spinner"></div>
            <span>Waiting for payment...</span>
        </div>
    </div>
    
    <!-- Card Form -->
    <div x-show="selectedMethod === 'card'" class="payment-form">
        <label>Card Reference Number:</label>
        <input type="text"
               x-model="cardReference"
               placeholder="Enter approval code"
               :disabled="$store.isCustomerDisplay">
        
        <div class="card-instruction">
            <p>1. Insert card into EDC machine</p>
            <p>2. Enter amount: <strong x-text="formatCurrency(total)"></strong></p>
            <p>3. Wait for approval</p>
            <p>4. Enter approval code above</p>
        </div>
    </div>
    
    <!-- Split Payment Section -->
    <div x-show="features.split_payment && splitPayments.length > 0"
         class="split-payments">
        <h4>Split Payments:</h4>
        <template x-for="(payment, index) in splitPayments" :key="index">
            <div class="split-item">
                <span x-text="payment.method"></span>
                <span x-text="formatCurrency(payment.amount)"></span>
                <button @click="removeSplit(index)">Remove</button>
            </div>
        </template>
        <div class="split-remaining">
            <span>Remaining:</span>
            <span x-text="formatCurrency(remainingAmount)"></span>
        </div>
    </div>
    
    <!-- Action Buttons -->
    <div class="modal-actions">
        <button @click="closeModal()"
                class="btn-secondary"
                x-show="!$store.isCustomerDisplay">
            Cancel
        </button>
        
        <button @click="addSplitPayment()"
                class="btn-info"
                x-show="features.split_payment && !$store.isCustomerDisplay"
                :disabled="!canAddSplit()">
            + Add Payment
        </button>
        
        <button @click="processPayment()"
                class="btn-primary"
                x-show="!$store.isCustomerDisplay"
                :disabled="!canProcess()">
            <span x-show="!processing">Confirm Payment</span>
            <span x-show="processing">Processing...</span>
        </button>
    </div>
</div>
```

#### Alpine.js Data Layer

```javascript
function paymentModalData() {
    return {
        // State
        selectedMethod: 'cash',
        cashPaid: 0,
        change: 0,
        cardReference: '',
        qrisUrl: '',
        qrisStatus: 'pending',
        discount: 0,
        splitPayments: [],
        processing: false,
        
        // Computed
        get total() {
            return parseFloat(this.$el.dataset.total);
        },
        
        get remainingAmount() {
            const paid = this.splitPayments.reduce((sum, p) => sum + p.amount, 0);
            return this.total - paid;
        },
        
        // Methods
        selectMethod(method) {
            this.selectedMethod = method;
            
            // Load method-specific data
            if (method === 'qris') {
                this.generateQRIS();
            }
        },
        
        calculateChange() {
            this.change = this.cashPaid - this.total;
        },
        
        exactAmount() {
            return this.total;
        },
        
        roundUp(amount) {
            return Math.ceil(amount / 1000) * 1000;
        },
        
        canProcess() {
            if (this.processing) return false;
            
            switch(this.selectedMethod) {
                case 'cash':
                    return this.cashPaid >= this.total;
                case 'qris':
                    return this.qrisStatus === 'success';
                case 'card':
                    return this.cardReference.length > 0;
                default:
                    return false;
            }
        },
        
        async processPayment() {
            this.processing = true;
            
            const paymentData = {
                bill_id: this.billId,
                payment_method: this.selectedMethod,
                amount: this.total,
                cash_paid: this.cashPaid,
                change: this.change,
                reference: this.cardReference,
                split_payments: this.splitPayments
            };
            
            try {
                const response = await fetch('/pos/payment/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: JSON.stringify(paymentData)
                });
                
                if (response.ok) {
                    // Success
                    const result = await response.text();
                    document.getElementById('payment-result').innerHTML = result;
                    
                    // Clear customer display
                    await fetch('http://localhost:5000/api/customer-display/clear', {
                        method: 'POST'
                    });
                    
                    this.closeModal();
                } else {
                    alert('Payment failed. Please try again.');
                }
            } catch (error) {
                console.error('Payment error:', error);
                alert('Connection error. Please check your network.');
            } finally {
                this.processing = false;
            }
        },
        
        closeModal() {
            this.$store.modal.payment = false;
            
            // Hide modal on customer display
            fetch('http://localhost:5000/api/customer-display/hide-modal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ modal_type: 'payment' })
            });
        }
    }
}
```

#### Customer Display Adaptation

**Di kasir:**
- All buttons enabled
- All inputs editable
- Can cancel, can confirm

**Di customer display:**
```javascript
// Auto-detect customer display mode
if (window.location.port === '5000' || window.isCustomerDisplay) {
    Alpine.store('isCustomerDisplay', true);
}

// Modal rendered dengan kondisi:
// x-show="!$store.isCustomerDisplay" pada semua buttons
// :disabled="$store.isCustomerDisplay" pada semua inputs

// Result:
// - Customer HANYA melihat
// - Tidak bisa interact
// - Informasi transparant
```

---

## 📊 Bill Panel Integration

### File: `templates/pos/partials/bill_panel.html`

#### Purpose
Sidebar yang menampilkan daftar item dalam bill saat ini.

#### Update Mechanism

**HTMX Auto-Polling:**
```html
<!-- In main.html -->
<div id="bill-panel"
     hx-get="/pos/bill-panel/"
     hx-trigger="every 2s"
     hx-swap="innerHTML">
    <!-- Content will be replaced -->
</div>
```

**How it works:**
1. Every 2 seconds, HTMX sends GET request
2. Django renders bill_panel.html with latest data
3. HTMX replaces #bill-panel innerHTML
4. Customer display also gets update via SSE

#### Bill Panel Structure

```html
<div class="bill-panel">
    <!-- Header -->
    <div class="bill-header">
        <h3>Current Order</h3>
        {% if bill %}
        <span class="bill-number">{{ bill.bill_number }}</span>
        {% endif %}
    </div>
    
    <!-- Items List -->
    <div class="bill-items">
        {% if bill and bill.items.exists %}
            {% for item in bill.items.all %}
            <div class="bill-item" data-item-id="{{ item.id }}">
                <div class="item-info">
                    <span class="item-name">{{ item.product.name }}</span>
                    
                    <!-- Modifiers -->
                    {% if item.modifiers %}
                    <div class="item-modifiers">
                        {% for modifier in item.modifiers %}
                        <span class="modifier-badge">{{ modifier.name }}</span>
                        {% endfor %}
                    </div>
                    {% endif %}
                    
                    <!-- Notes -->
                    {% if item.notes %}
                    <div class="item-notes">
                        <small>📝 {{ item.notes }}</small>
                    </div>
                    {% endif %}
                </div>
                
                <div class="item-quantity">
                    <button @click="decreaseQty('{{ item.id }}')">−</button>
                    <span>{{ item.quantity }}</span>
                    <button @click="increaseQty('{{ item.id }}')">+</button>
                </div>
                
                <div class="item-price">
                    {{ item.subtotal|currency }}
                </div>
                
                <div class="item-actions">
                    <button @click="editItem('{{ item.id }}')"
                            class="btn-edit">✏️</button>
                    <button @click="removeItem('{{ item.id }}')"
                            class="btn-remove">🗑️</button>
                </div>
            </div>
            {% endfor %}
        {% else %}
            <div class="empty-bill">
                <p>No items in order</p>
                <p class="text-sm text-gray">Add products to start</p>
            </div>
        {% endif %}
    </div>
    
    <!-- Totals -->
    <div class="bill-totals">
        <div class="total-line">
            <span>Subtotal:</span>
            <span>{{ bill.subtotal|currency }}</span>
        </div>
        
        {% if bill.discount > 0 %}
        <div class="total-line discount">
            <span>Discount:</span>
            <span class="text-red">-{{ bill.discount|currency }}</span>
        </div>
        {% endif %}
        
        <div class="total-line">
            <span>Tax (11%):</span>
            <span>{{ bill.tax|currency }}</span>
        </div>
        
        <div class="total-line grand-total">
            <span>TOTAL:</span>
            <span class="text-2xl font-bold">{{ bill.total|currency }}</span>
        </div>
    </div>
    
    <!-- Actions -->
    <div class="bill-actions">
        <button @click="holdBill()"
                :disabled="!hasBill"
                class="btn-secondary">
            Hold
        </button>
        
        <button @click="openPaymentModal()"
                :disabled="!hasBill"
                class="btn-primary">
            Pay
        </button>
    </div>
</div>
```

#### Django View Logic

```python
# apps/pos/views.py
@login_required
def bill_panel_view(request):
    """Render bill panel partial for HTMX polling"""
    
    # Get active bill from session
    bill_id = request.session.get('active_bill_id')
    bill = None
    
    if bill_id:
        try:
            bill = Bill.objects.select_related('terminal').prefetch_related(
                'items__product',
                'items__modifiers'
            ).get(id=bill_id, status='active')
        except Bill.DoesNotExist:
            # Bill sudah paid/void, clear session
            request.session.pop('active_bill_id', None)
    
    # Calculate totals
    if bill:
        bill.subtotal = sum(item.subtotal for item in bill.items.all())
        bill.tax = bill.subtotal * Decimal('0.11')  # 11% tax
        bill.total = bill.subtotal + bill.tax - bill.discount
        bill.save()
    
    # Send to customer display via Flask
    if bill:
        sync_bill_to_customer_display(bill)
    
    context = {
        'bill': bill,
        'has_bill': bill is not None
    }
    
    return render(request, 'pos/partials/bill_panel.html', context)


def sync_bill_to_customer_display(bill):
    """Send bill data to Flask API for customer display"""
    
    data = {
        'bill_id': str(bill.id),
        'bill_number': bill.bill_number,
        'items': [
            {
                'id': str(item.id),
                'name': item.product.name,
                'quantity': item.quantity,
                'unit_price': float(item.unit_price),
                'subtotal': float(item.subtotal),
                'modifiers': item.modifiers,
                'notes': item.notes
            }
            for item in bill.items.all()
        ],
        'subtotal': float(bill.subtotal),
        'tax': float(bill.tax),
        'discount': float(bill.discount),
        'total': float(bill.total)
    }
    
    try:
        requests.post(
            'http://localhost:5000/api/customer-display/update-bill',
            json=data,
            timeout=1  # Don't block if Flask is down
        )
    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to sync bill to customer display: {e}")
        # Don't fail the main request
```

---

## 🔗 Hubungan POS Launcher ↔ Django

### Communication Flow

```
┌────────────────────────────────────────────────────────────────────┐
│                         USER ACTION                                 │
│                    (Kasir klik "Add Item")                         │
└───────────────────────────┬────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│                  DJANGO VIEW (apps/pos/views.py)                   │
│                                                                     │
│  1. Validate product                                               │
│  2. Add BillItem to database                                       │
│  3. Calculate totals                                               │
│  4. Render bill_panel.html                                         │
│  5. Call sync_bill_to_customer_display()                          │
└───────────────────┬────────────────────────┬───────────────────────┘
                    │                        │
                    │                        │
         ┌──────────▼─────────┐   ┌─────────▼──────────┐
         │  Monitor Kasir     │   │  Flask API         │
         │  (HTMX Update)     │   │  POST /update-bill │
         └────────────────────┘   └─────────┬──────────┘
                                             │
                                             │ Store data
                                             │ + Emit SSE
                                             │
                                  ┌──────────▼─────────────┐
                                  │  Customer Display      │
                                  │  (Auto Update via SSE) │
                                  └────────────────────────┘
```

### Key Integration Points

1. **Terminal Detection** (`apps/pos/views.py` line 160-190)
   - Checks `launcher_terminal_code` from session
   - Fallback if `terminal_code` not set
   - Crucial for kiosk mode

2. **Bill Sync** (`apps/pos/views.py` → Flask API)
   - Every bill change triggers Flask POST
   - Flask stores in memory + emits SSE
   - Customer display auto-updates

3. **Modal Clone** (payment_modal.html → Flask API)
   - Modal HTML sent to Flask
   - Flask forwards to customer display via SSE
   - Customer display injects HTML into DOM

4. **Logout Persistence** (`apps/core/views.py` line 58-75)
   - Backup `launcher_terminal_code`
   - Clear session
   - Restore `launcher_terminal_code`
   - Critical for repeated logins

---

## 📝 Summary

### Critical Files to Understand

| File | Lines of Interest | Why Important |
|------|-------------------|---------------|
| `pos_launcher_qt.py` | 1-300 (all) | Main application entry point |
| `local_api.py` | 1-200 (all) | Bridge between Django & display |
| `apps/core/views.py` | 58-75 | Logout persistence fix |
| `apps/pos/views.py` | 62-75, 160-190 | Terminal detection & kiosk mode |
| `templates/pos/partials/payment_modal.html` | All 427 lines | Payment UI & logic |
| `templates/pos/partials/bill_panel.html` | All | Bill display & sync |

### Technology Interactions

```
PyQt6 (GUI Framework)
  ├─> QWebEngineView (Kasir)     → Django (HTTP)
  ├─> QWebEngineView (Customer)  → Flask (HTTP) → SSE
  └─> Flask Server (Subprocess)  → In-memory store

Django (Business Logic)
  ├─> PostgreSQL (Persistent Data)
  ├─> Redis (Session & Cache)
  └─> Flask API (Customer Display Bridge)

Flask (Real-time Bridge)
  ├─> SSE (Push to Customer Display)
  └─> In-memory Store (bills_data, modal_data)
```

---

**Next**: [03_DUAL_DISPLAY_SYNC.md](./03_DUAL_DISPLAY_SYNC.md) - Deep dive pada mekanisme sinkronisasi real-time

---

**Dibuat**: 2026-02-07  
**Versi**: 1.0  
**Kompleksitas**: Advanced
