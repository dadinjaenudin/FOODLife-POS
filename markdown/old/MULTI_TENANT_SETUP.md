# MULTI-TENANT SETUP MECHANISM

## 🏢 Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                    MULTI-TENANT                       │
│                     HIERARCHY                         │
└──────────────────────────────────────────────────────┘

     🏢 COMPANY (Top Level Tenant)
          │  - Yogya Group
          │  - Code: YGY
          │  - Loyalty Policy: 12 months expiry
          │
          ├─── 🏪 BRAND #1 (Business Concept)
          │      │  - Ayam Geprek Express
          │      │  - Code: YGY-001
          │      │  - Tax: 11%, Service: 5%
          │      │
          │      ├─── 🏬 STORE #1 (Physical Location - Edge Server)
          │      │      │  - Cabang BSD
          │      │      │  - Code: YGY-001-BSD
          │      │      │  - SINGLETON per Edge Server!
          │      │      │
          │      │      ├─── 💻 TERMINAL #1
          │      │      │      - POS Kasir 1
          │      │      │      - Code: BSD-POS1
          │      │      │      - Type: pos
          │      │      │
          │      │      ├─── 📱 TERMINAL #2
          │      │      │      - Tablet Waiter 1
          │      │      │      - Code: BSD-TAB1
          │      │      │      - Type: tablet
          │      │      │
          │      │      └─── 🖥️ TERMINAL #3
          │      │             - Kitchen Display
          │      │             - Code: BSD-KDS1
          │      │             - Type: kitchen_display
          │      │
          │      └─── 🏬 STORE #2
          │             - Cabang Senayan (Different Edge Server)
          │             - Code: YGY-001-SNY
          │
          └─── 🏪 BRAND #2
                 - Bakso Boedjangan
                 - Code: YGY-002
```

---

## 🔐 Setup Flow: http://127.0.0.1:8000/setup/

### **STEP 1: Check Configuration Status**

**URL**: `http://127.0.0.1:8000/setup/`  
**View**: `apps/core/views_setup.py::setup_wizard()`

```python
def setup_wizard(request):
    store_config = Store.get_current()  # ← Check singleton store
    
    if store_config:
        # ✅ Already configured → Show status page
        return render(request, 'core/setup_status.html', {
            'store': store_config,
            'terminals': POSTerminal.objects.filter(store=store_config),
            'is_configured': True
        })
    
    # ❌ Not configured → Check if company exists
    companies = Company.objects.filter(is_active=True)
    
    if not companies.exists():
        # No company → Show company creation form
        return render(request, 'core/setup_company.html')
    
    # Company exists → Show store setup form
    return render(request, 'core/setup_store.html', {
        'companies': companies,
    })
```

**Decision Tree:**
```
Store exists?
  ├─ YES → Show setup_status.html (Configuration Complete)
  └─ NO → Company exists?
            ├─ YES → Show setup_store.html (Select Company/Brand, Create Store)
            └─ NO → Show setup_company.html (Create Company First)
```

**Performance Optimization:**
```python
# ✅ OPTIMIZED: Use prefetch_related to avoid N+1 queries
companies = Company.objects.filter(is_active=True).prefetch_related('brands')
```

**Query Efficiency:**
- Without prefetch: 1 + N queries (1 for companies, 1 query per company for brands)
- With prefetch: 2 queries total (1 for companies, 1 for all brands)
- **Impact**: 10x-100x faster for systems with many companies/brands

---

### **STEP 2A: Create Company (if no company exists)**

**URL**: `POST /setup/company/`  
**View**: `apps/core/views_setup.py::setup_company()`

```python
def setup_company(request):
    if request.method == 'POST':
        code = request.POST.get('code').strip().upper()  # YGY
        name = request.POST.get('name').strip()          # Yogya Group
        timezone = request.POST.get('timezone', 'Asia/Jakarta')
        
        # 1. Create Company
        company = Company.objects.create(
            code=code,
            name=name,
            timezone=timezone
        )
        
        # 2. Auto-create default Brand
        brand = Brand.objects.create(
            company=company,
            code=f'{code}-01',                  # YGY-01
            name=f'{name} - Main',              # Yogya Group - Main
            address='',
            phone='',
        )
        
        # 3. Redirect back to setup wizard
        return redirect('core:setup_wizard')
```

