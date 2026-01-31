# Sync API Documentation for Edge Server

## Overview

The Sync API provides REST endpoints for Edge Servers (POS terminals) to synchronize promotion data, product catalogs, and upload usage logs back to the Head Office (HO) server.

**Base URL:** `/api/sync/`

**Authentication:** All endpoints require authentication using Django REST Framework token or session authentication.

---

## 📡 API Endpoints

### 1. Sync Promotions

Download compiled promotion rules for a specific store.

**Endpoint:** `GET /api/sync/promotions/`

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `store_id` | UUID | ✅ Yes | Store identifier |
| `company_id` | UUID | ✅ Yes | Company identifier |
| `brand_id` | UUID | ❌ No | Filter by specific brand |
| `updated_since` | ISO 8601 | ❌ No | For incremental sync (e.g., `2026-01-27T10:00:00Z`) |

**Response:**

```json
{
  "promotions": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "10% Off All Items",
      "discount_type": "percent",
      "discount_value": 10.00,
      "start_date": "2026-01-20",
      "end_date": "2026-02-05",
      "execution_priority": 10,
      "scope": {
        "apply_to": "all_products",
        "stores": ["all"],
        "categories": [],
        "products": []
      },
      "time_rules": {
        "days_of_week": [1, 2, 3, 4, 5, 6, 7],
        "time_start": null,
        "time_end": null
      },
      "rules": {
        "min_quantity": 1,
        "min_amount": null,
        "max_discount": null
      },
      "limits": {
        "usage_limit_per_transaction": null,
        "usage_limit_per_customer": null,
        "total_usage_limit": 1000
      },
      "targeting": {
        "member_only": false,
        "member_tiers": []
      }
    }
  ],
  "deleted_ids": [],
  "sync_timestamp": "2026-01-27T09:10:42.123456Z",
  "total": 15,
  "total_available": 20,
  "settings": {
    "strategy": "include_future",
    "future_days": 7,
    "past_days": 1,
    "max_promotions": 100
  },
  "store": {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "code": "YGY-001-BSD",
    "name": "Cabang BSD"
  }
}
```

**Error Responses:**

```json
// 400 Bad Request - Missing store_id
{
  "error": "store_id is required",
  "code": "MISSING_STORE_ID"
}

// 404 Not Found - Invalid store
{
  "error": "Store not found",
  "code": "STORE_NOT_FOUND"
}

// 401 Unauthorized
{
  "detail": "Authentication credentials were not provided."
}
```

---

### 2. Sync Categories

Download product categories for catalog display.

**Endpoint:** `GET /api/sync/categories/`

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `company_id` | UUID | ✅ Yes | Company identifier |
| `brand_id` | UUID | ❌ No | Filter by specific brand |
| `updated_since` | ISO 8601 | ❌ No | For incremental sync |

**Response:**

```json
{
  "categories": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440010",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "brand_id": "550e8400-e29b-41d4-a716-446655440001",
      "name": "Main Course",
      "code": "MAIN",
      "parent_id": null,
      "is_active": true,
      "display_order": 1,
      "image_url": "https://example.com/categories/main.jpg",
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-27T09:00:00Z"
    }
  ],
  "deleted_ids": [],
  "sync_timestamp": "2026-01-27T09:10:42.123456Z",
  "total": 10
}
```

---

### 3. Sync Products

Download product catalog with pricing.

**Endpoint:** `GET /api/sync/products/`

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `company_id` | UUID | ✅ Yes | Company identifier |
| `brand_id` | UUID | ✅ Yes | Brand identifier |
| `store_id` | UUID | ❌ No | Filter store-specific products |
| `updated_since` | ISO 8601 | ❌ No | For incremental sync |

**Response:**

```json
{
  "products": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440020",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "brand_id": "550e8400-e29b-41d4-a716-446655440001",
      "store_id": null,
      "category_id": "550e8400-e29b-41d4-a716-446655440010",
      "name": "Nasi Goreng Special",
      "sku": "NGS-001",
      "price": "25000.00",
      "cost": "15000.00",
      "is_active": true,
      "has_modifiers": true,
      "image_url": "https://example.com/products/ngs.jpg",
      "description": "Nasi goreng dengan telur dan ayam",
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-27T09:00:00Z"
    }
  ],
  "deleted_ids": [],
  "sync_timestamp": "2026-01-27T09:10:42.123456Z",
  "total": 50
}
```

---

### 4. Sync Version

Check data version to determine if sync is needed.

**Endpoint:** `GET /api/sync/version/`

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `company_id` | UUID | ✅ Yes | Company identifier |

**Response:**

```json
{
  "version": 1738045842,
  "last_updated": "2026-01-27T09:10:42.123456Z",
  "force_update": false
}
```

**Usage:**
- Edge Server stores last synced version
- Before full sync, check if `version` has changed
- If version unchanged, skip sync to save bandwidth

---

### 5. Upload Usage

Upload promotion usage logs from Edge Server to HO.

**Endpoint:** `POST /api/sync/usage/`

**Request Body:**

```json
{
  "usages": [
    {
      "promotion_id": "550e8400-e29b-41d4-a716-446655440000",
      "bill_id": "B20260127-001",
      "discount_amount": 15000.0,
      "used_at": "2026-01-27T10:30:00Z",
      "store_id": "550e8400-e29b-41d4-a716-446655440001",
      "customer_id": "550e8400-e29b-41d4-a716-446655440002"
    },
    {
      "promotion_id": "550e8400-e29b-41d4-a716-446655440000",
      "bill_id": "B20260127-002",
      "discount_amount": 20000.0,
      "used_at": "2026-01-27T10:35:00Z",
      "store_id": "550e8400-e29b-41d4-a716-446655440001",
      "customer_id": null
    }
  ]
}
```

