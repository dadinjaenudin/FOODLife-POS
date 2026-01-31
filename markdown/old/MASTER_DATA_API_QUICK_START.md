# Master Data API - Quick Start Guide 🚀

## Overview

This guide shows you how to quickly use the Master Data Sync API endpoints that were just implemented.

**Status:** ✅ Implemented and Tested  
**Date:** January 27, 2026

---

## 🎯 Quick Test

### Option 1: Using the Test Script

```bash
python test_sync_api.py
```

This will run all 7 test cases and show you:
- ✅ All companies
- ✅ All brands for a company
- ✅ All stores for a brand
- ✅ Error handling validation

### Option 2: Using cURL

```bash
# 1. Get all companies
curl http://localhost:8000/api/sync/companies/

# 2. Get brands by company (replace with your company UUID)
curl "http://localhost:8000/api/sync/brands/?company_id=YOUR_COMPANY_UUID"

# 3. Get stores by brand (replace with your brand UUID)
curl "http://localhost:8000/api/sync/stores/?brand_id=YOUR_BRAND_UUID"
```

### Option 3: Using Browser

Simply open in your browser:
```
http://localhost:8000/api/sync/companies/
```

---

## 📋 API Endpoints Summary

| Endpoint | Method | Parameters | Description |
|----------|--------|------------|-------------|
| `/api/sync/companies/` | GET | None | List all active companies |
| `/api/sync/brands/` | GET | `company_id` (required) | List brands by company |
| `/api/sync/stores/` | GET | `brand_id` (required) | List stores by brand |

---

## 💻 Usage Examples

### Python (requests)

```python
import requests

BASE_URL = "http://localhost:8000"

# Get all companies
response = requests.get(f"{BASE_URL}/api/sync/companies/")
data = response.json()

print(f"Found {data['total']} companies")
for company in data['companies']:
    print(f"- {company['name']} ({company['code']})")
    
    # Get brands for this company
    brands_response = requests.get(
        f"{BASE_URL}/api/sync/brands/",
        params={'company_id': company['id']}
    )
    brands_data = brands_response.json()
    
    for brand in brands_data['brands']:
        print(f"  - Brand: {brand['name']} ({brand['code']})")
        
        # Get stores for this brand
        stores_response = requests.get(
            f"{BASE_URL}/api/sync/stores/",
            params={'brand_id': brand['id']}
        )
        stores_data = stores_response.json()
        
        for store in stores_data['stores']:
            print(f"    - Store: {store['store_name']} ({store['store_code']})")
```

### JavaScript (fetch)

```javascript
async function fetchMasterData() {
    // Get all companies
    const companiesRes = await fetch('/api/sync/companies/');
    const companiesData = await companiesRes.json();
    
    console.log(`Found ${companiesData.total} companies`);
    
    for (const company of companiesData.companies) {
        console.log(`Company: ${company.name} (${company.code})`);
        
        // Get brands for this company
        const brandsRes = await fetch(`/api/sync/brands/?company_id=${company.id}`);
        const brandsData = await brandsRes.json();
        
        for (const brand of brandsData.brands) {
            console.log(`  Brand: ${brand.name} (${brand.code})`);
            
            // Get stores for this brand
            const storesRes = await fetch(`/api/sync/stores/?brand_id=${brand.id}`);
            const storesData = await storesRes.json();
            
            for (const store of storesData.stores) {
                console.log(`    Store: ${store.store_name} (${store.store_code})`);
            }
        }
    }
}

fetchMasterData();
```

### Django Template (AJAX)

```html
<script>
// Load companies into dropdown
fetch('/api/sync/companies/')
    .then(response => response.json())
    .then(data => {
        const select = document.getElementById('company-select');
        data.companies.forEach(company => {
            const option = document.createElement('option');
            option.value = company.id;
            option.textContent = `${company.name} (${company.code})`;
            select.appendChild(option);
        });
    });

// When company is selected, load brands
document.getElementById('company-select').addEventListener('change', (e) => {
    const companyId = e.target.value;
    fetch(`/api/sync/brands/?company_id=${companyId}`)
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('brand-select');
            select.innerHTML = '<option value="">-- Select Brand --</option>';
            data.brands.forEach(brand => {
                const option = document.createElement('option');
                option.value = brand.id;
                option.textContent = `${brand.name} (${brand.code})`;
                select.appendChild(option);
            });
        });
});

// When brand is selected, load stores
document.getElementById('brand-select').addEventListener('change', (e) => {
    const brandId = e.target.value;
    fetch(`/api/sync/stores/?brand_id=${brandId}`)
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('store-select');
            select.innerHTML = '<option value="">-- Select Store --</option>';
            data.stores.forEach(store => {
                const option = document.createElement('option');
                option.value = store.id;
                option.textContent = `${store.store_name} (${store.store_code})`;
                select.appendChild(option);
            });
        });
});
</script>
```

