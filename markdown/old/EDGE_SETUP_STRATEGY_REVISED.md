# Edge Server Setup Strategy - Revised
## Validasi Company & Store, Full Sync Brands dari HO

## 🎯 Revised Understanding

### Setup Flow:

```
Edge Server Setup:
1. ✅ Validate Company exists in HO
2. ✅ Validate Store exists in HO and belongs to Company
3. ✅ Save Company & Store config to Edge
4. ✅ Auto-sync ALL brands dari HO untuk company tersebut
5. ✅ Auto-sync products, categories, dll per brand
```

### Key Points:

- **Company & Store:** Validasi ID/Code sesuai HO
- **Brands:** Full sync dari HO (tidak pilih manual)
- **Master Data:** Follow brands yang ada di HO
- **One-time Setup:** Company & Store tidak bisa diganti setelah setup

## 🏗️ Revised Setup Architecture

### Setup Process

```
┌─────────────────────────────────────────────────────────────┐
│              Edge Server Setup (One-Time)                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Step 1: Select Company from HO                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Company: [YOGYA GROUP ▼] (fetch from HO API)          │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  Step 2: Select Store from HO                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Store: [YOGYA SUNDA ▼] (fetch from HO API)            │ │
│  │        - YOGYA MALIOBORO                               │ │
│  │        - YOGYA SUNDA                                   │ │
│  │        - YOGYA SUDIRMAN                                │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  Step 3: System Auto-Syncs Everything                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ ⏳ Syncing from HO Server...                           │ │
│  │ ✓ Company: YOGYA GROUP                                │ │
│  │ ✓ Store: YOGYA SUNDA                                  │ │
│  │ ✓ Brands: CHICKEN SUMO, NASI PADANG, SOTO (3)        │ │
│  │ ✓ Products: 150 items                                 │ │
│  │ ✓ Categories: 25 categories                           │ │
│  │ ✓ Condiments: 30 items                                │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  [💾 Complete Setup]                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Setup Flow Diagram

```
User Opens /setup/
       │
       ▼
Select Company (from HO)
       │
       ├─ Fetch companies from HO API
       ├─ User selects: YOGYA GROUP
       └─ Save company_id
       │
       ▼
Select Store (from HO, filtered by company)
       │
       ├─ Fetch stores for YOGYA GROUP from HO API
       ├─ User selects: YOGYA SUNDA
       └─ Save store_id
       │
       ▼
Backend Auto-Sync Process
       │
       ├─ 1. Sync Company from HO → Edge DB
       │   └─ Save: Company (YOGYA GROUP)
       │
       ├─ 2. Sync Store from HO → Edge DB
       │   └─ Save: Store (YOGYA SUNDA)
       │
       ├─ 3. Sync ALL Brands for this Store from HO
       │   ├─ Fetch: GET /api/sync/stores/{store_id}/brands/
       │   ├─ Save: Brand (CHICKEN SUMO)
       │   ├─ Save: Brand (NASI PADANG)
       │   ├─ Save: Brand (SOTO LAMONGAN)
       │   └─ Create: StoreBrand relationships
       │
       ├─ 4. Sync Products per Brand
       │   ├─ Fetch: GET /api/sync/products/?brand_id={uuid}
       │   └─ Save all products per brand
       │
       ├─ 5. Sync Categories per Brand
       │   ├─ Fetch: GET /api/sync/categories/?brand_id={uuid}
       │   └─ Save all categories per brand
       │
       └─ 6. Sync Condiments per Brand
           ├─ Fetch: GET /api/sync/condiments/?brand_id={uuid}
           └─ Save all condiments per brand
       │
       ▼
Setup Complete!
       │
       └─ Redirect to: /setup/terminal/ (register terminals)
