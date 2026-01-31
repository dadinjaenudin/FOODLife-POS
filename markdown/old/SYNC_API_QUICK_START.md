# Sync API Quick Start Guide

Quick reference untuk testing dan menggunakan Sync API.

---

## 🚀 Quick Setup (5 Minutes)

### 1. Start Server
```bash
# Development
python manage.py runserver

# Or with Docker
docker-compose up
```

### 2. Create Test Data
```bash
# Create admin user
python manage.py createsuperuser

# Create sample data
python manage.py generate_sample_data

# Create test promotions
python create_promotion_samples.py
```

### 3. Get Authentication Token
```bash
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'
```

Response:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Save the `access` token** for subsequent requests.

---

## 📡 Test All Endpoints (Copy-Paste Ready)

### Setup Variables
```bash
# Replace these with your actual values
export TOKEN="your_jwt_token_here"
export BASE_URL="http://localhost:8000"
export COMPANY_ID="your-company-uuid"
export BRAND_ID="your-brand-uuid"
export STORE_ID="your-store-uuid"
```

### 1. Check Version (Fastest Test)
```bash
curl -X GET "$BASE_URL/api/sync/version/?company_id=$COMPANY_ID" \
  -H "Authorization: Bearer $TOKEN" | jq
```

Expected:
```json
{
  "version": 1738045842,
  "last_updated": "2026-01-27T09:10:42.123456Z",
  "force_update": false
}
```

### 2. Sync Promotions (Main Endpoint)
```bash
curl -X GET "$BASE_URL/api/sync/promotions/?store_id=$STORE_ID&company_id=$COMPANY_ID" \
  -H "Authorization: Bearer $TOKEN" | jq
```

Expected:
```json
{
  "promotions": [...],
  "total": 15,
  "sync_timestamp": "2026-01-27T09:10:42Z",
  "settings": {
    "strategy": "include_future",
    "future_days": 7,
    "past_days": 1
  }
}
```

### 3. Sync Categories
```bash
curl -X GET "$BASE_URL/api/sync/categories/?company_id=$COMPANY_ID" \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 4. Sync Products
```bash
curl -X GET "$BASE_URL/api/sync/products/?company_id=$COMPANY_ID&brand_id=$BRAND_ID" \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 5. Upload Usage
```bash
curl -X POST "$BASE_URL/api/sync/usage/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "usages": [
      {
        "promotion_id": "550e8400-e29b-41d4-a716-446655440000",
        "bill_id": "B001",
        "discount_amount": 15000.0,
        "used_at": "2026-01-27T10:00:00Z",
        "store_id": "'$STORE_ID'"
      }
    ]
  }' | jq
```

Expected:
```json
{
  "created": 1,
  "errors": [],
  "total": 1
}
```

---

## 🔍 Common Issues & Solutions

### ❌ "Authentication credentials were not provided"
**Problem:** Missing or invalid token

**Solution:**
```bash
# Get new token
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'

# Use Bearer (not Token) with JWT
-H "Authorization: Bearer YOUR_TOKEN"
```

### ❌ "Store not found"
**Problem:** Invalid store_id or company_id

**Solution:**
```bash
# Get valid IDs from Django shell
python manage.py shell
>>> from core.models import Company, Brand, Store
>>> company = Company.objects.first()
>>> print(f"Company: {company.id}")
>>> store = Store.objects.first()
>>> print(f"Store: {store.id}")
```

### ❌ Empty promotions array
**Problem:** No promotions match the sync criteria

**Solution:**
```bash
# Check sync settings
python manage.py shell
>>> from promotions.models_settings import PromotionSyncSettings
>>> from core.models import Company
>>> company = Company.objects.first()
>>> settings = PromotionSyncSettings.get_for_company(company)
>>> print(f"Strategy: {settings.sync_strategy}")
>>> print(f"Future days: {settings.future_days}")

# Create test promotions
python create_promotion_samples.py
```

---

## 🧪 Testing Scenarios

