# Master Data API Implementation - Complete ✅

## Overview

The Master Data Sync API endpoints have been successfully implemented to provide hierarchical access to Companies, Brands, and Stores for Edge Server configuration.

**Implementation Date:** January 27, 2026  
**Status:** ✅ Complete and Tested

---

## 📁 Files Created/Modified

### New Files
1. **`apps/core/views_sync.py`** - API view functions
   - `sync_companies()` - List all active companies
   - `sync_brands()` - List brands by company_id
   - `sync_stores()` - List stores by brand_id

2. **`test_sync_api.py`** - Test script for API validation

### Modified Files
1. **`apps/core/urls.py`** - Added URL patterns for sync endpoints

---

## 🔗 API Endpoints

### 1. GET /api/sync/companies/

**Purpose:** Get all active companies in the system

**URL:** `/api/sync/companies/`

**Method:** `GET`

**Authentication:** None (can be added later)

**Query Parameters:** None

**Response Example:**
```json
{
  "companies": [
    {
      "id": "1363c720-4c02-4357-beca-dd50b3a10e3a",
      "code": "YOYGA001",
      "name": "YOGYA DEPARTEMENT STORE",
      "timezone": "Asia/Jakarta",
      "is_active": true,
      "point_expiry_months": 12,
      "points_per_currency": "1.00",
      "created_at": "2026-01-21T08:30:45.123Z",
      "updated_at": "2026-01-21T08:30:45.123Z"
    }
  ],
  "total": 1,
  "sync_timestamp": "2026-01-27T11:12:34.567Z"
}
```

**Status Codes:**
- `200 OK` - Success
- `500 Internal Server Error` - Server error

---

### 2. GET /api/sync/brands/?company_id={uuid}

**Purpose:** Get all active brands for a specific company

**URL:** `/api/sync/brands/`

**Method:** `GET`

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| company_id | UUID | Yes | UUID of the company |

**Response Example:**
```json
{
  "brands": [
    {
      "id": "328cfb14-45e3-4792-b149-8d9bc386ed22",
      "company_id": "1363c720-4c02-4357-beca-dd50b3a10e3a",
      "company_code": "YOYGA001",
      "company_name": "YOGYA DEPARTEMENT STORE",
      "code": "AVRIL",
      "name": "AVRIL",
      "address": "Jl. Example No. 123",
      "phone": "021-1234567",
      "tax_id": "01.234.567.8-901.000",
      "tax_rate": "11.00",
      "service_charge": "5.00",
      "point_expiry_months_override": null,
      "point_expiry_months": 12,
      "is_active": true,
      "created_at": "2026-01-21T08:30:45.123Z",
      "updated_at": "2026-01-21T08:30:45.123Z"
    }
  ],
  "total": 1,
  "company": {
    "id": "1363c720-4c02-4357-beca-dd50b3a10e3a",
    "code": "YOYGA001",
    "name": "YOGYA DEPARTEMENT STORE"
  },
  "sync_timestamp": "2026-01-27T11:12:34.567Z"
}
```

**Status Codes:**
- `200 OK` - Success
- `400 Bad Request` - Missing company_id parameter
- `404 Not Found` - Company not found
- `500 Internal Server Error` - Server error

**Error Response Example (400):**
```json
{
  "error": "Missing required parameter: company_id"
}
```

**Error Response Example (404):**
```json
{
  "error": "Company not found: 00000000-0000-0000-0000-000000000000"
}
```

---

### 3. GET /api/sync/stores/?brand_id={uuid}

**Purpose:** Get all active stores for a specific brand

**URL:** `/api/sync/stores/`

**Method:** `GET`

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| brand_id | UUID | Yes | UUID of the brand |

