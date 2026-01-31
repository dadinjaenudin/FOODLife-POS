# Multi-Brand Edge Server - Architecture Proposal

## 📋 Use Case

**Scenario:** Satu Edge Server melayani multiple brands dalam satu lokasi fisik (misalnya mall atau food court).

**Example:**
- **Company:** YOGYA GROUP (single)
- **Brands:** YOGYA, YOMART, GRIYA (multiple)
- **Stores:** Multiple stores per brand

## 🏗️ Architecture Options

### Option 1: Multi-Store Model (RECOMMENDED)

**Database Schema:**
```
Company (1)
  └─ Brand (Many)
      └─ Store (Many)
          └─ Terminal (Many)
```

**Current Model Already Supports This!**

Existing schema:
```python
class Company:
    code, name, timezone

class Brand:
    company = ForeignKey(Company)
    code, name

class Store:
    brand = ForeignKey(Brand)  # <-- Current: 1 Store = 1 Brand
    store_code, store_name

class Terminal:
    store = ForeignKey(Store)
    terminal_code
```

**Proposal: Keep current schema but allow multiple Store records**

Edge Server dapat punya multiple Store configs:
- Store 1: Brand=YOGYA, Code=YGY-001
- Store 2: Brand=YOMART, Code=YOM-001
- Store 3: Brand=GRIYA, Code=GRY-001

### Option 2: Store-Brand Many-to-Many (Alternative)

**Change Schema:**
```python
class Store:
    company = ForeignKey(Company)  # Direct link to company
    brands = ManyToManyField(Brand)  # Multiple brands
    store_code, store_name
```

**Not Recommended** because:
- Breaks existing architecture
- Complicates reporting (which brand sold what?)
- Inventory management becomes complex

## ✅ Recommended Solution: Option 1 (Multi-Store)

### Implementation Plan

#### 1. Change `Store` Model - Remove Unique Constraint

**Current:**
```python
class Store(models.Model):
    brand = models.OneToOneField(Brand)  # Only 1 store per brand
    store_code = models.CharField(max_length=20, unique=True)
```

**Proposed:**
```python
class Store(models.Model):
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)  # Multiple stores per brand
    store_code = models.CharField(max_length=20, unique=True)
    is_primary = models.BooleanField(default=False)  # Mark primary store for Edge Server
    
    class Meta:
        unique_together = [['brand', 'store_code']]  # Unique per brand
```

#### 2. Update Setup Page - Allow Multiple Stores

**UI Changes:**

```
Setup Edge Server
┌─────────────────────────────────────────────┐
│ Company: YOGYA GROUP (auto-select)         │
│                                              │
│ Stores Configuration:                       │
│                                              │
│ ┌─ Store 1 ────────────────────────────┐   │
│ │ Brand: [YOGYA ▼]                      │   │
│ │ Store: [YOGYA Malioboro ▼]            │   │
│ │ Code: YGY-MLI                          │   │
│ │ [✓] Primary Store                      │   │
│ └───────────────────────────────────────┘   │
│                                              │
│ ┌─ Store 2 ────────────────────────────┐   │
│ │ Brand: [YOMART ▼]                     │   │
│ │ Store: [YOMART Plaza ▼]               │   │
│ │ Code: YOM-PLZ                          │   │
│ │ [ ] Primary Store                      │   │
│ └───────────────────────────────────────┘   │
│                                              │
│ [+ Add Another Store]                       │
│                                              │
│ [💾 Save Configuration]                     │
└─────────────────────────────────────────────┘
```

#### 3. Terminal Setup - Select Store

**When registering terminal:**

```
Register Terminal
┌─────────────────────────────────────────────┐
│ Store: [Select Store ▼]                    │
│        - YOGYA Malioboro (YGY-MLI)         │
│        - YOMART Plaza (YOM-PLZ)            │
│        - GRIYA Premium (GRY-PRM)           │
│                                              │
│ Terminal Code: [Terminal-01]               │
│                                              │
│ [Register Terminal]                         │
└─────────────────────────────────────────────┘
```

#### 4. POS - Store/Brand Selection

**Login/Session Flow:**

```
User Login → Select Store → Start Session
```

**In POS Interface:**

```
┌─────────────────────────────────────────────┐
│ Current Store: YOGYA Malioboro             │
│ [Switch Store ▼]                           │
│   - YOGYA Malioboro                        │
│   - YOMART Plaza                           │
│   - GRIYA Premium                          │
└─────────────────────────────────────────────┘
```

## 🔄 Migration Strategy

### Step 1: Update Models

```python
# Migration to change OneToOneField to ForeignKey
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0004_previous_migration'),
    ]

    operations = [
        # Remove OneToOne constraint
        migrations.AlterField(
            model_name='store',
            name='brand',
            field=models.ForeignKey(
                'Brand',
                on_delete=models.CASCADE,
                related_name='stores'
            ),
        ),
        
        # Add is_primary flag
        migrations.AddField(
            model_name='store',
            name='is_primary',
            field=models.BooleanField(default=False),
        ),
        
        # Add unique constraint
        migrations.AlterUniqueTogether(
            name='store',
            unique_together={('brand', 'store_code')},
        ),
    ]
```

### Step 2: Update Setup Views

**Allow adding multiple stores:**

```python
@csrf_exempt
def setup_store_config(request):
    """Configure Edge Server store(s)"""
    
    if request.method == 'POST':
        stores_data = request.POST.getlist('stores[]')  # Array of stores
        
        for store_data in stores_data:
            company_id = store_data.get('company_id')
            brand_id = store_data.get('brand_id')
            store_code = store_data.get('store_code')
            is_primary = store_data.get('is_primary', False)
            
            # Sync company and brand from HO
            company = sync_company_from_ho(company_id)
            brand = sync_brand_from_ho(brand_id)
            
            # Create store
            Store.objects.create(
                brand=brand,
                store_code=store_code,
                store_name=store_name,
                is_primary=is_primary
            )
```

