# Master Data API - Quick Test Guide

## 🚀 Quick Start

### Step 1: Get Authentication Token

```bash
curl -X POST "http://localhost:8002/api/token/" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'
```

Save the token from response:
```bash
TOKEN="your_token_here"
```

---

## 📋 Test Each Endpoint

### Test 1: Get All Companies

```bash
curl -X GET "http://localhost:8002/api/sync/companies/" \
  -H "Authorization: Token $TOKEN" | jq
```

**Expected Response:**
```json
{
  "companies": [...],
  "total": N,
  "sync_timestamp": "..."
}
```

**Save a company_id for next test:**
```bash
COMPANY_ID="uuid-from-response"
```

---

### Test 2: Get Brands by Company

```bash
curl -X GET "http://localhost:8002/api/sync/brands/?company_id=$COMPANY_ID" \
  -H "Authorization: Token $TOKEN" | jq
```

**Expected Response:**
```json
{
  "brands": [...],
  "total": N,
  "company": {...},
  "sync_timestamp": "..."
}
```

**Test Error Case (missing parameter):**
```bash
curl -X GET "http://localhost:8002/api/sync/brands/" \
  -H "Authorization: Token $TOKEN" | jq
```

**Expected:** `400 Bad Request` with error message

**Save a brand_id for next test:**
```bash
BRAND_ID="uuid-from-response"
```

---

### Test 3: Get Stores by Brand

```bash
curl -X GET "http://localhost:8002/api/sync/stores/?brand_id=$BRAND_ID" \
  -H "Authorization: Token $TOKEN" | jq
```

**Expected Response:**
```json
{
  "stores": [...],
  "total": N,
  "brand": {...},
  "sync_timestamp": "..."
}
```

**Test Error Case (missing parameter):**
```bash
curl -X GET "http://localhost:8002/api/sync/stores/" \
  -H "Authorization: Token $TOKEN" | jq
```

**Expected:** `400 Bad Request` with error message

---

## 🧪 Full Flow Test Script

Save this as `test_master_data_apis.sh`:

```bash
#!/bin/bash

BASE_URL="http://localhost:8002"

echo "=========================================="
echo "Master Data API Test"
echo "=========================================="

# Step 1: Login
echo -e "\n1. Getting authentication token..."
TOKEN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/token/" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}')

TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.token // .access')
echo "Token: ${TOKEN:0:20}..."

# Step 2: Get Companies
echo -e "\n2. Getting companies..."
COMPANIES=$(curl -s -X GET "$BASE_URL/api/sync/companies/" \
  -H "Authorization: Token $TOKEN")

echo "Companies response:"
echo $COMPANIES | jq '.companies[0] | {id, code, name}'

COMPANY_ID=$(echo $COMPANIES | jq -r '.companies[0].id')
echo "Selected Company ID: $COMPANY_ID"

# Step 3: Get Brands
echo -e "\n3. Getting brands for company..."
BRANDS=$(curl -s -X GET "$BASE_URL/api/sync/brands/?company_id=$COMPANY_ID" \
  -H "Authorization: Token $TOKEN")

echo "Brands response:"
echo $BRANDS | jq '.brands[0] | {id, code, name, company_name}'

BRAND_ID=$(echo $BRANDS | jq -r '.brands[0].id')
echo "Selected Brand ID: $BRAND_ID"

# Step 4: Get Stores
echo -e "\n4. Getting stores for brand..."
STORES=$(curl -s -X GET "$BASE_URL/api/sync/stores/?brand_id=$BRAND_ID" \
  -H "Authorization: Token $TOKEN")

echo "Stores response:"
echo $STORES | jq '.stores[0] | {id, store_code, store_name, brand_name, company_name}'

STORE_ID=$(echo $STORES | jq -r '.stores[0].id')
echo "Selected Store ID: $STORE_ID"

# Summary
echo -e "\n=========================================="
echo "Test Complete!"
echo "=========================================="
echo "Hierarchy:"
echo "  Company: $(echo $COMPANIES | jq -r '.companies[0].name')"
echo "  Brand:   $(echo $BRANDS | jq -r '.brands[0].name')"
echo "  Store:   $(echo $STORES | jq -r '.stores[0].store_name')"
echo "=========================================="
```

**Run:**
```bash
chmod +x test_master_data_apis.sh
./test_master_data_apis.sh
```

---

## 🐍 Python Test Script

Save this as `test_master_data_apis.py`:

