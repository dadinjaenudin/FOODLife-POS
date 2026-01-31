# HO Database Schema Analysis

## 📊 Current HO Schema

### Company Table
```sql
company (
    id uuid PRIMARY KEY,
    code varchar(20) UNIQUE NOT NULL,
    name varchar(200) NOT NULL,
    logo varchar(100),
    timezone varchar(50) NOT NULL,
    is_active boolean NOT NULL,
    point_expiry_months integer NOT NULL,
    points_per_currency numeric(10,2) NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
)
```

### Brand Table
```sql
brand (
    id uuid PRIMARY KEY,
    code varchar(20) NOT NULL,
    name varchar(200) NOT NULL,
    address text NOT NULL,
    phone varchar(20) NOT NULL,
    tax_id varchar(50) NOT NULL,
    tax_rate numeric(5,2) NOT NULL,
    service_charge numeric(5,2) NOT NULL,
    point_expiry_months_override integer NULL,
    is_active boolean NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    company_id uuid NOT NULL REFERENCES company(id),
    
    UNIQUE (company_id, code)
)
```

### Store Table ⚠️ IMPORTANT
```sql
store (
    id uuid PRIMARY KEY,
    store_code varchar(20) UNIQUE NOT NULL,
    store_name varchar(200) NOT NULL,
    address text NOT NULL,
    phone varchar(20) NOT NULL,
    timezone varchar(50) NOT NULL,
    latitude numeric(9,6) NULL,
    longitude numeric(9,6) NULL,
    is_active boolean NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    brand_id uuid NOT NULL REFERENCES brand(id)  ← ONE BRAND PER STORE!
)
```

## 🚨 Key Finding

### Current HO Model:
```
Company (1) → Brand (Many) → Store (Many)
```

**Store belongs to ONE brand only!**

This is DIFFERENT from our multi-brand food court discussion where:
```
Company (1) → Store (1) → Brands (Many)
```

## 🤔 Question for Decision

### Option A: Follow HO Schema (1 Store = 1 Brand)
```python
# Edge models match HO exactly
class Store(models.Model):
    brand = models.ForeignKey(Brand)  # One brand
    store_code = models.CharField(max_length=20, unique=True)
    store_name = models.CharField(max_length=200)
```

**Use Case:**
- Traditional restaurant: YOGYA MALIOBORO → YOGYA Brand
- Each physical location = 1 brand
- Food court needs separate stores per brand

**Example:**
```
Store: YOGYA SUNDA CHICKEN SUMO → Brand: CHICKEN SUMO
Store: YOGYA SUNDA NASI PADANG → Brand: NASI PADANG
Store: YOGYA SUNDA SOTO → Brand: SOTO LAMONGAN
```

### Option B: Modify for Multi-Brand (1 Store = Many Brands)
```python
# Edge models different from HO
class Store(models.Model):
    company = models.ForeignKey(Company)  # Direct to company
    store_code = models.CharField(max_length=20, unique=True)
    # No brand field

class StoreBrand(models.Model):
    store = models.ForeignKey(Store)
    brand = models.ForeignKey(Brand)
```

**Use Case:**
- Food court: YOGYA SUNDA → Multiple brands
- One physical location serves multiple brands
- Terminals assigned to different brands

**Example:**
```
Store: YOGYA SUNDA
├─ Brand: CHICKEN SUMO
├─ Brand: NASI PADANG
└─ Brand: SOTO LAMONGAN
```

## 🎯 Recommendation

### For MVP and Compatibility: **Follow HO Schema (Option A)**

**Reasons:**
1. ✅ 100% compatible with HO
2. ✅ Sync APIs work out of the box
3. ✅ No schema mismatch
4. ✅ Simpler to implement
5. ✅ Can migrate to multi-brand later if needed

### Implementation for Food Court:

If using Option A, food court dengan 3 brands needs:
```
3 Store records in HO:
- Store: YGY-SND-SUMO, Brand: CHICKEN SUMO
- Store: YGY-SND-PADANG, Brand: NASI PADANG
- Store: YGY-SND-SOTO, Brand: SOTO LAMONGAN

Edge Server setup:
- User selects one store (e.g., YGY-SND-SUMO)
- Edge Server serves CHICKEN SUMO brand only
- Other brands need separate Edge Servers OR
- Multi-terminal setup with different stores
```

## 📋 Next Steps Based on Decision

### If following HO Schema (Option A):

1. Keep Store model with `brand_id`
2. Setup asks: Company + Store (store already has brand)
3. Sync single brand's data
4. Simple and compatible

### If modifying for multi-brand (Option B):

1. Change Store model to have `company_id` instead of `brand_id`
2. Add StoreBrand many-to-many table
3. Sync requires custom logic (HO store → Edge store with multiple brands)
4. More complex but flexible

## ❓ Question for User

**Which approach do you prefer?**

A. Follow HO schema (1 Store = 1 Brand) - Simpler, compatible
B. Modify for multi-brand (1 Store = Many Brands) - More flexible, requires changes

**This decision affects:**
- Setup flow
- Database migrations
- Sync API logic
- Terminal assignment
- User access control