### Step 3: Update Session Management

**Store selection in session:**

```python
class StoreSession(models.Model):
    user = models.ForeignKey(User)
    store = models.ForeignKey(Store)  # <-- Select from available stores
    terminal = models.ForeignKey(Terminal)
    opened_at = models.DateTimeField()
```

### Step 4: Update POS Views

**Filter by current store:**

```python
def pos_main(request):
    current_store = request.session.get('current_store')
    
    # Get products for current store's brand
    products = Product.objects.filter(brand=current_store.brand)
    
    # Get categories for current brand
    categories = Category.objects.filter(brand=current_store.brand)
```

## 📊 Database Relationships

```sql
-- Company (1 per Edge Server)
company_id | code  | name
-----------|-------|-------------
uuid-1     | YOGYA | YOGYA GROUP

-- Brands (Multiple per Company)
brand_id | company_id | code   | name
---------|------------|--------|--------
uuid-2   | uuid-1     | YOGYA  | YOGYA
uuid-3   | uuid-1     | YOMART | YOMART
uuid-4   | uuid-1     | GRIYA  | GRIYA

-- Stores (Multiple per Brand, Multiple per Edge Server)
store_id | brand_id | store_code | store_name       | is_primary
---------|----------|------------|------------------|------------
uuid-5   | uuid-2   | YGY-MLI    | YOGYA Malioboro  | true
uuid-6   | uuid-3   | YOM-PLZ    | YOMART Plaza     | false
uuid-7   | uuid-4   | GRY-PRM    | GRIYA Premium    | false

-- Terminals (Multiple per Store)
terminal_id | store_id | terminal_code
------------|----------|---------------
uuid-8      | uuid-5   | YGY-MLI-T01
uuid-9      | uuid-6   | YOM-PLZ-T01
uuid-10     | uuid-7   | GRY-PRM-T01
```

## 🎯 Benefits

### 1. **Operational Efficiency**
   - 1 Edge Server untuk multiple brands dalam 1 lokasi fisik
   - Shared infrastructure (1 server, 1 database)
   - Centralized management

### 2. **Data Segregation**
   - Setiap brand tetap punya data terpisah
   - Reporting per brand tetap akurat
   - Inventory per brand tetap independent

### 3. **Flexibility**
   - Easy to add new brands
   - Easy to add new stores per brand
   - Terminal bisa di-assign ke store mana saja

### 4. **Cost Efficiency**
   - Tidak perlu multiple Edge Servers untuk multiple brands
   - 1 hardware untuk banyak brands

## 🚨 Important Considerations

### 1. **Inventory Management**
- Setiap brand punya inventory sendiri
- Stock terpisah per brand
- Transfer antar brand perlu approval

### 2. **Reporting**
- Report harus filter by store/brand
- Company-level aggregate reports
- Brand-level detail reports

### 3. **Session Management**
- User login → Select store → Work in selected store
- Switch store = end session, start new session
- Transaction always linked to specific store

### 4. **Sync Strategy**
- Sync master data (products, categories) per brand
- Don't mix inventory between brands
- Transaction sync include store identifier

## 📝 Implementation Checklist

### Phase 1: Database Schema
- [ ] Update Store model (OneToOne → ForeignKey)
- [ ] Add is_primary field
- [ ] Create migration
- [ ] Test migration on dev database

### Phase 2: Setup UI
- [ ] Update setup page to allow multiple stores
- [ ] Add "Add Store" button
- [ ] Company selection (single, fixed after first setup)
- [ ] Multiple brand/store selection

### Phase 3: Terminal Management
- [ ] Add store selection in terminal registration
- [ ] Update terminal list to show store

### Phase 4: POS Changes
- [ ] Add store selector in session start
- [ ] Filter products by current store's brand
- [ ] Update bill to include store reference

### Phase 5: Reporting
- [ ] Add store filter in reports
- [ ] Aggregate by brand
- [ ] Company-level summary

### Phase 6: Sync Updates
- [ ] Include store_id in transaction sync
- [ ] Sync multiple stores' data from HO
- [ ] Handle brand-specific master data

## 🎬 Next Steps

**Recommendation:**

1. **For MVP/Phase 1:** Keep current single-store model
   - Simplest to implement
   - Works for single-brand stores
   - Can migrate later

2. **For Phase 2:** Implement multi-store model
   - After MVP proven working
   - When customer requests multi-brand support
   - Use migration strategy above

**Current Status:**
- ✅ Single store works perfectly
- ✅ Can be extended to multi-store later
- ✅ Database schema flexible enough

**When to Implement Multi-Store:**
- When you have actual customer needing multi-brand
- When MVP is stable and tested
- When you have time for proper testing

## 💡 Alternative: Multiple Edge Servers

If brands are truly separate businesses:

```
Physical Location: Mall Food Court
├─ Edge Server 1 → YOGYA Brand only
├─ Edge Server 2 → YOMART Brand only
└─ Edge Server 3 → GRIYA Brand only
```

**Pros:**
- Complete data isolation
- Simple architecture
- No code changes needed

**Cons:**
- More hardware costs
- More maintenance
- Redundant infrastructure

## 🎯 Final Recommendation

**Start with current single-store model**, then upgrade to multi-store when needed:

1. **Current:** 1 Edge = 1 Company = 1 Brand = 1 Store ✅
2. **Future:** 1 Edge = 1 Company = Multiple Brands = Multiple Stores

Schema already supports it, just need UI and business logic updates.

---

**Decision:** Keep it simple for now, extend when customer needs it! 🚀
