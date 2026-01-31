# Food Court Multi-Brand Architecture Analysis

## 🎯 Business Model (Corrected Understanding)

### Scenario: Food Court / Multi-Brand Store

**Example:**
- **Company:** YOGYA (1 per Edge Server)
- **Store:** YOGYA SUNDA (1 per Edge Server) - Physical location
- **Brands:** Multiple brands dalam 1 store (CHICKEN SUMO, NASI PADANG, SOTO LAMONGAN)
- **Terminals:** Each terminal dedicated to 1 brand

```
Physical Location: YOGYA SUNDA FOOD COURT
├─ Company: YOGYA
└─ Store: YOGYA SUNDA
    ├─ Brand: CHICKEN SUMO
    │   ├─ Terminal: T01-SUMO
    │   ├─ Terminal: T02-SUMO
    │   └─ Products: Chicken menu items
    │
    ├─ Brand: NASI PADANG
    │   ├─ Terminal: T03-PADANG
    │   └─ Products: Padang menu items
    │
    └─ Brand: SOTO LAMONGAN
        ├─ Terminal: T04-SOTO
        └─ Products: Soto menu items
```

## 🚨 Problem with Current Schema

### Current Schema:
```python
class Store(models.Model):
    brand = models.ForeignKey(Brand)  # ❌ 1 Store = 1 Brand only
    store_code = models.CharField()
    store_name = models.CharField()
```

**Problem:** Store hanya bisa punya 1 brand!

### Current Relationship:
```
Company (1) → Brand (Many) → Store (Many)
```

**This means:**
- 1 Company has many Brands
- 1 Brand has many Stores
- ❌ But 1 Store can only belong to 1 Brand!

## ✅ Proposed Solution: Store-Brand Many-to-Many

### New Schema:

```python
class Company(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    timezone = models.CharField(max_length=50)

class Brand(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)

class Store(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    store_code = models.CharField(max_length=20, unique=True)
    store_name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    
    class Meta:
        # ✅ Constraint: Only 1 Store per Company in Edge Server
        unique_together = [['company', 'store_code']]

class StoreBrand(models.Model):
    """Many-to-Many relationship between Store and Brand"""
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='store_brands')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='brand_stores')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = [['store', 'brand']]
        verbose_name = 'Store Brand'
        verbose_name_plural = 'Store Brands'

class Terminal(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)  # ✅ Terminal dedicated to brand
    terminal_code = models.CharField(max_length=20, unique=True)
    terminal_name = models.CharField(max_length=100)
    
    class Meta:
        unique_together = [['store', 'terminal_code']]
```

## 🏗️ Database Relationships

```
┌─────────────┐
│   Company   │ (1 per Edge Server)
│   YOGYA     │
└──────┬──────┘
       │
       ├───────────────────┬────────────────────┐
       │                   │                    │
┌──────▼──────┐   ┌────────▼────────┐   ┌──────▼──────┐
│    Brand    │   │     Brand       │   │    Brand    │
│CHICKEN SUMO │   │  NASI PADANG    │   │SOTO LAMONGAN│
└──────┬──────┘   └────────┬────────┘   └──────┬──────┘
       │                   │                    │
       │         ┌─────────▼────────┐          │
       │         │      Store       │          │
       └────────►│  YOGYA SUNDA     │◄─────────┘
                 │  (1 per Edge)    │
                 └─────────┬────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐      ┌─────▼─────┐    ┌─────▼─────┐
    │Terminal │      │ Terminal  │    │ Terminal  │
    │T01-SUMO │      │T03-PADANG │    │T04-SOTO   │
    │Brand:   │      │Brand:     │    │Brand:     │
    │SUMO     │      │PADANG     │    │LAMONGAN   │
    └─────────┘      └───────────┘    └───────────┘
```

## 📊 Database Example

### Companies Table
```sql
id      | code  | name        | timezone
--------|-------|-------------|-------------
uuid-1  | YOGYA | YOGYA GROUP | Asia/Jakarta
```

### Brands Table
```sql
id      | company_id | code    | name
--------|------------|---------|---------------
uuid-2  | uuid-1     | SUMO    | CHICKEN SUMO
uuid-3  | uuid-1     | PADANG  | NASI PADANG
uuid-4  | uuid-1     | SOTO    | SOTO LAMONGAN
```

### Stores Table (1 row only per Edge Server!)
```sql
id      | company_id | store_code | store_name
--------|------------|------------|-------------
uuid-5  | uuid-1     | YGY-SND    | YOGYA SUNDA
```