**Result:**
- ✅ Company created (e.g., Yogya Group - YGY)
- ✅ Default Brand auto-created (e.g., YGY-01)
- ↩️ Redirect to `/setup/` → Now shows store setup form

---

### **STEP 2B: Create Store (Edge Server Configuration)**

**URL**: `POST /setup/store-config/`  
**View**: `apps/core/views_setup.py::setup_store_config()`

```python
def setup_store_config(request):
    # Enforce singleton: Only 1 store per Edge Server!
    if Store.objects.exists():
        messages.warning(request, 'Store already configured')
        return redirect('core:setup_wizard')
    
    if request.method == 'POST':
        brand_id = request.POST.get('brand_id')              # UUID of selected brand
        store_code = request.POST.get('store_code').upper()  # YGY-001-BSD
        store_name = request.POST.get('store_name')          # Cabang BSD
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        
        # Validation
        if not all([brand_id, store_code, store_name]):
            messages.error(request, 'Brand, store code, and name are required')
            return redirect('core:setup_wizard')
        
        try:
            # 1. Get Brand object
            brand = Brand.objects.get(id=brand_id)
            
            # 2. Create Store (SINGLETON)
            store_config = Store.objects.create(
                brand=brand,                    # ← Link to Brand (FK)
                store_code=store_code,          # YGY-001-BSD
                store_name=store_name,          # Cabang BSD
                address=address,
                phone=phone,
            )
            
            # 3. Redirect to terminal registration
            messages.success(request, f'Store "{store_name}" configured!')
            return redirect('core:terminal_setup')
            
        except Brand.DoesNotExist:
            messages.error(request, 'Invalid brand selected')
```

**Key Features:**
- ✅ **Singleton Pattern**: `Store.save()` enforces only 1 store per Edge Server
- ✅ **Brand Foreign Key**: Links store to specific brand (and company via brand.company)
- ✅ **Auto-generated code**: Suggested format `{BRAND_CODE}-{LOCATION}` (e.g., YGY-001-BSD)
- ↩️ **Auto-redirect**: After success → `/setup/terminal/` for terminal registration

---

### **STEP 3: Register Terminal**

**URL**: `http://127.0.0.1:8000/setup/terminal/`  
**View**: `apps/core/views_terminal.py::terminal_setup()`

```python
def terminal_setup(request):
    store = Store.get_current()
    
    if not store:
        # Store not configured → Show error
        return render(request, 'core/terminal_setup_error.html', {
            'error': 'Store not configured. Please complete setup first.'
        })
    
    if request.method == 'POST':
        terminal_code = request.POST.get('terminal_code').upper()  # BSD-POS1
        terminal_name = request.POST.get('terminal_name')           # Kasir 1
        device_type = request.POST.get('device_type')               # pos/tablet/kiosk
        
        # Create Terminal
        terminal = POSTerminal.objects.create(
            store=store,                      # ← Link to Store (FK)
            terminal_code=terminal_code,
            terminal_name=terminal_name,
            device_type=device_type,
            ip_address=get_client_ip(request),
            registered_by=request.user,
        )
        
        # Store terminal_id in session
        request.session['terminal_id'] = str(terminal.id)
        
        # Return JSON with terminal + company info
        return JsonResponse({
            'success': True,
            'terminal': {
                'id': str(terminal.id),
                'code': terminal.terminal_code,
                'name': terminal.terminal_name,
                'type': terminal.device_type,
            },
            'store': {
                'id': str(store.id),
                'code': store.store_code,
                'name': store.store_name,
            },
            'brand': {
                'id': str(store.brand.id),
                'code': store.brand.code,
                'name': store.brand.name,
            },
            'company': {
                'id': str(store.brand.company.id),
                'code': store.brand.company.code,
                'name': store.brand.company.name,
            }
        })
```

**Key Features:**
- ✅ **Store Validation**: Must complete store setup first
- ✅ **Multiple Terminals**: Can register many terminals per store
- ✅ **Session Storage**: Terminal ID stored in `request.session['terminal_id']`
- ✅ **Full Context**: Returns complete hierarchy (Terminal → Store → Brand → Company)
- ✅ **Auto IP Detection**: Records terminal's IP address
- ✅ **User Tracking**: Records who registered the terminal

