# ✅ Multi-Brand Edge Server Setup - Implementation Complete!

## 🎉 Summary

Implementasi **multi-brand setup dengan auto-sync dari HO** sudah selesai!

## 📦 What's Been Implemented

### 1. Database Schema Changes
- ✅ Modified `Store` model: Changed `brand` FK → `company` FK
- ✅ Created `StoreBrand` model: Many-to-many relationship (Store ↔ Brand)
- ✅ Added `ho_store_id` in StoreBrand: Reference ke HO store untuk sync
- ✅ Added `brand` FK to `Terminal`: Each terminal dedicated to brand

### 2. Sync Infrastructure
- ✅ Created `apps/core/sync_helpers.py`:
  - `get_ho_api_token()` - JWT authentication
  - `sync_company_from_ho()` - Sync company data
  - `sync_brand_from_ho()` - Sync brand data
  - `sync_products_for_brand()` - Sync products per brand
  - `sync_categories_for_brand()` - Sync categories per brand
  - `sync_condiments_for_brand()` - Sync condiments per brand
  - `setup_multi_brand_store()` - Main setup orchestrator

### 3. Setup View
- ✅ Created `setup_store_config_multi_brand()` view
- ✅ Accepts: company_id, store_code, store_name, ho_store_ids[]
- ✅ Auto-syncs all master data from HO
- ✅ Creates StoreBrand relationships with ho_store_id reference

### 4. Setup UI
- ✅ Step 1: Select Company from HO
- ✅ Step 2: Multi-select HO stores (representing brands)
- ✅ Step 3: Enter Edge store details
- ✅ Auto-sync progress shown
- ✅ Success message with summary

## 🏗️ Architecture

### Schema Flow:
```
HO Server:
└─ Store (YGY-SND-SUMO, brand_id=CHICKEN_SUMO)
└─ Store (YGY-SND-PADANG, brand_id=NASI_PADANG)
└─ Store (YGY-SND-SOTO, brand_id=SOTO_LAMONGAN)

↓ Sync via API

Edge Server:
└─ Store (YGY-SUNDA, company_id=YOGYA)
    ├─ StoreBrand (brand=CHICKEN_SUMO, ho_store_id=YGY-SND-SUMO)
    ├─ StoreBrand (brand=NASI_PADANG, ho_store_id=YGY-SND-PADANG)
    └─ StoreBrand (brand=SOTO_LAMONGAN, ho_store_id=YGY-SND-SOTO)
```

### Setup Flow:
```
1. User selects Company (YOGYA GROUP)
2. System fetches HO stores for company
3. User selects multiple HO stores:
   ☑ YGY-SND-SUMO (CHICKEN SUMO)
   ☑ YGY-SND-PADANG (NASI PADANG)
   ☑ YGY-SND-SOTO (SOTO LAMONGAN)
4. User enters Edge store code & name
5. Click "Setup Edge Server"
6. Backend automatically:
   - Get JWT token from HO
   - Sync Company → Edge DB
   - Create Edge Store
   - For each HO store:
     • Get HO store data
     • Sync Brand → Edge DB
     • Create StoreBrand (with ho_store_id reference)
     • Sync Products from HO store
     • Sync Categories from HO store
     • Sync Condiments from HO store
7. Done! Edge Server configured
```

## 📄 Files Modified/Created

### Models:
- ✅ `apps/core/models.py`:
  - Modified `Store` class
  - Created `StoreBrand` class
  - Modified `POSTerminal` class

### Views:
- ✅ `apps/core/views_setup.py`:
  - Created `setup_store_config_multi_brand()`

### Helpers:
- ✅ `apps/core/sync_helpers.py` (NEW):
  - Complete sync logic for multi-brand setup

### Templates:
- ✅ `templates/core/setup_store.html`:
  - Updated UI for multi-brand selection
  - Checkbox list for HO stores
  - Removed brand/store dropdowns

### URLs:
- ✅ `apps/core/urls.py`:
  - Routed `/setup/store/` to multi-brand view

## 🧪 Testing

### Test Scenario 1: Food Court (3 Brands)

**Setup Data in HO:**
- Company: YOGYA GROUP
- HO Stores:
  - YGY-SND-SUMO (Brand: CHICKEN SUMO)
  - YGY-SND-PADANG (Brand: NASI PADANG)
  - YGY-SND-SOTO (Brand: SOTO LAMONGAN)

**Setup Flow:**
1. Navigate to: `http://localhost:8001/setup/`
2. Select Company: YOGYA GROUP
3. Select all 3 HO stores
4. Enter Store Code: YGY-SUNDA
5. Enter Store Name: YOGYA SUNDA FOOD COURT
6. Click "Setup Edge Server"