### StoreBrand Table (Many-to-Many)
```sql
id      | store_id | brand_id | is_active
--------|----------|----------|----------
uuid-6  | uuid-5   | uuid-2   | true      -- YOGYA SUNDA has CHICKEN SUMO
uuid-7  | uuid-5   | uuid-3   | true      -- YOGYA SUNDA has NASI PADANG
uuid-8  | uuid-5   | uuid-4   | true      -- YOGYA SUNDA has SOTO LAMONGAN
```

### Terminals Table
```sql
id      | store_id | brand_id | terminal_code | terminal_name
--------|----------|----------|---------------|------------------
uuid-9  | uuid-5   | uuid-2   | T01-SUMO      | Kasir Chicken Sumo
uuid-10 | uuid-5   | uuid-3   | T03-PADANG    | Kasir Nasi Padang
uuid-11 | uuid-5   | uuid-4   | T04-SOTO      | Kasir Soto Lamongan
```

## 🎨 UI Design

### Setup Page

```
┌───────────────────────────────────────────────────────────┐
│        Setup Edge Server - Food Court Configuration       │
├───────────────────────────────────────────────────────────┤
│                                                            │
│  Company Configuration (One-time)                         │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Company: [YOGYA GROUP ▼] (from HO)                 │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                            │
│  Store Configuration (One-time)                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Store Code: [YGY-SND]                              │ │
│  │ Store Name: [YOGYA SUNDA]                          │ │
│  │ Address: [Jl. Sunda No. 123, Bandung]             │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                            │
│  Brands in This Store (Multiple)                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ ☑ CHICKEN SUMO                                      │ │
│  │ ☑ NASI PADANG                                       │ │
│  │ ☑ SOTO LAMONGAN                                     │ │
│  │ ☐ GRIYA PREMIUM                                     │ │
│  │ ☐ YOMART                                            │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                            │
│  [💾 Save Configuration]                                  │
│                                                            │
└───────────────────────────────────────────────────────────┘
```

### Terminal Registration Page

```
┌───────────────────────────────────────────────────────────┐
│              Register New Terminal                         │
├───────────────────────────────────────────────────────────┤
│                                                            │
│  Store: YOGYA SUNDA (read-only)                           │
│                                                            │
│  Assign to Brand: [Select Brand ▼]                        │
│                    ├─ CHICKEN SUMO                        │
│                    ├─ NASI PADANG                         │
│                    └─ SOTO LAMONGAN                       │
│                                                            │
│  Terminal Code: [T01-SUMO]                                │
│  Terminal Name: [Kasir Chicken Sumo]                      │
│                                                            │
│  [Register Terminal]                                      │
│                                                            │
└───────────────────────────────────────────────────────────┘
```

### POS Terminal View

```
┌───────────────────────────────────────────────────────────┐
│  Terminal: T01-SUMO | Brand: CHICKEN SUMO                 │
│  Store: YOGYA SUNDA | Cashier: John Doe                  │
├───────────────────────────────────────────────────────────┤
│                                                            │
│  [Products dari CHICKEN SUMO brand only]                  │
│  - Ayam Goreng Crispy                                     │
│  - Chicken Wings                                          │
│  - Paket Sumo Combo                                       │
│                                                            │
│  ❌ Cannot see products from NASI PADANG or SOTO         │
│                                                            │
└───────────────────────────────────────────────────────────┘
```

## 🔄 Data Flow & Business Logic

### 1. Setup Flow

```
1. Setup Edge Server
   ├─ Select Company from HO (YOGYA GROUP)
   ├─ Enter Store info (YOGYA SUNDA)
   └─ Select Brands (☑ SUMO, ☑ PADANG, ☑ SOTO)

2. Backend Process:
   ├─ Sync Company from HO → Save to Edge DB
   ├─ Sync selected Brands from HO → Save to Edge DB
   ├─ Create Store record (1 row only!)
   └─ Create StoreBrand records (many rows)

3. Result:
   ├─ 1 Company in Edge DB
   ├─ 3 Brands in Edge DB
   ├─ 1 Store in Edge DB
   └─ 3 StoreBrand relationships
```

### 2. Terminal Registration Flow

```
1. Register Terminal
   ├─ Store: Auto-filled (YOGYA SUNDA)
   ├─ Select Brand: User chooses (e.g., CHICKEN SUMO)
   └─ Enter Terminal Code (T01-SUMO)

2. Backend Process:
   ├─ Validate Brand exists in StoreBrand
   ├─ Create Terminal record with Store + Brand
   └─ Terminal now dedicated to CHICKEN SUMO

3. Result:
   Terminal T01-SUMO can only sell CHICKEN SUMO products
```