```

## 🔧 Implementation

### Updated Setup View

```python
@csrf_exempt
def setup_store_config(request):
    """
    Edge Server Setup - Validate Company & Store, Sync All Brands
    One-time setup only
    """
    
    # Check if already setup
    if Store.objects.exists():
        messages.warning(request, 'Edge Server already configured')
        return redirect('core:setup_wizard')
    
    if request.method == 'POST':
        company_id = request.POST.get('company_id')
        store_id = request.POST.get('store_id')  # Changed: now get store_id from HO
        
        if not all([company_id, store_id]):
            messages.error(request, 'Company and Store are required')
            return redirect('core:setup_wizard')
        
        try:
            # Get HO API credentials
            ho_api_url = getattr(settings, 'HO_API_URL')
            username = getattr(settings, 'HO_API_USERNAME', 'admin')
            password = getattr(settings, 'HO_API_PASSWORD', 'admin123')
            
            # Step 1: Get JWT token
            print(f"[SETUP] Getting token from HO Server...")
            token_response = requests.post(
                f"{ho_api_url}/api/token/",
                json={'username': username, 'password': password},
                timeout=10
            )
            token_response.raise_for_status()
            access_token = token_response.json().get('access')
            
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Step 2: Validate and Sync Company
            print(f"[SETUP] Validating company {company_id}...")
            company_response = requests.get(
                f"{ho_api_url}/api/sync/companies/",
                headers=headers,
                timeout=10
            )
            company_response.raise_for_status()
            companies = company_response.json().get('companies', [])
            
            company_data = next((c for c in companies if c['id'] == company_id), None)
            if not company_data:
                messages.error(request, 'Company not found in HO Server')
                return redirect('core:setup_wizard')
            
            # Sync company to Edge
            company, _ = sync_company_from_remote(company_data)
            print(f"[SETUP] ✓ Company synced: {company.name}")
            
            # Step 3: Validate and Sync Store
            print(f"[SETUP] Validating store {store_id}...")
            store_response = requests.get(
                f"{ho_api_url}/api/sync/stores/",
                params={'company_id': company_id},
                headers=headers,
                timeout=10
            )
            store_response.raise_for_status()
            stores = store_response.json().get('stores', [])
            
            store_data = next((s for s in stores if s['id'] == store_id), None)
            if not store_data:
                messages.error(request, 'Store not found in HO Server')
                return redirect('core:setup_wizard')
            
            # Validate store belongs to company
            if store_data.get('company_id') != company_id:
                messages.error(request, 'Store does not belong to selected company')
                return redirect('core:setup_wizard')
            
            # Sync store to Edge (without brand - we'll link brands separately)
            store = Store.objects.create(
                id=store_data['id'],
                company=company,
                store_code=store_data['store_code'],
                store_name=store_data['store_name'],
                address=store_data.get('address', ''),
                phone=store_data.get('phone', ''),
            )
            print(f"[SETUP] ✓ Store synced: {store.store_name}")
            
            # Step 4: Sync ALL Brands for this Store from HO
            print(f"[SETUP] Syncing brands for store {store_id}...")
            brands_response = requests.get(
                f"{ho_api_url}/api/sync/stores/{store_id}/brands/",  # New endpoint!
                headers=headers,
                timeout=10
            )
            brands_response.raise_for_status()
            brands_data = brands_response.json().get('brands', [])
            
            synced_brands = []
            for brand_data in brands_data:
                # Sync brand to Edge
                brand, created = sync_brand_from_remote(brand_data)
                
                # Create StoreBrand relationship
                StoreBrand.objects.create(
                    store=store,
                    brand=brand,
                    is_active=True
                )
                
                synced_brands.append(brand.name)
                print(f"[SETUP] ✓ Brand synced: {brand.name}")
            
            # Step 5: Sync Master Data per Brand
            for brand_data in brands_data:
                brand_id = brand_data['id']
                brand_name = brand_data['name']
                
                print(f"[SETUP] Syncing master data for {brand_name}...")
                
                # Sync Products
                products_response = requests.get(
                    f"{ho_api_url}/api/sync/products/",
                    params={'brand_id': brand_id},
                    headers=headers,
                    timeout=30
                )
                if products_response.status_code == 200:
                    products_data = products_response.json().get('products', [])
                    for product_data in products_data:
                        sync_product_from_remote(product_data)
                    print(f"[SETUP]   ✓ Products: {len(products_data)} items")
                
                # Sync Categories
                categories_response = requests.get(
                    f"{ho_api_url}/api/sync/categories/",
                    params={'brand_id': brand_id},
                    headers=headers,
                    timeout=30
                )
                if categories_response.status_code == 200:
                    categories_data = categories_response.json().get('categories', [])
                    for category_data in categories_data:
                        sync_category_from_remote(category_data)
                    print(f"[SETUP]   ✓ Categories: {len(categories_data)} items")
                
                # Sync Condiments (if applicable)
                condiments_response = requests.get(
                    f"{ho_api_url}/api/sync/condiments/",
                    params={'brand_id': brand_id},
                    headers=headers,
                    timeout=30
                )
                if condiments_response.status_code == 200:
                    condiments_data = condiments_response.json().get('condiments', [])
                    for condiment_data in condiments_data:
                        sync_condiment_from_remote(condiment_data)
                    print(f"[SETUP]   ✓ Condiments: {len(condiments_data)} items")
            
            # Success!
            messages.success(
                request,
                f'✅ Edge Server Setup Complete!\n\n'
                f'Company: {company.name}\n'
                f'Store: {store.store_name} ({store.store_code})\n'
                f'Brands: {", ".join(synced_brands)} ({len(synced_brands)} brands)\n\n'
                f'All master data synced from HO Server.'
            )
            
            print(f"[SETUP] ✅ Setup complete!")
            return redirect('core:setup_wizard')
            
        except requests.exceptions.RequestException as e:
            print(f"[SETUP] ✗ API Error: {str(e)}")
            messages.error(request, f'Failed to connect to HO Server: {str(e)}')
        except Exception as e:
            print(f"[SETUP] ✗ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            messages.error(request, f'Setup failed: {str(e)}')
        
        return redirect('core:setup_wizard')
    
    return redirect('core:setup_wizard')
```

### New HO API Endpoint Needed

```python
# In HO Server: apps/core/views_sync.py

@csrf_exempt
def sync_store_brands(request, store_id):
    """
    Get all brands for a specific store
    This is used during Edge Server setup
    """
    try:
        store = Store.objects.get(id=store_id)
        
        # Get all brands for this store
        brands = Brand.objects.filter(
            brand_stores__store=store,
            brand_stores__is_active=True
        ).distinct()
        
        brands_data = []
        for brand in brands:
            brands_data.append({
                'id': str(brand.id),
                'company_id': str(brand.company_id),
                'code': brand.code,
                'name': brand.name,
                'logo': brand.logo.url if brand.logo else None,
                'is_active': brand.is_active,
            })
        
        return JsonResponse({
            'success': True,
            'store_id': str(store.id),
            'store_name': store.store_name,
            'brands': brands_data,
            'total': len(brands_data),
            'sync_timestamp': timezone.now().isoformat()
        })
        
    except Store.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Store not found'
        }, status=404)