### Test 1: Current Only Strategy
```bash
# Set strategy to current_only via Django Admin or shell
python manage.py shell
>>> from promotions.models_settings import PromotionSyncSettings
>>> from core.models import Company
>>> settings = PromotionSyncSettings.objects.get(company=Company.objects.first())
>>> settings.sync_strategy = 'current_only'
>>> settings.save()

# Sync - should only get promotions valid TODAY
curl -X GET "$BASE_URL/api/sync/promotions/?store_id=$STORE_ID&company_id=$COMPANY_ID" \
  -H "Authorization: Bearer $TOKEN" | jq '.promotions[] | .name'
```

### Test 2: Incremental Sync
```bash
# First sync - get all
curl -X GET "$BASE_URL/api/sync/promotions/?store_id=$STORE_ID&company_id=$COMPANY_ID" \
  -H "Authorization: Bearer $TOKEN" | jq '.sync_timestamp'

# Save timestamp: 2026-01-27T09:10:42Z

# Update a promotion via Django Admin

# Second sync - only get updated
curl -X GET "$BASE_URL/api/sync/promotions/?store_id=$STORE_ID&company_id=$COMPANY_ID&updated_since=2026-01-27T09:10:42Z" \
  -H "Authorization: Bearer $TOKEN" | jq '.total'
```

### Test 3: Max Limit
```bash
# Set low limit
python manage.py shell
>>> from promotions.models_settings import PromotionSyncSettings
>>> settings = PromotionSyncSettings.objects.first()
>>> settings.max_promotions_per_sync = 5
>>> settings.save()

# Sync - should only get 5 promotions
curl -X GET "$BASE_URL/api/sync/promotions/?store_id=$STORE_ID&company_id=$COMPANY_ID" \
  -H "Authorization: Bearer $TOKEN" | jq '.total, .total_available'
```

---

## 📱 Postman Quick Import

1. **Import Collection:**
   - Open Postman
   - Click Import
   - Select `SYNC_API_POSTMAN_COLLECTION.json`

2. **Set Environment Variables:**
   - Create new environment "Sync API Dev"
   - Add variables:
     ```
     base_url = http://localhost:8000
     token = (get from /api/token/)
     company_id = (get from Django admin)
     brand_id = (get from Django admin)
     store_id = (get from Django admin)
     ```

3. **Run Collection:**
   - Click "Run Collection"
   - Select all requests
   - Run

---

## 🐍 Python Client Example

```python
import requests
from datetime import datetime

class SyncAPIClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.token = self._get_token(username, password)
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
    
    def _get_token(self, username, password):
        response = requests.post(
            f'{self.base_url}/api/token/',
            json={'username': username, 'password': password}
        )
        return response.json()['access']
    
    def check_version(self, company_id):
        response = requests.get(
            f'{self.base_url}/api/sync/version/',
            params={'company_id': company_id},
            headers=self.headers
        )
        return response.json()
    
    def sync_promotions(self, store_id, company_id, updated_since=None):
        params = {
            'store_id': store_id,
            'company_id': company_id
        }
        if updated_since:
            params['updated_since'] = updated_since
        
        response = requests.get(
            f'{self.base_url}/api/sync/promotions/',
            params=params,
            headers=self.headers
        )
        return response.json()
    
    def upload_usage(self, usages):
        response = requests.post(
            f'{self.base_url}/api/sync/usage/',
            json={'usages': usages},
            headers=self.headers
        )
        return response.json()

# Usage
client = SyncAPIClient('http://localhost:8000', 'admin', 'admin')

# Check version
version = client.check_version('company-uuid')
print(f"Current version: {version['version']}")

# Sync promotions
promotions = client.sync_promotions('store-uuid', 'company-uuid')
print(f"Downloaded {promotions['total']} promotions")

# Upload usage
result = client.upload_usage([
    {
        'promotion_id': 'promo-uuid',
        'bill_id': 'B001',
        'discount_amount': 15000.0,
        'used_at': datetime.now().isoformat(),
        'store_id': 'store-uuid'
    }
])
print(f"Uploaded {result['created']} usage records")
```