### 3. POS Session Flow

```
1. User Login at Terminal T01-SUMO
   ├─ System reads Terminal.brand → CHICKEN SUMO
   ├─ Load Products where brand_id = CHICKEN SUMO
   └─ Load Categories where brand_id = CHICKEN SUMO

2. Create Bill
   ├─ Bill.store = YOGYA SUNDA
   ├─ Bill.brand = CHICKEN SUMO (from Terminal)
   ├─ Bill.terminal = T01-SUMO
   └─ Bill.company = YOGYA GROUP (from Store)

3. Reporting
   ├─ Sales by Store: YOGYA SUNDA total
   ├─ Sales by Brand: CHICKEN SUMO detail
   └─ Sales by Company: YOGYA GROUP aggregate
```

## 🔒 Constraints & Validation

### 1. Store Constraint
```python
# Only 1 Store per Edge Server
def setup_store_config(request):
    if Store.objects.exists():
        raise ValidationError("Edge Server already has a store configured")
```

### 2. Brand Constraint
```python
# Terminal can only be assigned to brands in StoreBrand
def register_terminal(request):
    store = Store.objects.get()  # Single store
    brand_id = request.POST.get('brand_id')
    
    # Validate brand is assigned to this store
    if not StoreBrand.objects.filter(store=store, brand_id=brand_id, is_active=True).exists():
        raise ValidationError("Brand not available in this store")
```

### 3. Product Filter
```python
# POS only shows products for terminal's brand
def get_products(terminal):
    return Product.objects.filter(brand=terminal.brand, is_active=True)
```

## 📋 Migration Plan

### Step 1: Update Models

```python
# apps/core/models.py

class Store(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)  # Changed
    store_code = models.CharField(max_length=20, unique=True)
    store_name = models.CharField(max_length=200)
    # Remove brand field!

class StoreBrand(models.Model):  # New model
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = [['store', 'brand']]

class Terminal(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)  # New field!
    terminal_code = models.CharField(max_length=20, unique=True)
```

### Step 2: Create Migration

```python
# Generated migration file
class Migration(migrations.Migration):
    operations = [
        # 1. Add company field to Store
        migrations.AddField(
            model_name='store',
            name='company',
            field=models.ForeignKey('Company', on_delete=models.CASCADE),
        ),
        
        # 2. Create StoreBrand model
        migrations.CreateModel(
            name='StoreBrand',
            fields=[
                ('id', models.UUIDField(primary_key=True)),
                ('store', models.ForeignKey('Store', on_delete=models.CASCADE)),
                ('brand', models.ForeignKey('Brand', on_delete=models.CASCADE)),
                ('is_active', models.BooleanField(default=True)),
            ],
        ),
        
        # 3. Migrate existing data: Store.brand → StoreBrand
        migrations.RunPython(migrate_store_brands),
        
        # 4. Add brand field to Terminal
        migrations.AddField(
            model_name='terminal',
            name='brand',
            field=models.ForeignKey('Brand', on_delete=models.CASCADE),
        ),
        
        # 5. Remove brand field from Store
        migrations.RemoveField(
            model_name='store',
            name='brand',
        ),
    ]

def migrate_store_brands(apps, schema_editor):
    Store = apps.get_model('core', 'Store')
    StoreBrand = apps.get_model('core', 'StoreBrand')
    
    for store in Store.objects.all():
        if store.brand:
            StoreBrand.objects.create(
                store=store,
                brand=store.brand,
                is_active=True
            )
```

### Step 3: Update Views

```python
# apps/core/views_setup.py

@csrf_exempt
def setup_store_config(request):
    """Configure Edge Server: 1 Company + 1 Store + Multiple Brands"""
    
    if Store.objects.exists():
        messages.warning(request, 'Store already configured')
        return redirect('core:setup_wizard')
    
    if request.method == 'POST':
        company_id = request.POST.get('company_id')
        store_code = request.POST.get('store_code')
        store_name = request.POST.get('store_name')
        brand_ids = request.POST.getlist('brand_ids[]')  # Multiple brands!
        
        # Sync company from HO
        company = sync_company_from_ho(company_id)
        
        # Create store (1 only!)
        store = Store.objects.create(
            company=company,
            store_code=store_code,
            store_name=store_name
        )
        
        # Sync brands and link to store
        for brand_id in brand_ids:
            brand = sync_brand_from_ho(brand_id)
            StoreBrand.objects.create(
                store=store,
                brand=brand,
                is_active=True
            )
        
        messages.success(request, f'Store configured with {len(brand_ids)} brands')
        return redirect('core:setup_wizard')
```