---

## 🔍 Response Structure

### Companies Response
```json
{
  "companies": [
    {
      "id": "uuid",
      "code": "string",
      "name": "string",
      "timezone": "string",
      "is_active": boolean,
      "point_expiry_months": integer,
      "points_per_currency": "decimal",
      "created_at": "ISO8601",
      "updated_at": "ISO8601"
    }
  ],
  "total": integer,
  "sync_timestamp": "ISO8601"
}
```

### Brands Response
```json
{
  "brands": [
    {
      "id": "uuid",
      "company_id": "uuid",
      "company_code": "string",
      "company_name": "string",
      "code": "string",
      "name": "string",
      "address": "string",
      "phone": "string",
      "tax_id": "string",
      "tax_rate": "decimal",
      "service_charge": "decimal",
      "point_expiry_months_override": integer|null,
      "point_expiry_months": integer,
      "is_active": boolean,
      "created_at": "ISO8601",
      "updated_at": "ISO8601"
    }
  ],
  "total": integer,
  "company": {
    "id": "uuid",
    "code": "string",
    "name": "string"
  },
  "sync_timestamp": "ISO8601"
}
```

### Stores Response
```json
{
  "stores": [
    {
      "id": integer,
      "brand_id": "uuid",
      "brand_code": "string",
      "brand_name": "string",
      "company_id": "uuid",
      "company_code": "string",
      "company_name": "string",
      "store_code": "string",
      "store_name": "string",
      "address": "string",
      "phone": "string",
      "timezone": "string",
      "latitude": "decimal"|null,
      "longitude": "decimal"|null,
      "is_active": boolean,
      "configured_at": "ISO8601"
    }
  ],
  "total": integer,
  "brand": {
    "id": "uuid",
    "code": "string",
    "name": "string",
    "company_id": "uuid",
    "company_code": "string",
    "company_name": "string"
  },
  "sync_timestamp": "ISO8601"
}
```

---

## ⚠️ Error Responses

### 400 Bad Request
```json
{
  "error": "Missing required parameter: company_id"
}
```

### 404 Not Found
```json
{
  "error": "Company not found: 00000000-0000-0000-0000-000000000000"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error: <error message>"
}
```

---

## 🎨 Integration with Setup UI

You can integrate these APIs with the existing setup wizard in `apps/core/views_setup.py`:

```python
# Example: Enhance setup_wizard to support remote HO API
import requests
from django.conf import settings

def setup_wizard(request):
    # Check if HO API is configured
    if hasattr(settings, 'HO_API_URL') and settings.HO_API_URL:
        # Fetch from remote HO API
        try:
            response = requests.get(f"{settings.HO_API_URL}/api/sync/companies/")
            companies_data = response.json()
            # Convert to Company objects or use directly in template
        except:
            # Fallback to local database
            companies = Company.objects.filter(is_active=True)
    else:
        # Use local database (current behavior)
        companies = Company.objects.filter(is_active=True)
    
    # Rest of the wizard logic...
```

---

## 📊 Current Database Status

Run this to check your current data:

```python
python manage.py shell -c "from apps.core.models import Company, Brand, Store; print(f'Companies: {Company.objects.count()}'); print(f'Brands: {Brand.objects.count()}'); print(f'Stores: {Store.objects.count()}')"
```

---

## 🚀 What's Next?

### Immediate Use Cases
1. **Edge Server Setup** - Use these APIs for initial configuration
2. **Remote Sync** - Pull master data from Head Office server
3. **Multi-tenant Admin** - Build admin UIs for managing hierarchy

### Future Enhancements
1. Add authentication (Token/JWT)
2. Add pagination for large datasets
3. Add filtering (e.g., search by name, code)
4. Add sorting options
5. Add field selection (e.g., only return specific fields)
6. Add caching for better performance

---

## 📚 Related Documentation

- **`MASTER_DATA_API_DOCUMENTATION.md`** - Full API specification
- **`MASTER_DATA_API_IMPLEMENTATION_COMPLETE.md`** - Implementation details
- **`test_sync_api.py`** - Test script with examples
- **`apps/core/views_sync.py`** - Source code for API views
- **`apps/core/urls.py`** - URL routing configuration

---

## ✅ Verification Checklist

Before using in production:

- [x] API endpoints implemented
- [x] URL routing configured
- [x] Error handling tested
- [x] Response format validated
- [x] Documentation complete
- [ ] Authentication added (optional)
- [ ] Rate limiting configured (optional)
- [ ] Monitoring/logging setup (optional)

---

## 🎉 You're Ready!

The Master Data Sync API is now ready to use. Start with:

```bash
python test_sync_api.py
```

Or open in browser:
```
http://localhost:8000/api/sync/companies/
```

Happy coding! 🚀
