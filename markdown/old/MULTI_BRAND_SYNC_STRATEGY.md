# Multi-Brand Edge Server - Sync Strategy with HO

## ✅ YES, Data dari HO Masih Bisa Diambil!

### Strategi: Edge Schema Berbeda, Sync Logic Custom

## 🏗️ Schema Comparison

### HO Schema (Current):
```sql
company (id, code, name)
  ↓
brand (id, code, name, company_id)
  ↓
store (id, store_code, store_name, brand_id)  ← 1 Brand per Store

Example HO Data:
Store: YGY-SND-SUMO, Brand: CHICKEN SUMO
Store: YGY-SND-PADANG, Brand: NASI PADANG
Store: YGY-SND-SOTO, Brand: SOTO LAMONGAN
```

### Edge Schema (Modified):
```sql
company (id, code, name)
  ↓
store (id, store_code, store_name, company_id)  ← NO brand_id!
  ↓
store_brand (store_id, brand_id)  ← Many-to-Many
  ↓
brand (id, code, name, company_id)

Example Edge Data:
Store: YGY-SUNDA (single store)
├─ StoreBrand: CHICKEN SUMO
├─ StoreBrand: NASI PADANG
└─ StoreBrand: SOTO LAMONGAN
```

## 🔄 Sync Strategy: Aggregate Multiple HO Stores

### Scenario:
Di HO ada 3 stores untuk food court yang sama:
```
HO Stores:
- YGY-SND-SUMO (store_code: YGY-SND-SUMO, brand: CHICKEN SUMO)
- YGY-SND-PADANG (store_code: YGY-SND-PADANG, brand: NASI PADANG)
- YGY-SND-SOTO (store_code: YGY-SND-SOTO, brand: SOTO LAMONGAN)
```

Di Edge, kita aggregate jadi 1 store:
```
Edge Store:
- Store: YGY-SUNDA
  ├─ Brand: CHICKEN SUMO
  ├─ Brand: NASI PADANG
  └─ Brand: SOTO LAMONGAN
```

## 📊 Setup Flow dengan Sync Custom

### User Setup di Edge:

```
1. User enters PHYSICAL store info:
   - Store Code: YGY-SUNDA
   - Store Name: YOGYA SUNDA FOOD COURT
   - Company: YOGYA GROUP

2. User selects HO store codes yang mewakili brands:
   - HO Store 1: YGY-SND-SUMO → Brand: CHICKEN SUMO
   - HO Store 2: YGY-SND-PADANG → Brand: NASI PADANG
   - HO Store 3: YGY-SND-SOTO → Brand: SOTO LAMONGAN

3. System creates:
   - 1 Edge Store (YGY-SUNDA)
   - 3 StoreBrand relationships
   - Sync products from each HO store
```

### Setup API Call:

```javascript
// Edge Setup API
POST /setup/store/
{
  "company_id": "699f0e0a-...",  // YOGYA GROUP
  "store_code": "YGY-SUNDA",     // Physical store
  "store_name": "YOGYA SUNDA FOOD COURT",
  "ho_store_ids": [
    "uuid-ygy-snd-sumo",    // HO store for CHICKEN SUMO
    "uuid-ygy-snd-padang",  // HO store for NASI PADANG
    "uuid-ygy-snd-soto"     // HO store for SOTO LAMONGAN
  ]
}
```

### Sync Logic:

```python
def setup_multi_brand_store(company_id, store_code, store_name, ho_store_ids):
    """
    Setup Edge store dengan multiple brands dari multiple HO stores
    """
    
    # Step 1: Sync Company
    company = sync_company_from_ho(company_id)
    
    # Step 2: Create Edge Store (single store for physical location)
    edge_store = Store.objects.create(
        company=company,
        store_code=store_code,
        store_name=store_name,
        # NO brand_id field!
    )
    
    # Step 3: For each HO store, get brand and sync data
    for ho_store_id in ho_store_ids:
        # Get HO store data
        ho_store_data = fetch_ho_store(ho_store_id)
        
        # Get brand from HO store
        brand_id = ho_store_data['brand_id']
        
        # Sync brand to Edge
        brand = sync_brand_from_ho(brand_id)
        
        # Create StoreBrand relationship
        StoreBrand.objects.create(
            store=edge_store,
            brand=brand,
            ho_store_id=ho_store_id,  # Keep reference to HO store!
            is_active=True
        )
        
        # Sync products for this brand (from HO store)
        sync_products_from_ho_store(ho_store_id, brand)
        
        # Sync categories for this brand
        sync_categories_from_ho_store(ho_store_id, brand)
    
    return edge_store
```

## 🗂️ Modified StoreBrand Model

```python
class StoreBrand(models.Model):
    """
    Many-to-Many: Edge Store dapat punya banyak Brands
    Keep reference ke HO store untuk sync
    """
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    
    # NEW: Reference to HO store for this brand
    ho_store_id = models.UUIDField(
        help_text="HO Store ID yang represent brand ini"
    )
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = [['store', 'brand']]
```

## 📡 Sync Products from HO

### Problem: HO Store has brand_id, Edge needs to map
```python
def sync_products_from_ho_store(ho_store_id, edge_brand):
    """
    Fetch products dari HO store, save ke Edge dengan brand mapping
    """
    
    # Get products from HO store
    ho_products = fetch_from_ho_api(
        f'/api/sync/products/?store_id={ho_store_id}'
    )
    
    for ho_product in ho_products:
        # Save to Edge with correct brand mapping
        Product.objects.update_or_create(
            id=ho_product['id'],
            defaults={
                'brand': edge_brand,  # Map to Edge brand
                'company': edge_brand.company,
                'name': ho_product['name'],
                'price': ho_product['price'],
                # ... other fields
            }
        )
```

## 🔄 Periodic Sync Strategy

```python
def periodic_sync_multi_brand_store():
    """
    Periodic sync untuk multi-brand store
    Sync dari multiple HO stores
    """
    
    edge_store = Store.objects.first()
    
    # For each brand in this store
    for store_brand in edge_store.store_brands.filter(is_active=True):
        ho_store_id = store_brand.ho_store_id
        edge_brand = store_brand.brand
        
        print(f"[SYNC] Syncing brand {edge_brand.name} from HO store {ho_store_id}")
        
        # Sync products from this HO store
        sync_products_from_ho_store(ho_store_id, edge_brand)
        
        # Sync categories
        sync_categories_from_ho_store(ho_store_id, edge_brand)
        
        # Sync other master data
        sync_condiments_from_ho_store(ho_store_id, edge_brand)
```

## 📤 Transaction Sync to HO

### Problem: Edge bill needs to know which HO store to sync to

```python
class Bill(models.Model):
    store = models.ForeignKey(Store)  # Edge store
    brand = models.ForeignKey(Brand)  # Brand being served
    terminal = models.ForeignKey(Terminal)
    
    # NEW: For sync back to HO
    ho_store_id = models.UUIDField(
        help_text="HO Store ID untuk sync transaksi ini"
    )
```

When creating bill:
```python
def create_bill(terminal, brand):
    # Get HO store ID for this brand
    store_brand = StoreBrand.objects.get(
        store=terminal.store,
        brand=brand
    )
    
    bill = Bill.objects.create(
        store=terminal.store,
        brand=brand,
        terminal=terminal,
        ho_store_id=store_brand.ho_store_id  # For sync to correct HO store
    )
```

When syncing to HO:
```python
def sync_bill_to_ho(bill):
    """
    Sync Edge bill ke HO store yang tepat
    """
    
    # Sync ke HO store yang sesuai dengan brand
    response = post_to_ho_api(
        f'/api/sync/bills/',
        data={
            'store_id': bill.ho_store_id,  # HO store ID
            'bill_number': bill.bill_number,
            'total_amount': bill.total_amount,
            'items': [...],
            # ... other data
        }
    )
```