### Step 4: Update Terminal Registration

```python
# apps/core/views_terminal.py

def terminal_setup(request):
    store = Store.objects.first()  # Single store
    
    if request.method == 'POST':
        brand_id = request.POST.get('brand_id')
        terminal_code = request.POST.get('terminal_code')
        
        # Validate brand is in this store
        if not StoreBrand.objects.filter(
            store=store, 
            brand_id=brand_id, 
            is_active=True
        ).exists():
            messages.error(request, 'Brand not available in this store')
            return redirect('core:terminal_setup')
        
        # Create terminal with brand
        Terminal.objects.create(
            store=store,
            brand_id=brand_id,
            terminal_code=terminal_code,
            terminal_name=f"Terminal {terminal_code}"
        )
        
        messages.success(request, 'Terminal registered successfully')
        return redirect('core:terminal_setup')
    
    # Get available brands for this store
    available_brands = Brand.objects.filter(
        brand_stores__store=store,
        brand_stores__is_active=True
    )
    
    return render(request, 'core/terminal_setup.html', {
        'store': store,
        'available_brands': available_brands
    })
```

### Step 5: Update POS Views

```python
# apps/pos/views.py

def pos_main(request):
    terminal = get_current_terminal(request)
    
    # Filter products by terminal's brand
    products = Product.objects.filter(
        brand=terminal.brand,
        is_active=True
    )
    
    # Filter categories by terminal's brand
    categories = Category.objects.filter(
        brand=terminal.brand,
        is_active=True
    )
    
    return render(request, 'pos/main.html', {
        'terminal': terminal,
        'store': terminal.store,
        'brand': terminal.brand,
        'products': products,
        'categories': categories
    })
```

## ✅ Benefits of This Architecture

### 1. **Clear Hierarchy**
```
Company (1) → Store (1) → Brands (Many) → Terminals (Many)
```

### 2. **Data Segregation**
- Each brand has its own products
- Each brand has its own categories
- Each brand has its own sales data

### 3. **Flexible Management**
- Easy to add new brands to store
- Easy to deactivate brands
- Terminal dedicated to specific brand

### 4. **Accurate Reporting**
- Sales by Company (aggregate all brands)
- Sales by Store (single store)
- Sales by Brand (per brand detail)
- Sales by Terminal (per terminal detail)

## 🚨 Important Constraints

### 1. **One Store Per Edge Server**
```python
# Enforce in setup view
if Store.objects.exists():
    raise ValidationError("Store already configured")
```

### 2. **Terminal Must Belong to Store's Brands**
```python
# Validate in terminal registration
if not store.store_brands.filter(brand_id=brand_id).exists():
    raise ValidationError("Brand not in this store")
```

### 3. **Products Filtered by Terminal's Brand**
```python
# In POS view
products = Product.objects.filter(brand=terminal.brand)
```

## 📊 Query Examples

### Get all brands in a store
```python
store = Store.objects.first()
brands = Brand.objects.filter(
    brand_stores__store=store,
    brand_stores__is_active=True
)
```

### Get all terminals for a brand in store
```python
terminals = Terminal.objects.filter(
    store=store,
    brand=brand
)
```

### Get sales by brand
```python
brand_sales = Bill.objects.filter(
    brand=brand,
    store=store
).aggregate(total=Sum('total_amount'))
```

### Get sales by store (all brands)
```python
store_sales = Bill.objects.filter(
    store=store
).values('brand__name').annotate(
    total=Sum('total_amount')
)
```

## 🎯 Conclusion

**Architecture Summary:**
- ✅ 1 Edge Server = 1 Company + 1 Store (unique constraint)
- ✅ Multiple Brands per Store (many-to-many via StoreBrand)
- ✅ Each Terminal dedicated to 1 Brand
- ✅ Products filtered by Terminal's Brand
- ✅ Clear hierarchy and data segregation

**This architecture perfectly fits your food court use case!** 🎉

---

**Next Steps:**
1. Create migration for new schema
2. Update setup UI for brand selection
3. Update terminal registration for brand assignment
4. Update POS to filter by terminal's brand
5. Test with sample data