```

### Updated Setup UI

```html
<!-- templates/core/setup_store.html -->

<form method="post" action="{% url 'core:setup_store_config' %}">
    {% csrf_token %}
    
    <!-- Hidden fields -->
    <input type="hidden" name="company_id" id="company_id_hidden">
    <input type="hidden" name="store_id" id="store_id_hidden">
    
    <!-- Step 1: Select Company -->
    <div>
        <label>Select Company *</label>
        <select id="company_select" required>
            <option value="">-- Loading from HO... --</option>
        </select>
        <p class="help">Company will be validated against HO Server</p>
    </div>
    
    <!-- Step 2: Select Store -->
    <div>
        <label>Select Store *</label>
        <select id="store_select" required disabled>
            <option value="">-- Select Company First --</option>
        </select>
        <p class="help">Store will be validated and synced from HO Server</p>
    </div>
    
    <!-- Info: What will be synced -->
    <div class="info-box">
        <h4>What happens next?</h4>
        <p>After you select Company and Store, the system will automatically:</p>
        <ul>
            <li>✓ Validate Company and Store exist in HO Server</li>
            <li>✓ Sync Company and Store config to this Edge Server</li>
            <li>✓ Sync ALL brands associated with this store</li>
            <li>✓ Sync all products, categories, and master data per brand</li>
        </ul>
        <p><strong>This is a one-time setup and cannot be changed later.</strong></p>
    </div>
    
    <button type="submit">
        🚀 Setup Edge Server (Sync from HO)
    </button>
</form>

<script>
// JavaScript to handle dropdowns
document.addEventListener('DOMContentLoaded', function() {
    const companySelect = document.getElementById('company_select');
    const storeSelect = document.getElementById('store_select');
    const companyIdHidden = document.getElementById('company_id_hidden');
    const storeIdHidden = document.getElementById('store_id_hidden');
    
    // Load companies from HO
    fetch('/api/ho/companies/')
        .then(r => r.json())
        .then(data => {
            companySelect.innerHTML = '<option value="">-- Select Company --</option>';
            data.companies.forEach(company => {
                const option = document.createElement('option');
                option.value = company.id;
                option.textContent = `${company.name} (${company.code})`;
                companySelect.appendChild(option);
            });
        });
    
    // When company selected, load stores
    companySelect.addEventListener('change', function() {
        const companyId = this.value;
        companyIdHidden.value = companyId;
        
        if (!companyId) {
            storeSelect.innerHTML = '<option value="">-- Select Company First --</option>';
            storeSelect.disabled = true;
            return;
        }
        
        storeSelect.innerHTML = '<option value="">-- Loading Stores... --</option>';
        storeSelect.disabled = true;
        
        // Load stores for this company from HO
        fetch(`/api/ho/stores/?company_id=${companyId}`)
            .then(r => r.json())
            .then(data => {
                storeSelect.innerHTML = '<option value="">-- Select Store --</option>';
                
                if (data.stores && data.stores.length > 0) {
                    data.stores.forEach(store => {
                        const option = document.createElement('option');
                        option.value = store.id;
                        option.textContent = `${store.store_name} (${store.store_code})`;
                        storeSelect.appendChild(option);
                    });
                    storeSelect.disabled = false;
                } else {
                    storeSelect.innerHTML = '<option value="">-- No Stores Found --</option>';
                }
            });
    });
    
    // When store selected, update hidden field
    storeSelect.addEventListener('change', function() {
        storeIdHidden.value = this.value;
    });
});
</script>
```

## 📊 Data Flow

### Setup Process Data Flow

```
Edge Server                          HO Server
───────────                          ─────────

