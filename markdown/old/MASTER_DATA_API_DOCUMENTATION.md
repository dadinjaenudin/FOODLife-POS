# Master Data API Documentation

## Overview

Master Data APIs provide hierarchical access to Companies, Brands, and Stores for Edge Server configuration and setup.

**Base URL:** `/api/sync/`

**Authentication:** Required (Token/JWT)

---

## 📋 API Endpoints

### 1. GET /api/sync/companies/

Get all active companies in the system.

**URL:** `/api/sync/companies/`

**Method:** `GET`

**Authentication:** Required

**Query Parameters:** None

**Response Format:**
```json
{
  "companies": [
    {
      "id": "uuid",
      "code": "YGY",
      "name": "Yogya Group",
      "timezone": "Asia/Jakarta",
      "is_active": true,
      "point_expiry_months": 12,
      "points_per_currency": "1.00",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1,
  "sync_timestamp": "2026-01-27T10:00:00Z"
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8002/api/sync/companies/" \
  -H "Authorization: Token YOUR_API_TOKEN"
```

---

### 2. GET /api/sync/brands/?company_id={uuid}

Get all active brands for a specific company.

**URL:** `/api/sync/brands/`

**Method:** `GET`

**Authentication:** Required

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| company_id | UUID | Yes | UUID of the company |

**Response Format:**
```json
{
  "brands": [
    {
      "id": "uuid",
      "company_id": "uuid",
      "company_code": "YGY",
      "company_name": "Yogya Group",
      "code": "YGY-001",
      "name": "Ayam Geprek Express",
      "address": "Jl. Contoh No. 123",
      "phone": "021-1234567",
      "tax_id": "01.234.567.8-901.000",
      "tax_rate": "11.00",
      "service_charge": "5.00",
      "point_expiry_months_override": null,
      "point_expiry_months": 12,
      "is_active": true,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1,
  "company": {
    "id": "uuid",
    "code": "YGY",
    "name": "Yogya Group"
  },
  "sync_timestamp": "2026-01-27T10:00:00Z"
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8002/api/sync/brands/?company_id=YOUR_COMPANY_UUID" \
  -H "Authorization: Token YOUR_API_TOKEN"
```

**Error Responses:**

- `400 Bad Request` - Missing company_id parameter
```json
{
  "error": "Missing required parameter: company_id"
}
```

- `404 Not Found` - Company not found
```json
{
  "error": "Company not found: {uuid}"
}
```

---

### 3. GET /api/sync/stores/?brand_id={uuid}

Get all active stores for a specific brand.

**URL:** `/api/sync/stores/`

**Method:** `GET`

**Authentication:** Required

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| brand_id | UUID | Yes | UUID of the brand |

**Response Format:**
```json
{
  "stores": [
    {
      "id": "uuid",
      "brand_id": "uuid",
      "brand_code": "YGY-001",
      "brand_name": "Ayam Geprek Express",
      "company_id": "uuid",
      "company_code": "YGY",
      "company_name": "Yogya Group",
      "store_code": "YGY-001-BSD",
      "store_name": "Cabang BSD",
      "address": "Jl. BSD Raya No. 123",
      "phone": "021-7654321",
      "timezone": "Asia/Jakarta",
      "latitude": "-6.302100",
      "longitude": "106.652900",
      "is_active": true,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1,
  "brand": {
    "id": "uuid",
    "code": "YGY-001",
    "name": "Ayam Geprek Express",
    "company_id": "uuid",
    "company_code": "YGY",
    "company_name": "Yogya Group"
  },
  "sync_timestamp": "2026-01-27T10:00:00Z"
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8002/api/sync/stores/?brand_id=YOUR_BRAND_UUID" \
  -H "Authorization: Token YOUR_API_TOKEN"
```

**Error Responses:**

- `400 Bad Request` - Missing brand_id parameter
```json
{
  "error": "Missing required parameter: brand_id"
}
```

- `404 Not Found` - Brand not found
```json
{
  "error": "Brand not found: {uuid}"
}
```

---

## 🔄 Typical Sync Flow for Edge Server

When setting up an Edge Server, follow this hierarchical flow:

1. **Get All Companies**
   ```bash
   GET /api/sync/companies/
   ```
   → User selects company from dropdown

2. **Get Brands for Selected Company**
   ```bash
   GET /api/sync/brands/?company_id={selected_company_uuid}
   ```
   → User selects brand from dropdown

3. **Get Stores for Selected Brand**
   ```bash
   GET /api/sync/stores/?brand_id={selected_brand_uuid}
   ```
   → User selects store (this becomes the Edge Server identity)

4. **Sync Operational Data**
   - Use the `store_id` to sync promotions, products, categories, etc.
   - Example: `GET /api/sync/promotions/?store_id={store_uuid}&company_id={company_uuid}`

---

## 🔑 Key Features

### Hierarchical Relationships
Each API response includes parent entity information:
- **Brands** include company details
- **Stores** include both brand and company details

This eliminates the need for additional API calls to fetch parent information.

### Active Filtering
All endpoints automatically filter for `is_active=True` records only, ensuring Edge Servers only see valid, active configurations.