---

## 📊 Database Relationships

### **Foreign Key Chain**
```
Terminal.store → Store.brand → Brand.company → Company
   (FK)             (FK)           (FK)
```

### **Models Schema**

#### **1. Company (Top Level)**
```python
class Company(models.Model):
    id = UUIDField(primary_key=True)           # UUID for multi-tenant isolation
    code = CharField(max_length=20, unique=True)   # YGY
    name = CharField(max_length=200)               # Yogya Group
    timezone = CharField(default='Asia/Jakarta')
    
    # Loyalty Configuration (Company-wide)
    point_expiry_months = IntegerField(default=12)
    points_per_currency = DecimalField(default=1.00)
```

**Uniqueness**: `code` is globally unique  
**Isolation**: Each company is completely isolated  
**Policy**: Company-wide loyalty/points configuration

#### **2. Brand (Business Concept)**
```python
class Brand(models.Model):
    id = UUIDField(primary_key=True)
    company = ForeignKey(Company, on_delete=CASCADE)  # ← Parent company
    code = CharField(max_length=20)                   # YGY-001
    name = CharField(max_length=100)                  # Ayam Geprek Express
    
    # Brand-specific settings
    tax_rate = DecimalField(default=11.00)            # 11% PPN
    service_charge = DecimalField(default=5.00)       # 5% service
    
    # Brand can override company loyalty policy
    point_expiry_months_override = IntegerField(null=True, blank=True)
    
    class Meta:
        unique_together = [['company', 'code']]       # Code unique within company
```

**Uniqueness**: `(company, code)` composite unique  
**Hierarchy**: Multiple brands per company  
**Override**: Can override company loyalty policy

#### **3. Store (Physical Location - Edge Server)**
```python
class Store(models.Model):
    brand = ForeignKey(Brand, on_delete=PROTECT)   # ← Parent brand
    store_code = CharField(max_length=20, unique=True)  # YGY-001-BSD (globally unique!)
    store_name = CharField(max_length=200)              # Cabang BSD
    address = TextField(blank=True)
    phone = CharField(max_length=20, blank=True)
    timezone = CharField(default='Asia/Jakarta')
    
    # Geolocation (optional)
    latitude = DecimalField(null=True, blank=True)
    longitude = DecimalField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        # ⚠️ SINGLETON ENFORCEMENT
        if not self.pk and Store.objects.exists():
            raise ValueError('Store already exists. Only one store per Edge Server.')
        return super().save(*args, **kwargs)
    
    @classmethod
    def get_current(cls):
        """Get the singleton store for this Edge Server"""
        return cls.objects.first()
```

**Uniqueness**: `store_code` is globally unique (across all companies!)  
**Singleton**: Only 1 store per Django instance (Edge Server)  
**Edge Pattern**: Each physical location runs separate Django instance

#### **4. POSTerminal (Device Registration)**
```python
class POSTerminal(models.Model):
    DEVICE_TYPE_CHOICES = [
        ('pos', 'POS / Kasir'),
        ('tablet', 'Tablet / Waiter'),
        ('kiosk', 'Self-Service Kiosk'),
        ('kitchen_display', 'Kitchen Display'),
    ]
    
    id = UUIDField(primary_key=True)
    store = ForeignKey(Store, on_delete=CASCADE)      # ← Parent store
    terminal_code = CharField(max_length=20, unique=True)  # BSD-POS1
    terminal_name = CharField(max_length=100)              # Kasir 1
    device_type = CharField(max_length=20, choices=DEVICE_TYPE_CHOICES)
    
    # Network tracking
    ip_address = GenericIPAddressField(null=True)
    mac_address = CharField(max_length=17, blank=True)
    last_heartbeat = DateTimeField(null=True)
    
    # Status
    is_active = BooleanField(default=True)
    registered_by = ForeignKey(User, null=True)
```

**Uniqueness**: `terminal_code` is globally unique  
**Multiplicity**: Multiple terminals per store  
**Heartbeat**: Tracks terminal online/offline status  
**Session**: Terminal ID stored in `request.session['terminal_id']`

---

## 🔄 Multi-Tenant Data Isolation

### **Query Patterns**