1. User selects Company
   └─ GET /api/ho/companies/    →   Return: All companies

2. User selects Store
   └─ GET /api/ho/stores/       →   Return: Stores for company
      ?company_id={uuid}

3. User clicks Submit
   │
   ├─ POST /setup/store/
   │  Body: {company_id, store_id}
   │
   ├─ GET /api/token/           →   Return: JWT token
   │
   ├─ GET /api/sync/companies/  →   Return: Company data
   │  Headers: Bearer {token}
   │  └─ Save to Edge DB
   │
   ├─ GET /api/sync/stores/     →   Return: Store data
   │  ?company_id={uuid}
   │  └─ Save to Edge DB
   │
   ├─ GET /api/sync/stores/     →   Return: All brands for store
   │  {store_id}/brands/
   │  └─ Save to Edge DB
   │     Create StoreBrand links
   │
   └─ For each brand:
      ├─ GET /api/sync/products/    →   Return: Products
      │  ?brand_id={uuid}
      ├─ GET /api/sync/categories/  →   Return: Categories
      │  ?brand_id={uuid}
      └─ GET /api/sync/condiments/  →   Return: Condiments
         ?brand_id={uuid}
         └─ All saved to Edge DB
```

## ✅ Benefits of This Approach

### 1. **Single Source of Truth**
- HO Server manages all master data
- Edge Server always in sync with HO
- No manual brand selection = no mistakes

### 2. **Simplified Setup**
- User only selects Company & Store
- System auto-syncs everything else
- One-time setup, no confusion

### 3. **Always Consistent**
- If HO adds new brand to store → periodic sync will get it
- If HO removes brand → periodic sync will deactivate it
- No data drift between HO and Edge

### 4. **Validation Built-in**
- Store ID must exist in HO
- Store must belong to Company
- Cannot setup with invalid data

### 5. **Clear Audit Trail**
- Edge Server knows its Store ID from HO
- All transactions reference HO Store ID
- Easy to track in reports

## 🔄 Periodic Sync (After Setup)

After initial setup, Edge Server should periodically sync:

```python
# Periodic sync (cron job or scheduled task)
def periodic_sync_from_ho():
    """
    Sync updates from HO Server
    Run every 6 hours or as configured
    """
    
    store = Store.objects.first()  # Single store in Edge
    
    # Get token
    token = get_ho_api_token()
    
    # Sync brands (in case new brands added to store)
    sync_store_brands(store.id, token)
    
    # Sync products per brand
    for store_brand in store.store_brands.filter(is_active=True):
        brand = store_brand.brand
        sync_products_for_brand(brand.id, token)
        sync_categories_for_brand(brand.id, token)
        sync_condiments_for_brand(brand.id, token)
    
    print(f"[SYNC] Periodic sync completed for {store.store_name}")
```

## 🎯 Summary

### Setup Strategy:

1. **Company:** Validate ID from HO ✅
2. **Store:** Validate ID from HO ✅
3. **Brands:** Auto-sync ALL from HO ✅
4. **Master Data:** Auto-sync per brand ✅

### Key Points:

- ✅ User tidak pilih brands manually
- ✅ System auto-sync semua brands untuk store
- ✅ Store ID dari HO, bukan generate baru
- ✅ Company ID dari HO, bukan generate baru
- ✅ One-time setup, immutable
- ✅ Periodic sync untuk updates

### Next Steps:

- [ ] Add `/api/sync/stores/{store_id}/brands/` endpoint di HO Server
- [ ] Update setup view untuk auto-sync brands
- [ ] Update setup UI untuk remove brand selection
- [ ] Add periodic sync task
- [ ] Test setup flow end-to-end

**This is the correct approach for Edge-HO architecture!** 🎉