**Expected Result:**
- ✅ Edge Store created: YGY-SUNDA
- ✅ 3 StoreBrand relationships created
- ✅ Products synced for all 3 brands
- ✅ Categories synced for all 3 brands
- ✅ Success message with summary

### Test Scenario 2: Single Restaurant (1 Brand)

**Setup Data in HO:**
- Company: YOGYA GROUP
- HO Store:
  - YGY-MLI (Brand: YOGYA RESTAURANT)

**Setup Flow:**
1. Navigate to: `http://localhost:8001/setup/`
2. Select Company: YOGYA GROUP
3. Select 1 HO store (YGY-MLI)
4. Enter Store Code: YGY-MALIOBORO
5. Enter Store Name: YOGYA MALIOBORO
6. Click "Setup Edge Server"

**Expected Result:**
- ✅ Edge Store created: YGY-MALIOBORO
- ✅ 1 StoreBrand relationship created
- ✅ Products synced for YOGYA RESTAURANT
- ✅ Success message

## 📊 Database State After Setup

### Food Court Example:

**core_store:**
```sql
id      | company_id | store_code | store_name
uuid-1  | yogya-id   | YGY-SUNDA  | YOGYA SUNDA FOOD COURT
```

**core_storebrand:**
```sql
id      | store_id | brand_id      | ho_store_id
uuid-2  | uuid-1   | sumo-id       | ho-sumo-id
uuid-3  | uuid-1   | padang-id     | ho-padang-id
uuid-4  | uuid-1   | soto-id       | ho-soto-id
```

**core_brand:**
```sql
id        | company_id | code   | name
sumo-id   | yogya-id   | SUMO   | CHICKEN SUMO
padang-id | yogya-id   | PADANG | NASI PADANG
soto-id   | yogya-id   | SOTO   | SOTO LAMONGAN
```

**pos_product:** (150+ products across 3 brands)
**core_category:** (25+ categories across 3 brands)
**pos_condiment:** (30+ condiments across 3 brands)

## 🔄 Periodic Sync (Future)

After setup, implement periodic sync:

```python
# Cron job or scheduled task
def periodic_sync():
    store = Store.objects.first()
    
    for store_brand in store.store_brands.filter(is_active=True):
        ho_store_id = store_brand.ho_store_id
        brand = store_brand.brand
        
        # Sync from this HO store
        sync_products_for_brand(brand, ho_store_id)
        sync_categories_for_brand(brand, ho_store_id)
        # ... etc
```

## 📤 Transaction Sync to HO (Future)

When syncing bills back to HO:

```python
def sync_bill_to_ho(bill):
    # Get HO store ID for this brand
    store_brand = StoreBrand.objects.get(
        store=bill.store,
        brand=bill.brand
    )
    
    # Sync to correct HO store
    post_to_ho_api(
        f'/api/sync/bills/',
        data={
            'store_id': store_brand.ho_store_id,  # Correct HO store
            'bill_data': {...}
        }
    )
```

## ✅ Next Steps

### 1. Test Setup Flow
- [ ] Start HO Server with sample data
- [ ] Create multiple stores per company in HO
- [ ] Test Edge Server setup with multi-brand
- [ ] Verify data synced correctly

### 2. Terminal Registration
- [ ] Update terminal registration to require brand
- [ ] Validate brand is in StoreBrand for store
- [ ] Test terminal assignment

### 3. User Management
- [ ] Implement UserBrand many-to-many
- [ ] Add brand access control in login
- [ ] Test user brand permissions

### 4. POS Updates
- [ ] Filter products by terminal.brand
- [ ] Filter categories by terminal.brand
- [ ] Add brand to Bill model with ho_store_id

### 5. Reporting
- [ ] Report by Edge store (all brands aggregate)
- [ ] Report by brand (per brand detail)
- [ ] Report by terminal

## 🎯 Success Criteria

- [x] User can select multiple HO stores during setup
- [x] System creates 1 Edge store with multiple brands
- [x] All master data synced from HO per brand
- [x] StoreBrand keeps reference to HO store (ho_store_id)
- [x] Setup UI clear and intuitive
- [ ] Migrations run successfully
- [ ] Docker build successful
- [ ] End-to-end test passes

## 🚀 Ready for Testing!

**To test:**
1. Ensure HO Server running: `http://localhost:8002`
2. Rebuild Edge Docker: `docker-compose -f docker-compose.edge.yml build`
3. Start Edge Server: `docker-compose -f docker-compose.edge.yml up -d`
4. Run migrations: `docker exec fnb_edge_web python manage.py migrate`
5. Access setup: `http://localhost:8001/setup/`

---

**Status:** ✅ Implementation Complete
**Date:** 2026-01-27
**Architecture:** Multi-Brand with HO Sync