#### **Get Current Tenant Context**
```python
# In views/services
store = Store.get_current()                  # Singleton store
brand = store.brand                          # Current brand
company = brand.company                      # Current company
```

#### **Filter Products by Brand**
```python
# Products are brand-specific
products = Product.objects.filter(brand=brand)

# Categories are brand-specific
categories = Category.objects.filter(brand=brand)
```

#### **Filter Bills by Store**
```python
# Bills are store-specific
bills = Bill.objects.filter(store=store)

# With denormalized company_id for reporting
bills = Bill.objects.filter(company_id=company.id)  # All bills for company
```

#### **User Authorization by Scope**
```python
class User(AbstractUser):
    role_scope = models.CharField(choices=[
        ('store', 'Store Level'),      # Can only see own store
        ('brand', 'Brand Level'),       # Can see all stores in brand
        ('company', 'Company Level'),   # Can see all brands & stores
    ])
    
    brand = ForeignKey(Brand)          # Assigned brand
    company = ForeignKey(Company)      # Assigned company

# In views
if request.user.role_scope == 'store':
    # Filter by current store only
    bills = Bill.objects.filter(store=store)
    
elif request.user.role_scope == 'brand':
    # Filter by user's assigned brand
    bills = Bill.objects.filter(store__brand=request.user.brand)
    
elif request.user.role_scope == 'company':
    # Filter by user's assigned company
    bills = Bill.objects.filter(company=request.user.company)
```

---

## 🎯 Setup Scenarios

### **Scenario 1: Fresh Installation (No Data)**

```bash
Step 1: Access http://127.0.0.1:8000/setup/
Result: Shows "Create Company" form (no companies exist)

Step 2: Fill company form
  - Code: YGY
  - Name: Yogya Group
  - Timezone: Asia/Jakarta
Result: Company created + Auto-creates default brand "YGY-01"

Step 3: Redirected to setup wizard
Result: Shows "Create Store" form with brand dropdown

Step 4: Fill store form
  - Select Brand: YGY-01 (Yogya Group - Main)
  - Store Code: YGY-001-BSD
  - Store Name: Cabang BSD
  - Address: Jl. BSD Raya No. 1
  - Phone: 021-12345678
Result: Store created (singleton)

Step 5: Redirected to terminal setup
Result: Shows "Register Terminal" form

Step 6: Fill terminal form
  - Terminal Code: BSD-POS1
  - Terminal Name: Kasir 1
  - Device Type: pos
Result: Terminal registered + Session stores terminal_id

Step 7: Redirected to POS
Result: Can now access POS system at /pos/
```

---

### **Scenario 2: Company Exists (Add New Store)**

```bash
Step 1: Access http://127.0.0.1:8000/setup/
Result: Shows "Create Store" form (company "YGY" already exists)

Step 2: Create new brand (via Django admin)
  - Company: Yogya Group
  - Code: YGY-002
  - Name: Bakso Boedjangan
  - Tax: 11%, Service: 5%
  
Step 3: Back to setup wizard
Result: Dropdown now shows 2 brands:
  - YGY-001: Yogya Group - Main
  - YGY-002: Bakso Boedjangan

Step 4: Select brand YGY-002
  - Store Code: YGY-002-JKT
  - Store Name: Cabang Jakarta
Result: Store created for Bakso Boedjangan brand

Step 5: Register terminals for this store
```

---

### **Scenario 3: Store Already Configured**

```bash
Step 1: Access http://127.0.0.1:8000/setup/
Result: Shows "Setup Status" page (store already exists)

Page displays:
  - ✅ Company: Yogya Group (YGY)
  - ✅ Brand: Ayam Geprek Express (YGY-001)
  - ✅ Store: Cabang BSD (YGY-001-BSD)
  - 📋 Registered Terminals:
      - BSD-POS1 (Kasir 1) - Online
      - BSD-TAB1 (Tablet Waiter 1) - Offline
      - BSD-KDS1 (Kitchen Display) - Online

Options:
  - Register New Terminal
  - Reset Configuration (Superuser only)
```

---

## 🔧 Reset Configuration

**URL**: `POST /setup/reset/`  
**View**: `apps/core/views_setup.py::setup_reset()`  
**Auth**: Superuser only