---

## 🎯 One-Liner Tests

```bash
# Test all endpoints in sequence
TOKEN=$(curl -s -X POST http://localhost:8000/api/token/ -H "Content-Type: application/json" -d '{"username":"admin","password":"admin"}' | jq -r '.access') && \
echo "Token: $TOKEN" && \
curl -s -X GET "http://localhost:8000/api/sync/version/?company_id=$COMPANY_ID" -H "Authorization: Bearer $TOKEN" | jq '.version' && \
echo "✅ Version check passed" && \
curl -s -X GET "http://localhost:8000/api/sync/promotions/?store_id=$STORE_ID&company_id=$COMPANY_ID" -H "Authorization: Bearer $TOKEN" | jq '.total' && \
echo "✅ Promotion sync passed"
```

---

## 📊 Expected Response Times

| Endpoint | Response Time | Size |
|----------|--------------|------|
| `/version/` | < 50ms | < 1KB |
| `/categories/` | < 200ms | ~10KB |
| `/products/` | < 500ms | ~100KB |
| `/promotions/` | < 1s | ~50KB |
| `/usage/` (POST) | < 300ms | ~5KB |

If response time > 2x expected, check:
- Database indexes
- Number of promotions
- Network latency

---

## 🔗 Quick Links

- **Full API Docs:** `SYNC_API_DOCUMENTATION.md`
- **Implementation Summary:** `SYNC_API_IMPLEMENTATION_SUMMARY.md`
- **Postman Collection:** `SYNC_API_POSTMAN_COLLECTION.json`
- **Test Suite:** `promotions/tests/test_sync_api.py`

---

## 💡 Pro Tips

1. **Always check version first** - Saves bandwidth
2. **Use incremental sync** - Only sync changes
3. **Batch usage uploads** - Upload every 5 minutes, not per transaction
4. **Store locally** - Edge Server should cache everything
5. **Handle failures gracefully** - Queue for retry on network issues

---

## ✅ Quick Health Check

Run this to verify all endpoints are working:

```bash
#!/bin/bash
# save as test_sync_api.sh

BASE_URL="http://localhost:8000"
USERNAME="admin"
PASSWORD="admin"

echo "🚀 Sync API Health Check"
echo "========================"

# Get token
echo -n "1. Getting token... "
TOKEN=$(curl -s -X POST $BASE_URL/api/token/ \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" | jq -r '.access')

if [ "$TOKEN" != "null" ]; then
  echo "✅"
else
  echo "❌ Failed to get token"
  exit 1
fi

# Get company/store IDs
COMPANY_ID=$(curl -s -X GET "$BASE_URL/api/v1/core/companies/" -H "Authorization: Bearer $TOKEN" | jq -r '.results[0].id')
STORE_ID=$(curl -s -X GET "$BASE_URL/api/v1/core/stores/" -H "Authorization: Bearer $TOKEN" | jq -r '.results[0].id')

# Test version
echo -n "2. Testing version endpoint... "
VERSION=$(curl -s -X GET "$BASE_URL/api/sync/version/?company_id=$COMPANY_ID" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.version')

if [ "$VERSION" != "null" ]; then
  echo "✅ (version: $VERSION)"
else
  echo "❌"
fi

# Test promotions
echo -n "3. Testing promotions endpoint... "
PROMO_COUNT=$(curl -s -X GET "$BASE_URL/api/sync/promotions/?store_id=$STORE_ID&company_id=$COMPANY_ID" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.total')

if [ "$PROMO_COUNT" != "null" ]; then
  echo "✅ ($PROMO_COUNT promotions)"
else
  echo "❌"
fi

echo ""
echo "🎉 Health check complete!"
```

---

**Need Help?** Check full documentation in `SYNC_API_DOCUMENTATION.md`