### Timestamp Tracking
Every response includes a `sync_timestamp` field for audit and debugging purposes.

### Optimized Queries
All endpoints use `select_related()` to minimize database queries and improve performance.

---

## 🧪 Testing

### Using cURL

```bash
# 1. Get authentication token first
curl -X POST "http://localhost:8002/api/token/" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}'

# Save the token from response
TOKEN="your_token_here"

# 2. Test Companies endpoint
curl -X GET "http://localhost:8002/api/sync/companies/" \
  -H "Authorization: Token $TOKEN"

# 3. Test Brands endpoint (replace with actual company_id)
curl -X GET "http://localhost:8002/api/sync/brands/?company_id=COMPANY_UUID" \
  -H "Authorization: Token $TOKEN"

# 4. Test Stores endpoint (replace with actual brand_id)
curl -X GET "http://localhost:8002/api/sync/stores/?brand_id=BRAND_UUID" \
  -H "Authorization: Token $TOKEN"
```

### Using Python

```python
import requests

BASE_URL = "http://localhost:8002"
TOKEN = "your_token_here"
headers = {"Authorization": f"Token {TOKEN}"}

# Get companies
response = requests.get(f"{BASE_URL}/api/sync/companies/", headers=headers)
companies = response.json()["companies"]

# Get brands for first company
company_id = companies[0]["id"]
response = requests.get(
    f"{BASE_URL}/api/sync/brands/",
    headers=headers,
    params={"company_id": company_id}
)
brands = response.json()["brands"]

# Get stores for first brand
brand_id = brands[0]["id"]
response = requests.get(
    f"{BASE_URL}/api/sync/stores/",
    headers=headers,
    params={"brand_id": brand_id}
)
stores = response.json()["stores"]

print(f"Found {len(stores)} stores")
```

---

## 📊 Response Fields Reference

### Company Fields
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Unique company identifier |
| code | String | Company code (e.g., "YGY") |
| name | String | Company name |
| timezone | String | Default timezone |
| is_active | Boolean | Active status |
| point_expiry_months | Integer | Default point expiry period |
| points_per_currency | Decimal | Points earned per currency unit |
| created_at | ISO DateTime | Creation timestamp |
| updated_at | ISO DateTime | Last update timestamp |

### Brand Fields
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Unique brand identifier |
| company_id | UUID | Parent company ID |
| company_code | String | Parent company code |
| company_name | String | Parent company name |
| code | String | Brand code |
| name | String | Brand name |
| address | String | Brand address |
| phone | String | Contact phone |
| tax_id | String | Tax ID (NPWP) |
| tax_rate | Decimal | Tax rate percentage |
| service_charge | Decimal | Service charge percentage |
| point_expiry_months_override | Integer/Null | Override point expiry |
| point_expiry_months | Integer | Effective point expiry |
| is_active | Boolean | Active status |
| created_at | ISO DateTime | Creation timestamp |
| updated_at | ISO DateTime | Last update timestamp |

### Store Fields
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Unique store identifier |
| brand_id | UUID | Parent brand ID |
| brand_code | String | Parent brand code |
| brand_name | String | Parent brand name |
| company_id | UUID | Parent company ID |
| company_code | String | Parent company code |
| company_name | String | Parent company name |
| store_code | String | Store code |
| store_name | String | Store name |
| address | String | Store address |
| phone | String | Contact phone |
| timezone | String | Store timezone |
| latitude | Decimal/Null | GPS latitude |
| longitude | Decimal/Null | GPS longitude |
| is_active | Boolean | Active status |
| created_at | ISO DateTime | Creation timestamp |
| updated_at | ISO DateTime | Last update timestamp |

---

## 🔒 Security Notes

1. **Authentication Required:** All endpoints require valid authentication token
2. **Active Records Only:** Only active companies, brands, and stores are returned
3. **Read-Only:** These are GET-only endpoints for syncing configuration data
4. **No Sensitive Data:** Password hashes and sensitive fields are excluded from responses

---

## 🐛 Troubleshooting

### 401 Unauthorized
- Check if your authentication token is valid
- Verify the token is included in the `Authorization` header

### 400 Bad Request
- Verify all required query parameters are provided
- Check parameter format (UUID should be valid)

### 404 Not Found
- Ensure the company/brand exists and is active
- Verify the UUID is correct

### 500 Internal Server Error
- Check server logs for detailed error information
- Verify database connectivity

---

## 📚 Related Documentation

- [Sync API Documentation](SYNC_API_DOCUMENTATION.md)
- [API Quick Reference](API_QUICK_REFERENCE.md)
- [Edge Server Implementation](EDGE_SERVER_IMPLEMENTATION.md)

---

## ✅ Implementation Checklist

- [x] Create sync_companies API endpoint
- [x] Create sync_brands API endpoint
- [x] Create sync_stores API endpoint
- [x] Add URL routing
- [x] Update API documentation page
- [x] Add comprehensive examples
- [x] Test API structure
- [ ] Test with live database
- [ ] Test with Postman
- [ ] Update SYNC_API_POSTMAN_COLLECTION.json

---

**Last Updated:** 2026-01-27
**API Version:** v1
**Endpoints Added:** 3
