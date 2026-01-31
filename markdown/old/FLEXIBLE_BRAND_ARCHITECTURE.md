# Flexible Multi-Brand Architecture
## Support untuk Single Brand dan Multiple Brands

## 🎯 Use Cases yang Didukung

### Case 1: Food Court - Multiple Brands
```
Store: YOGYA SUNDA FOOD COURT
├─ Brand: CHICKEN SUMO (3 terminals)
├─ Brand: NASI PADANG (2 terminals)
└─ Brand: SOTO LAMONGAN (1 terminal)

Total: 3 brands, 6 terminals
```

### Case 2: Single Restaurant - 1 Brand Only
```
Store: YOGYA MALIOBORO
└─ Brand: YOGYA RESTAURANT (5 terminals)

Total: 1 brand, 5 terminals
```

### Case 3: Hybrid - Main Brand + Sub Brands
```
Store: YOGYA SUDIRMAN
├─ Brand: YOGYA RESTAURANT (main)
└─ Brand: YOGYA BAKERY (side)

Total: 2 brands, multiple terminals
```

## ✅ Architecture Supports All Cases

### Schema (Same for All Cases!)

```python
class Store(models.Model):
    company = ForeignKey(Company)
    store_code = CharField(unique=True)
    store_name = CharField()

class StoreBrand(models.Model):
    store = ForeignKey(Store)
    brand = ForeignKey(Brand)
    is_active = BooleanField(default=True)
    
    class Meta:
        unique_together = [['store', 'brand']]

class Terminal(models.Model):
    store = ForeignKey(Store)
    brand = ForeignKey(Brand)
    terminal_code = CharField(unique=True)
```

**The beauty:** Same schema works for 1 brand or 100 brands! 🎉

## 📊 Database Examples

### Example 1: Food Court (Multiple Brands)

**Stores:**
```sql
store_id | company_id | store_code | store_name
---------|------------|------------|------------------
uuid-1   | YOGYA      | YGY-SND    | YOGYA SUNDA FC
```

**StoreBrand:**
```sql
store_id | brand_id      | is_active
---------|---------------|----------
uuid-1   | CHICKEN_SUMO  | true
uuid-1   | NASI_PADANG   | true
uuid-1   | SOTO_LAMONGAN | true
```

**Terminals:**
```sql
terminal_id | store_id | brand_id      | terminal_code
------------|----------|---------------|---------------
term-1      | uuid-1   | CHICKEN_SUMO  | T01-SUMO
term-2      | uuid-1   | CHICKEN_SUMO  | T02-SUMO
term-3      | uuid-1   | NASI_PADANG   | T03-PADANG
term-4      | uuid-1   | SOTO_LAMONGAN | T04-SOTO
```

### Example 2: Single Restaurant (1 Brand)

**Stores:**
```sql
store_id | company_id | store_code | store_name
---------|------------|------------|------------------
uuid-2   | YOGYA      | YGY-MLI    | YOGYA MALIOBORO
```

**StoreBrand:**
```sql
store_id | brand_id    | is_active
---------|-------------|----------
uuid-2   | YOGYA_REST  | true      ← Only 1 brand!
```

**Terminals:**
```sql
terminal_id | store_id | brand_id   | terminal_code
------------|----------|------------|---------------
term-5      | uuid-2   | YOGYA_REST | T01-MLI
term-6      | uuid-2   | YOGYA_REST | T02-MLI
term-7      | uuid-2   | YOGYA_REST | T03-MLI
term-8      | uuid-2   | YOGYA_REST | T04-MLI
term-9      | uuid-2   | YOGYA_REST | T05-MLI
```

**All terminals point to same brand - perfectly valid!** ✅

## 🎨 UI Flexibility

### Setup UI - Detects Number of Brands