```python
def setup_reset(request):
    if not request.user.is_superuser:
        messages.error(request, 'Unauthorized')
        return redirect('core:setup_wizard')
    
    if request.method == 'POST':
        confirm = request.POST.get('confirm', '').lower()
        if confirm == 'reset':
            # ⚠️ DANGER: Delete all store data
            POSTerminal.objects.all().delete()   # Delete terminals first (FK)
            Store.objects.all().delete()          # Delete store
            
            messages.success(request, 'Configuration reset. Start fresh.')
        else:
            messages.error(request, 'Confirmation failed')
    
    return redirect('core:setup_wizard')
```

**What Gets Deleted:**
- ✅ Store configuration (singleton)
- ✅ All terminals registered to store
- ❌ Company/Brand NOT deleted (intentional)
- ❌ User accounts NOT deleted
- ❌ Products/Bills NOT deleted

**Use Case**: 
- Reconfigure Edge Server for different store
- Move hardware to different location
- Fix misconfiguration

---

## 📝 URL Routing

**File**: `apps/core/urls.py`

```python
urlpatterns = [
    # Setup Wizard
    path('setup/', views_setup.setup_wizard, name='setup_wizard'),
    path('setup/company/', views_setup.setup_company, name='setup_company'),
    path('setup/store-config/', views_setup.setup_store_config, name='setup_store_config'),
    path('setup/reset/', views_setup.setup_reset, name='setup_reset'),
    
    # Terminal Registration
    path('setup/terminal/', views_terminal.terminal_setup, name='terminal_setup'),
    path('api/terminal/heartbeat/', views_terminal.terminal_heartbeat, name='terminal_heartbeat'),
    path('admin/terminals/', views_terminal.terminal_list, name='terminal_list'),
]
```

**Named URLs:**
- `core:setup_wizard` → Main setup page
- `core:setup_company` → POST: Create company
- `core:setup_store_config` → POST: Create store
- `core:setup_reset` → POST: Reset configuration
- `core:terminal_setup` → GET/POST: Terminal registration

---

## 🎨 Templates

### **1. setup_company.html**
**Rendered when**: No companies exist

```html
<form method="POST" action="{% url 'core:setup_company' %}">
    <input name="code" placeholder="Company Code (e.g., YGY)">
    <input name="name" placeholder="Company Name (e.g., Yogya Group)">
    <select name="timezone">
        <option value="Asia/Jakarta">Asia/Jakarta</option>
    </select>
    <button type="submit">Create Company</button>
</form>
```

### **2. setup_store.html**
**Rendered when**: Company exists, but no store configured

```html
<form method="POST" action="{% url 'core:setup_store_config' %}">
    <select name="brand_id">
        {% for company in companies %}
            <optgroup label="{{ company.name }}">
                {% for brand in company.brands.all %}
                    <option value="{{ brand.id }}">{{ brand.code }} - {{ brand.name }}</option>
                {% endfor %}
            </optgroup>
        {% endfor %}
    </select>
    
    <input name="store_code" placeholder="Store Code (e.g., YGY-001-BSD)">
    <input name="store_name" placeholder="Store Name (e.g., Cabang BSD)">
    <textarea name="address" placeholder="Address"></textarea>
    <input name="phone" placeholder="Phone">
    
    <button type="submit">Configure Store</button>
</form>
```

### **3. setup_status.html**
**Rendered when**: Store already configured

```html
<div class="status">
    <h2>✅ Store Configured</h2>
    
    <dl>
        <dt>Company:</dt>
        <dd>{{ store.brand.company.name }} ({{ store.brand.company.code }})</dd>
        
        <dt>Brand:</dt>
        <dd>{{ store.brand.name }} ({{ store.brand.code }})</dd>
        
        <dt>Store:</dt>
        <dd>{{ store.store_name }} ({{ store.store_code }})</dd>
    </dl>
    
    <h3>Registered Terminals</h3>
    <ul>
        {% for terminal in terminals %}
        <li>
            {{ terminal.terminal_code }} - {{ terminal.terminal_name }}
            {% if terminal.is_online %}🟢 Online{% else %}🔴 Offline{% endif %}
        </li>
        {% endfor %}
    </ul>
    
    <a href="{% url 'core:terminal_setup' %}">Register New Terminal</a>
    
    {% if user.is_superuser %}
    <form method="POST" action="{% url 'core:setup_reset' %}">
        <input name="confirm" placeholder="Type 'reset' to confirm">
        <button type="submit">⚠️ Reset Configuration</button>
    </form>
    {% endif %}
</div>
```