**Response:**

```json
{
  "created": 2,
  "errors": [],
  "total": 2
}
```

**With Errors:**

```json
{
  "created": 1,
  "errors": [
    {
      "data": {
        "promotion_id": "invalid-id",
        "bill_id": "B20260127-002"
      },
      "error": "Invalid promotion_id"
    }
  ],
  "total": 2
}
```

---

## 🔐 Authentication

All endpoints require authentication. There are two methods:

### Method 1: Token Authentication (Recommended)

1. Obtain token from `/api/token/` endpoint
2. Include in header:

```http
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

### Method 2: Session Authentication

Use Django session cookies (for web browser testing).

---

## 📋 Sync Strategy Settings

Controlled by `PromotionSyncSettings` per company:

### Strategies

1. **`current_only`** - Only promotions valid today
   - Use case: Minimal bandwidth, real-time only

2. **`include_future`** (Default) - Valid today + future promotions
   - Use case: Pre-load upcoming promotions
   - Configurable: `future_days` (default: 7) and `past_days` (default: 1)

3. **`all_active`** - All active promotions regardless of dates
   - Use case: Maximum availability, higher bandwidth

### Additional Settings

- **`max_promotions_per_sync`**: Limit response size (default: 100)
- **`include_inactive`**: Include inactive promotions (default: false)
- **`auto_sync_enabled`**: Enable automatic periodic sync (default: true)
- **`sync_interval_hours`**: Hours between auto-sync (default: 6)
- **`enable_compression`**: Enable gzip compression (default: true)

---

## 🔄 Recommended Sync Flow

### Initial Sync (First Time)

```
1. GET /api/sync/version/?company_id={id}
2. GET /api/sync/categories/?company_id={id}&brand_id={id}
3. GET /api/sync/products/?company_id={id}&brand_id={id}
4. GET /api/sync/promotions/?store_id={id}&company_id={id}
5. Store all data locally + version number
```

### Incremental Sync (Periodic)

```
1. GET /api/sync/version/?company_id={id}
2. If version changed:
   a. GET /api/sync/promotions/?store_id={id}&company_id={id}&updated_since={last_sync}
   b. Merge with local data
   c. Update version number
3. If version unchanged: Skip sync
```

### Usage Upload (After Each Transaction)

```
1. Queue usage logs locally
2. POST /api/sync/usage/ (batch upload every 5 minutes)
3. Retry on failure with exponential backoff
```

---

## 🧪 Testing Endpoints

### Using cURL

```bash
# Get token (if using token auth)
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'

# Sync promotions
curl -X GET "http://localhost:8000/api/sync/promotions/?store_id=550e8400-e29b-41d4-a716-446655440001&company_id=550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Token YOUR_TOKEN_HERE"

# Upload usage
curl -X POST http://localhost:8000/api/sync/usage/ \
  -H "Authorization: Token YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "usages": [
      {
        "promotion_id": "550e8400-e29b-41d4-a716-446655440000",
        "bill_id": "B001",
        "discount_amount": 15000.0,
        "used_at": "2026-01-27T10:00:00Z",
        "store_id": "550e8400-e29b-41d4-a716-446655440001"
      }
    ]
  }'
```

### Using Python Requests

```python
import requests

BASE_URL = "http://localhost:8000"
TOKEN = "your_token_here"

headers = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json"
}

# Sync promotions
response = requests.get(
    f"{BASE_URL}/api/sync/promotions/",
    params={
        "store_id": "550e8400-e29b-41d4-a716-446655440001",
        "company_id": "550e8400-e29b-41d4-a716-446655440000"
    },
    headers=headers
)

promotions = response.json()
print(f"Total promotions: {promotions['total']}")
```

---

## ⚡ Performance Considerations

### Bandwidth Optimization

1. **Use incremental sync** with `updated_since` parameter
2. **Enable compression** in sync settings
3. **Adjust `max_promotions_per_sync`** based on network speed
4. **Use version checking** before full sync

### Edge Server Storage

- Store all synced data in local SQLite database
- Index by `store_id`, `category_id`, `product_id`
- Keep compiled JSON for fast POS engine processing

### Error Handling

- Implement retry logic with exponential backoff
- Queue failed requests for later upload
- Log all sync errors for debugging

---

## 📊 Monitoring & Analytics

Track these metrics on HO:

1. **Sync frequency per store**
2. **Sync duration and bandwidth usage**
3. **Failed sync attempts**
4. **Promotion usage upload lag**
5. **Data version staleness per store**

---

## 🔒 Security Best Practices

1. **Use HTTPS** in production
2. **Rotate tokens** regularly
3. **Rate limit** sync endpoints
4. **Validate all UUIDs** before queries
5. **Log all sync requests** for audit trail

---

## 📝 Notes

- All datetime fields use ISO 8601 format with timezone
- All UUIDs are lowercase with hyphens
- Decimal fields (prices, amounts) use string format for precision
- Empty arrays are valid for optional list fields

---

## 🆘 Troubleshooting

### Problem: "Store not found" error
**Solution:** Verify `store_id` and `company_id` match in database

### Problem: No promotions returned
**Solution:** Check sync strategy settings and promotion date ranges

### Problem: Authentication failed
**Solution:** Verify token is valid and included in Authorization header

### Problem: Slow sync performance
**Solution:** Reduce `max_promotions_per_sync` or enable compression

---

## 📞 Support

For API support, contact:
- Development Team: dev@yogyagroup.com
- Documentation: Check `/api/sync/docs/` endpoint