```html
<!-- Setup Page adapts to single or multiple brands -->

<form method="post" action="/setup/store/">
    <!-- Company (always required) -->
    <div>
        <label>Company *</label>
        <select name="company_id">
            <option value="uuid-yogya">YOGYA GROUP</option>
        </select>
    </div>
    
    <!-- Store (always required) -->
    <div>
        <label>Store Code *</label>
        <input name="store_code" value="YGY-MLI">
    </div>
    
    <div>
        <label>Store Name *</label>
        <input name="store_name" value="YOGYA MALIOBORO">
    </div>
    
    <!-- Brands (flexible: select 1 or many) -->
    <div>
        <label>Brands in This Store *</label>
        <p class="help-text">
            Select all brands available in this store. 
            For single-brand stores, select only one.
        </p>
        
        <div class="brand-checkboxes">
            <label>
                <input type="checkbox" name="brand_ids[]" value="uuid-yogya-rest">
                ☑ YOGYA RESTAURANT
            </label>
            
            <label>
                <input type="checkbox" name="brand_ids[]" value="uuid-yogya-bakery">
                ☐ YOGYA BAKERY
            </label>
            
            <label>
                <input type="checkbox" name="brand_ids[]" value="uuid-chicken-sumo">
                ☐ CHICKEN SUMO
            </label>
            
            <label>
                <input type="checkbox" name="brand_ids[]" value="uuid-nasi-padang">
                ☐ NASI PADANG
            </label>
        </div>
    </div>
    
    <button type="submit">💾 Save Configuration</button>
</form>
```

### Terminal Registration - Shows Available Brands

```html
<!-- For Single Brand Store -->
<form>
    <div>
        <label>Store</label>
        <input value="YOGYA MALIOBORO" readonly>
    </div>
    
    <div>
        <label>Brand</label>
        <select name="brand_id">
            <option value="uuid-yogya-rest">YOGYA RESTAURANT</option>
            <!-- Only 1 option! -->
        </select>
    </div>
    
    <div>
        <label>Terminal Code</label>
        <input name="terminal_code" value="T01-MLI">
    </div>
    
    <button>Register Terminal</button>
</form>

<!-- For Multi-Brand Store (Food Court) -->
<form>
    <div>
        <label>Store</label>
        <input value="YOGYA SUNDA FC" readonly>
    </div>
    
    <div>
        <label>Brand *</label>
        <select name="brand_id" required>
            <option value="">-- Select Brand --</option>
            <option value="uuid-chicken-sumo">CHICKEN SUMO</option>
            <option value="uuid-nasi-padang">NASI PADANG</option>
            <option value="uuid-soto-lamongan">SOTO LAMONGAN</option>
            <!-- Multiple options! -->
        </select>
    </div>
    
    <div>
        <label>Terminal Code</label>
        <input name="terminal_code" value="T01-SUMO">
    </div>
    
    <button>Register Terminal</button>
</form>
```

## 🔧 Backend Logic - Auto-Adapts

### Setup View - Accepts 1 or Many Brands

```python
@csrf_exempt
def setup_store_config(request):
    """Works for single or multiple brands"""
    
    if request.method == 'POST':
        company_id = request.POST.get('company_id')
        store_code = request.POST.get('store_code')
        store_name = request.POST.get('store_name')
        brand_ids = request.POST.getlist('brand_ids[]')  # Can be 1 or many!
        
        # Validation
        if not brand_ids:
            messages.error(request, 'Please select at least 1 brand')
            return redirect('core:setup_wizard')
        
        # Sync company
        company = sync_company_from_ho(company_id)
        
        # Create store
        store = Store.objects.create(
            company=company,
            store_code=store_code,
            store_name=store_name
        )
        
        # Link brands to store (1 or many, same code!)
        for brand_id in brand_ids:
            brand = sync_brand_from_ho(brand_id)
            StoreBrand.objects.create(
                store=store,
                brand=brand,
                is_active=True
            )
        
        # Success message adapts
        if len(brand_ids) == 1:
            messages.success(request, 
                f'✅ Store configured with 1 brand: {store_name}'
            )
        else:
            messages.success(request, 
                f'✅ Store configured with {len(brand_ids)} brands: {store_name}'
            )
        
        return redirect('core:setup_wizard')
```

### Terminal Registration - Gets Available Brands