## 📊 Reporting Considerations

### Edge Reporting:
```python
# Sales by Edge store (aggregate all brands)
edge_store_sales = Bill.objects.filter(
    store=edge_store
).aggregate(total=Sum('total_amount'))

# Sales by brand in Edge store
brand_sales = Bill.objects.filter(
    store=edge_store
).values('brand__name').annotate(
    total=Sum('total_amount')
)
```

### HO Reporting:
HO tetap bisa report per HO store:
```sql
-- Di HO, report per store (each brand separate)
SELECT store_code, SUM(total_amount)
FROM bills
WHERE store_id IN ('ygy-snd-sumo', 'ygy-snd-padang', 'ygy-snd-soto')
GROUP BY store_code
```

## ✅ Advantages of This Approach

### 1. **Flexible Edge Schema**
- 1 physical store = 1 Edge store record
- Multiple brands via StoreBrand
- Clear terminal assignment

### 2. **Compatible with HO Data**
- Still fetch from HO API
- Map HO stores → Edge brands
- Keep reference (ho_store_id)

### 3. **Accurate Transaction Sync**
- Each bill knows which HO store to sync to
- HO receives bills in correct stores
- Reports accurate in both systems

### 4. **Future Proof**
- If HO adds multi-brand support later, easy to migrate
- If HO stays single-brand, still works
- Edge can evolve independently

## ⚠️ Challenges & Solutions

### Challenge 1: Setup Complexity
**Problem:** User needs to select multiple HO stores

**Solution:**
```javascript
// Smart UI: Show HO stores grouped by brand
Company: YOGYA GROUP
Store Code: YGY-SUNDA

Select brands by choosing HO stores:
☑ CHICKEN SUMO (HO Store: YGY-SND-SUMO)
☑ NASI PADANG (HO Store: YGY-SND-PADANG)
☑ SOTO LAMONGAN (HO Store: YGY-SND-SOTO)
```

### Challenge 2: Product Duplication
**Problem:** Same product might exist in multiple HO stores

**Solution:**
```python
# Use product ID from HO as primary key
# Same product across brands = same ID
Product.objects.update_or_create(
    id=ho_product['id'],  # UUID from HO
    defaults={...}
)
```

### Challenge 3: Store Code Uniqueness
**Problem:** HO has multiple stores (YGY-SND-SUMO, YGY-SND-PADANG), Edge has one (YGY-SUNDA)

**Solution:**
```python
# Edge store_code different from HO store_code
# But keep mapping via StoreBrand.ho_store_id
```

## 🎯 Summary

### Can We Sync from HO?
**✅ YES!** With custom logic:

1. **Setup:** User selects multiple HO stores → Create 1 Edge store with multiple brands
2. **Sync:** For each brand, sync from corresponding HO store
3. **Transactions:** Each bill references HO store ID for sync back
4. **Reporting:** Edge aggregates, HO sees per-store

### Data Flow:
```
HO Stores (3 separate):          Edge Store (1 aggregated):
├─ YGY-SND-SUMO                  Store: YGY-SUNDA
├─ YGY-SND-PADANG        →       ├─ Brand: CHICKEN SUMO (ho_store_id: YGY-SND-SUMO)
└─ YGY-SND-SOTO                  ├─ Brand: NASI PADANG (ho_store_id: YGY-SND-PADANG)
                                  └─ Brand: SOTO LAMONGAN (ho_store_id: YGY-SND-SOTO)
```

### Key Points:
- ✅ Edge schema berbeda dari HO (multi-brand capable)
- ✅ Data tetap bisa sync dari HO via API
- ✅ Keep reference (ho_store_id) untuk mapping
- ✅ Transaction sync back ke HO store yang tepat
- ⚠️ Setup flow lebih complex (pilih multiple HO stores)
- ⚠️ Butuh custom sync logic (tidak direct 1:1)

**Recommendation:** Implement Option B untuk flexibility, dengan extra effort di sync logic.