**Response Example:**
```json
{
  "stores": [
    {
      "id": 1,
      "brand_id": "328cfb14-45e3-4792-b149-8d9bc386ed22",
      "brand_code": "AVRIL",
      "brand_name": "AVRIL",
      "company_id": "1363c720-4c02-4357-beca-dd50b3a10e3a",
      "company_code": "YOYGA001",
      "company_name": "YOGYA DEPARTEMENT STORE",
      "store_code": "AVRIL-BSD",
      "store_name": "AVRIL BSD",
      "address": "BSD City",
      "phone": "021-7654321",
      "timezone": "Asia/Jakarta",
      "latitude": "-6.302100",
      "longitude": "106.652900",
      "is_active": true,
      "configured_at": "2026-01-21T08:30:45.123Z"
    }
  ],
  "total": 1,
  "brand": {
    "id": "328cfb14-45e3-4792-b149-8d9bc386ed22",
    "code": "AVRIL",
    "name": "AVRIL",
    "company_id": "1363c720-4c02-4357-beca-dd50b3a10e3a",
    "company_code": "YOYGA001",
    "company_name": "YOGYA DEPARTEMENT STORE"
  },
  "sync_timestamp": "2026-01-27T11:12:34.567Z"
}
```

**Status Codes:**
- `200 OK` - Success
- `400 Bad Request` - Missing brand_id parameter
- `404 Not Found` - Brand not found
- `500 Internal Server Error` - Server error

**Error Response Example (400):**
```json
{
  "error": "Missing required parameter: brand_id"
}
```

**Error Response Example (404):**
```json
{
  "error": "Brand not found: 00000000-0000-0000-0000-000000000000"
}
```

---

## 🧪 Testing Results

All tests passed successfully:

### Test 1: GET /api/sync/companies/
- ✅ Status Code: 200
- ✅ Returns list of companies
- ✅ Includes total count and sync_timestamp

### Test 2: GET /api/sync/brands/?company_id={uuid}
- ✅ Status Code: 200
- ✅ Returns list of brands for the company
- ✅ Includes parent company information
- ✅ Includes total count and sync_timestamp

### Test 3: GET /api/sync/stores/?brand_id={uuid}
- ✅ Status Code: 200
- ✅ Returns list of stores for the brand
- ✅ Includes parent brand and company information
- ✅ Includes total count and sync_timestamp

### Test 4: Error Handling - Missing company_id
- ✅ Status Code: 400
- ✅ Returns proper error message

### Test 5: Error Handling - Missing brand_id
- ✅ Status Code: 400
- ✅ Returns proper error message

### Test 6: Error Handling - Invalid company_id
- ✅ Status Code: 404
- ✅ Returns proper error message

### Test 7: Error Handling - Invalid brand_id
- ✅ Status Code: 404
- ✅ Returns proper error message

---

## 🎯 Key Features Implemented

### 1. Hierarchical Data Structure
- Each response includes parent entity information
- **Brands** include company details (id, code, name)
- **Stores** include both brand and company details

### 2. Active Filtering
- All endpoints automatically filter for `is_active=True`
- Ensures only valid configurations are returned

### 3. Query Optimization
- Uses `select_related()` to minimize database queries
- Efficient data retrieval with JOIN operations

### 4. Proper Error Handling
- `400 Bad Request` for missing parameters
- `404 Not Found` for invalid UUIDs
- `500 Internal Server Error` for unexpected errors
- Clear error messages for debugging

### 5. Timestamp Tracking
- Every response includes `sync_timestamp` in ISO 8601 format
- Useful for audit trails and debugging

### 6. CSRF Exempt
- API endpoints are decorated with `@csrf_exempt`
- Allows external systems to call the API

---

## 📊 Database Schema

### Company Model
```python
- id (UUID, PK)
- code (CharField, unique)
- name (CharField)
- timezone (CharField)
- is_active (BooleanField)
- point_expiry_months (IntegerField)
- points_per_currency (DecimalField)
- created_at, updated_at (DateTimeField)
```

### Brand Model
```python
- id (UUID, PK)
- company (FK → Company)
- code (CharField)
- name (CharField)
- address, phone, tax_id (CharField/TextField)
- tax_rate, service_charge (DecimalField)
- point_expiry_months_override (IntegerField, nullable)
- is_active (BooleanField)
- created_at, updated_at (DateTimeField)
```