```python
def terminal_setup(request):
    """Shows brands available in this store (1 or many)"""
    
    store = Store.objects.first()
    
    if request.method == 'POST':
        brand_id = request.POST.get('brand_id')
        terminal_code = request.POST.get('terminal_code')
        
        # Validate brand is in store
        if not StoreBrand.objects.filter(
            store=store, 
            brand_id=brand_id, 
            is_active=True
        ).exists():
            messages.error(request, 'Brand not available in this store')
            return redirect('core:terminal_setup')
        
        # Create terminal
        Terminal.objects.create(
            store=store,
            brand_id=brand_id,
            terminal_code=terminal_code
        )
        
        messages.success(request, 'Terminal registered')
        return redirect('core:terminal_setup')
    
    # Get available brands (can be 1 or many!)
    available_brands = Brand.objects.filter(
        brand_stores__store=store,
        brand_stores__is_active=True
    )
    
    return render(request, 'core/terminal_setup.html', {
        'store': store,
        'available_brands': available_brands,
        'is_single_brand': available_brands.count() == 1
    })
```

### POS View - Always Filters by Terminal's Brand

```python
def pos_main(request):
    """Works the same for single or multi-brand stores"""
    
    terminal = get_current_terminal(request)
    
    # Always filter by terminal's brand
    # Works whether store has 1 brand or 10 brands!
    products = Product.objects.filter(
        brand=terminal.brand,
        is_active=True
    )
    
    categories = Category.objects.filter(
        brand=terminal.brand,
        is_active=True
    )
    
    return render(request, 'pos/main.html', {
        'terminal': terminal,
        'brand': terminal.brand,  # Clear which brand
        'products': products,
        'categories': categories
    })
```

## 📊 Reporting - Flexible Aggregation

### Single Brand Store Report
```python
# Store: YOGYA MALIOBORO (1 brand)
store = Store.objects.get(store_code='YGY-MLI')

# All sales = sales of that single brand
store_sales = Bill.objects.filter(store=store).aggregate(
    total=Sum('total_amount')
)
# Result: Total sales for YOGYA RESTAURANT brand
```

### Multi-Brand Store Report
```python
# Store: YOGYA SUNDA FC (3 brands)
store = Store.objects.get(store_code='YGY-SND')

# Aggregate by brand
brand_sales = Bill.objects.filter(store=store).values(
    'brand__name'
).annotate(
    total=Sum('total_amount')
)

# Result:
# [
#   {'brand__name': 'CHICKEN SUMO', 'total': 5000000},
#   {'brand__name': 'NASI PADANG', 'total': 3000000},
#   {'brand__name': 'SOTO LAMONGAN', 'total': 2000000}
# ]

# Store total
store_total = Bill.objects.filter(store=store).aggregate(
    total=Sum('total_amount')
)
# Result: 10000000 (sum of all brands)
```

## ✅ Advantages of This Flexible Design

### 1. **Same Code for All Scenarios**
- ✅ No special case for single-brand
- ✅ No special case for multi-brand
- ✅ One codebase handles everything

### 2. **Easy to Scale**
- Start with 1 brand → Add more brands later
- No schema changes needed
- No code changes needed

### 3. **Clear Data Model**
```python
# Check if store has multiple brands
store = Store.objects.first()
brand_count = store.store_brands.filter(is_active=True).count()

if brand_count == 1:
    print("Single brand store")
else:
    print(f"Multi-brand store with {brand_count} brands")
```

### 4. **Flexible UI**
```python
# Template can adapt
{% if available_brands.count == 1 %}
    <!-- Simpler UI for single brand -->
    <input type="hidden" name="brand_id" value="{{ available_brands.0.id }}">
    <p>Brand: {{ available_brands.0.name }}</p>
{% else %}
    <!-- Dropdown for multiple brands -->
    <select name="brand_id">
        {% for brand in available_brands %}
            <option value="{{ brand.id }}">{{ brand.name }}</option>
        {% endfor %}
    </select>
{% endif %}
```

### 5. **No Data Redundancy**
- StoreBrand table only has records for actual relationships
- Single brand store: 1 row in StoreBrand
- Multi brand store: N rows in StoreBrand
- Efficient and normalized

## 🎯 Real-World Examples