```python
import requests
import json

BASE_URL = "http://localhost:8002"

def test_master_data_apis():
    print("=" * 50)
    print("Master Data API Test")
    print("=" * 50)
    
    # Step 1: Login
    print("\n1. Getting authentication token...")
    response = requests.post(
        f"{BASE_URL}/api/token/",
        json={"username": "admin", "password": "admin"}
    )
    token = response.json().get('token') or response.json().get('access')
    headers = {"Authorization": f"Token {token}"}
    print(f"Token: {token[:20]}...")
    
    # Step 2: Get Companies
    print("\n2. Getting companies...")
    response = requests.get(f"{BASE_URL}/api/sync/companies/", headers=headers)
    companies = response.json()
    print(f"Found {companies['total']} companies")
    print(f"First company: {companies['companies'][0]['name']}")
    company_id = companies['companies'][0]['id']
    
    # Step 3: Get Brands
    print("\n3. Getting brands...")
    response = requests.get(
        f"{BASE_URL}/api/sync/brands/",
        headers=headers,
        params={"company_id": company_id}
    )
    brands = response.json()
    print(f"Found {brands['total']} brands")
    print(f"First brand: {brands['brands'][0]['name']}")
    brand_id = brands['brands'][0]['id']
    
    # Step 4: Get Stores
    print("\n4. Getting stores...")
    response = requests.get(
        f"{BASE_URL}/api/sync/stores/",
        headers=headers,
        params={"brand_id": brand_id}
    )
    stores = response.json()
    print(f"Found {stores['total']} stores")
    print(f"First store: {stores['stores'][0]['store_name']}")
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Complete!")
    print("=" * 50)
    print(f"Hierarchy:")
    print(f"  Company: {companies['companies'][0]['name']}")
    print(f"  Brand:   {brands['brands'][0]['name']}")
    print(f"  Store:   {stores['stores'][0]['store_name']}")
    print("=" * 50)

if __name__ == "__main__":
    test_master_data_apis()
```

**Run:**
```bash
python test_master_data_apis.py
```

---

## ✅ Test Checklist

### Basic Tests
- [ ] GET /api/sync/companies/ returns 200 OK
- [ ] Response has companies array
- [ ] Response has total count
- [ ] Response has sync_timestamp

### Brands Tests
- [ ] GET /api/sync/brands/?company_id={uuid} returns 200 OK
- [ ] Response includes company info
- [ ] Response has brands array with company details
- [ ] Missing company_id returns 400 Bad Request
- [ ] Invalid company_id returns 404 Not Found

### Stores Tests
- [ ] GET /api/sync/stores/?brand_id={uuid} returns 200 OK
- [ ] Response includes brand and company info
- [ ] Response has stores array with full hierarchy
- [ ] Missing brand_id returns 400 Bad Request
- [ ] Invalid brand_id returns 404 Not Found

### Performance Tests
- [ ] Check query count (should use select_related)
- [ ] Response time < 500ms for normal datasets
- [ ] Handles large datasets gracefully

### Security Tests
- [ ] Requires authentication token
- [ ] Invalid token returns 401 Unauthorized
- [ ] Only returns active records

---

## 🔍 Troubleshooting

### Error: "could not translate host name 'db'"
**Solution:** Start Docker containers
```bash
cd FoodBeverages-CMS
docker-compose up -d
```

### Error: 401 Unauthorized
**Solution:** Check token validity
```bash
# Get new token
curl -X POST "http://localhost:8002/api/token/" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'
```

### Error: No companies found
**Solution:** Create sample data
```bash
python manage.py generate_sample_data
```

---

## 📊 Expected Data Structure

### Companies
```
Company: Yogya Group (YGY)
├─ point_expiry_months: 12
├─ points_per_currency: 1.00
└─ timezone: Asia/Jakarta
```

### Brands
```
Brand: Ayam Geprek Express (YGY-001)
├─ Company: Yogya Group
├─ tax_rate: 11.00
├─ service_charge: 5.00
└─ point_expiry_months: 12 (inherited or override)
```

### Stores
```
Store: Cabang BSD (YGY-001-BSD)
├─ Brand: Ayam Geprek Express
├─ Company: Yogya Group
├─ location: -6.302100, 106.652900
└─ timezone: Asia/Jakarta
```

---

## 🎯 Quick URLs

- **API Documentation:** http://localhost:8002/promotions/compiler/api-docs/
- **Django Admin:** http://localhost:8002/admin/
- **Compiler Dashboard:** http://localhost:8002/promotions/compiler/

---

**Ready to test?** Start your Django server and run the test scripts above!