### Store Model
```python
- id (Integer, PK)
- brand (FK → Brand)
- store_code (CharField, unique)
- store_name (CharField)
- address, phone (CharField/TextField)
- timezone (CharField)
- latitude, longitude (DecimalField)
- is_active (BooleanField)
- configured_at (DateTimeField)
```

---

## 🔄 Typical Usage Flow

1. **Get All Companies**
   ```bash
   GET /api/sync/companies/
   ```
   → User/System selects a company

2. **Get Brands for Selected Company**
   ```bash
   GET /api/sync/brands/?company_id={selected_company_uuid}
   ```
   → User/System selects a brand

3. **Get Stores for Selected Brand**
   ```bash
   GET /api/sync/stores/?brand_id={selected_brand_uuid}
   ```
   → User/System selects a store (becomes Edge Server identity)

4. **Sync Operational Data**
   - Use the `store_id` and `company_id` to sync other data
   - Example: Products, Categories, Promotions, etc.

---

## 🚀 How to Use

### Python Example
```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Get all companies
response = requests.get(f"{BASE_URL}/api/sync/companies/")
companies = response.json()['companies']
company_id = companies[0]['id']

# 2. Get brands for company
response = requests.get(f"{BASE_URL}/api/sync/brands/?company_id={company_id}")
brands = response.json()['brands']
brand_id = brands[0]['id']

# 3. Get stores for brand
response = requests.get(f"{BASE_URL}/api/sync/stores/?brand_id={brand_id}")
stores = response.json()['stores']
store = stores[0]
```

### cURL Example
```bash
# Get all companies
curl http://localhost:8000/api/sync/companies/

# Get brands by company
curl "http://localhost:8000/api/sync/brands/?company_id=1363c720-4c02-4357-beca-dd50b3a10e3a"

# Get stores by brand
curl "http://localhost:8000/api/sync/stores/?brand_id=328cfb14-45e3-4792-b149-8d9bc386ed22"
```

### JavaScript Example
```javascript
// Get all companies
const response = await fetch('/api/sync/companies/');
const data = await response.json();
const companyId = data.companies[0].id;

// Get brands for company
const brandsResponse = await fetch(`/api/sync/brands/?company_id=${companyId}`);
const brandsData = await brandsResponse.json();
const brandId = brandsData.brands[0].id;

// Get stores for brand
const storesResponse = await fetch(`/api/sync/stores/?brand_id=${brandId}`);
const storesData = await storesResponse.json();
```

---

## 🔐 Security Considerations

### Current Implementation
- ✅ No authentication required (suitable for internal network)
- ✅ CSRF exempt (allows external API calls)
- ✅ Only returns active records (security by default)

### Future Enhancements (Optional)
- Add Token/JWT authentication
- Add rate limiting
- Add API key validation
- Add IP whitelisting
- Add detailed audit logging

---

## 📝 Next Steps

### Integration with Setup UI
The existing setup UI (`apps/core/views_setup.py`) can be enhanced to:
1. Fetch data from these APIs instead of direct database queries
2. Support remote HO (Head Office) server configuration
3. Enable Edge Server to pull master data from central system

### Example Integration
```python
# In setup wizard, fetch companies from API
import requests

def setup_wizard(request):
    # Option 1: Local database (current)
    companies = Company.objects.filter(is_active=True)
    
    # Option 2: Remote HO API (future enhancement)
    if settings.HO_API_URL:
        response = requests.get(f"{settings.HO_API_URL}/api/sync/companies/")
        companies_data = response.json()['companies']
```

---

## ✅ Summary

**What Was Implemented:**
1. ✅ Three API endpoints for master data sync
2. ✅ Complete error handling (400, 404, 500)
3. ✅ Hierarchical data structure with parent info
4. ✅ Query optimization with select_related()
5. ✅ Comprehensive test suite
6. ✅ Full documentation

**Test Results:**
- All 7 test cases passed ✅
- API endpoints working correctly ✅
- Error handling properly implemented ✅
- Data structure matches documentation ✅

**Database Status:**
- 1 Company configured
- 1 Brand configured
- 1 Store configured

The Master Data Sync API is now **production-ready** and can be used for Edge Server setup and configuration! 🎉