### Example A: Traditional Restaurant
```
Company: YOGYA GROUP
Store: YOGYA MALIOBORO
Brand: YOGYA RESTAURANT (single)
Terminals: T01-MLI, T02-MLI, T03-MLI, T04-MLI
Products: All from YOGYA RESTAURANT brand
```

### Example B: Food Court
```
Company: YOGYA GROUP
Store: YOGYA SUNDA FC
Brands: 
  - CHICKEN SUMO (terminals: T01-SUMO, T02-SUMO)
  - NASI PADANG (terminals: T03-PADANG)
  - SOTO LAMONGAN (terminals: T04-SOTO)
Products: Each terminal sees only their brand's products
```

### Example C: Restaurant + Bakery
```
Company: YOGYA GROUP
Store: YOGYA SUDIRMAN
Brands:
  - YOGYA RESTAURANT (terminals: T01-REST, T02-REST, T03-REST)
  - YOGYA BAKERY (terminals: T04-BAKERY)
Products: Restaurant terminals see restaurant menu, bakery sees bakery menu
```

### Example D: Franchise with Sub-Brands
```
Company: YOGYA GROUP
Store: YOGYA PREMIUM
Brands:
  - YOGYA PREMIUM DINING (fine dining)
  - YOGYA CAFE (casual)
  - YOGYA TAKEAWAY (grab-and-go)
Each brand has its own menu, pricing, and terminals
```

## 🔒 Validation Rules

### Setup Validation
```python
def validate_store_setup(company_id, store_code, brand_ids):
    """Validate setup works for 1 or many brands"""
    
    # Must have at least 1 brand
    if not brand_ids or len(brand_ids) == 0:
        raise ValidationError("Must select at least 1 brand")
    
    # All brands must belong to selected company
    brands = Brand.objects.filter(id__in=brand_ids)
    if brands.filter(company_id__ne=company_id).exists():
        raise ValidationError("All brands must belong to selected company")
    
    # Store code must be unique
    if Store.objects.filter(store_code=store_code).exists():
        raise ValidationError("Store code already exists")
    
    return True
```

### Terminal Registration Validation
```python
def validate_terminal_registration(store, brand_id, terminal_code):
    """Validate terminal registration (single or multi-brand)"""
    
    # Brand must be in store's brands
    if not StoreBrand.objects.filter(
        store=store, 
        brand_id=brand_id, 
        is_active=True
    ).exists():
        raise ValidationError(
            "Brand not available in this store. "
            "Available brands: " + 
            ", ".join(store.store_brands.values_list('brand__name', flat=True))
        )
    
    # Terminal code must be unique
    if Terminal.objects.filter(terminal_code=terminal_code).exists():
        raise ValidationError("Terminal code already exists")
    
    return True
```

## 💡 Best Practices

### 1. **Default to Single Brand**
- If not specified, assume single brand store
- Simpler for most use cases
- Can upgrade to multi-brand later

### 2. **Clear Brand Assignment**
- Terminal registration must explicitly choose brand
- No ambiguity about which brand terminal serves

### 3. **Graceful UI**
- If only 1 brand: auto-select, don't show dropdown
- If multiple brands: require selection

### 4. **Consistent Filtering**
- Always filter products by terminal.brand
- Never show products from other brands

### 5. **Clear Reporting**
- Always show brand breakdown
- Even for single-brand (shows consistency)

## 🎉 Conclusion

### ✅ Yes, This Architecture is Perfect for Both!

**Single Brand Store:**
- ✅ Works perfectly
- ✅ Just 1 row in StoreBrand table
- ✅ All terminals point to same brand
- ✅ Simple and clean

**Multi Brand Store:**
- ✅ Works perfectly
- ✅ Multiple rows in StoreBrand table
- ✅ Terminals assigned to different brands
- ✅ Full segregation

**The beauty: Same code, same schema, maximum flexibility!** 🚀

### Recommendation

**Implement this architecture because:**
1. ✅ Supports all use cases (single and multi-brand)
2. ✅ No special cases in code
3. ✅ Easy to scale from 1 to many brands
4. ✅ Clear data model and relationships
5. ✅ Future-proof and flexible

**You won't regret it!** 😊