---

## 🚨 Common Issues & Solutions

### **Issue 1: "Store already configured"**
**Cause**: Trying to create second store on same Edge Server  
**Solution**: Store is singleton. Use `/setup/reset/` to reconfigure OR use different Django instance for second store

### **Issue 2: "Brand.DoesNotExist"**
**Cause**: Selected brand was deleted after page load  
**Solution**: Refresh page, select valid brand

### **Issue 3: Terminal can't register**
**Cause**: Store not configured  
**Solution**: Complete store setup first at `/setup/`

### **Issue 4: Company dropdown empty**
**Cause**: No active companies (`is_active=True`)  
**Solution**: Create company via `/setup/` or activate in Django admin

### **Issue 5: `asyncio.exceptions.CancelledError`**
**Cause**: Browser cancelled request (refresh/navigate before response completed)  
**When it happens**: 
- User refreshes page too quickly
- Slow database query (N+1 problem)
- Network interruption

**Solution**:
```python
# ✅ FIXED: Added prefetch_related to avoid N+1 queries
companies = Company.objects.filter(is_active=True).prefetch_related('brands')
```

**Impact**: 
- ✅ Reduces queries from N+1 to 2 queries (1 for companies, 1 for brands)
- ✅ Faster page load (10x-100x for many brands)
- ✅ Less likely to get CancelledError

**If error persists**:
1. Wait for page to fully load before refreshing
2. Check network connection
3. Increase timeout in browser
4. Check Django logs for actual errors (CancelledError can be ignored)

**Note**: This error is **usually harmless** and can be ignored if:
- Page loads successfully after refresh
- No data corruption
- No actual errors in Django logs

---

## ✅ Validation Rules

### **Company Validation**
- ✅ `code` must be unique globally
- ✅ `code` auto-converted to uppercase
- ✅ `name` is required
- ✅ `timezone` defaults to `Asia/Jakarta`

### **Brand Validation**
- ✅ `(company, code)` must be unique together
- ✅ `company` foreign key required
- ✅ `tax_rate` and `service_charge` default to sensible values

### **Store Validation**
- ✅ Only 1 store per Django instance (singleton)
- ✅ `store_code` must be unique globally
- ✅ `store_code` auto-converted to uppercase
- ✅ `brand` foreign key required
- ✅ `Store.save()` raises `ValueError` if duplicate

### **Terminal Validation**
- ✅ `terminal_code` must be unique globally
- ✅ `terminal_code` auto-converted to uppercase
- ✅ `store` foreign key required
- ✅ `device_type` must be one of: pos/tablet/kiosk/kitchen_display

---

## 🔍 Testing the Setup Flow

### **Test Case 1: Fresh Installation**
```bash
# 1. Reset database
python reset_database.bat

# 2. Create superuser
python create_superuser.bat

# 3. Start server
python manage.py runserver

# 4. Open browser
http://127.0.0.1:8000/setup/

# Expected: Shows "Create Company" form
```

### **Test Case 2: With Existing Company**
```bash
# 1. Create company via Django admin or script
python create_default_superuser.py  # Creates Yogya Group + Head Office

# 2. Open setup
http://127.0.0.1:8000/setup/

# Expected: Shows "Create Store" form with brand dropdown
```

### **Test Case 3: Already Configured**
```bash
# 1. Complete full setup (company + brand + store)

# 2. Open setup again
http://127.0.0.1:8000/setup/

# Expected: Shows "Setup Status" page with terminal list
```

---

## 📚 Related Documentation

- **[SETUP_STORE.md](SETUP_STORE.md)** - Product import and bulk data setup
- **[TERMINAL_SETUP_FLOW.md](TERMINAL_SETUP_FLOW.md)** - Terminal registration details
- **[DATABASE_ERD.md](DATABASE_ERD.md)** - Multi-tenant database schema
- **[DENORMALIZATION_DECISION.md](DENORMALIZATION_DECISION.md)** - Company ID denormalization for reporting

---

**Last Updated**: January 2026  
**Version**: 2.0  
**Status**: ✅ Production Ready
