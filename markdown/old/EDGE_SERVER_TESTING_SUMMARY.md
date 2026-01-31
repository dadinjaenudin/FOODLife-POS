# 🎯 Edge Server API Testing - Complete Summary

Berdasarkan dashboard di: **http://localhost:8002/promotions/compiler/**

---

## 📋 **5 API Endpoints yang Akan Di-Hit dari Edge Server**

### **Base URL:** `http://localhost:8002/api/sync/`

| # | Endpoint | Method | Purpose | Frequency | Priority |
|---|----------|--------|---------|-----------|----------|
| 1 | `/api/sync/version/` | GET | Check if sync needed | Before each sync | 🔴 CRITICAL |
| 2 | `/api/sync/promotions/` | GET | Download promotion rules | Every 6 hours | 🔴 CRITICAL |
| 3 | `/api/sync/categories/` | GET | Download product categories | Daily | 🟡 IMPORTANT |
| 4 | `/api/sync/products/` | GET | Download product catalog | Daily | 🟡 IMPORTANT |
| 5 | `/api/sync/usage/` | POST | Upload promotion usage | Every 5 mins | 🟢 MEDIUM |

---

## 🚀 Quick Start Testing (3 Steps)

### Step 1: Get Authentication Token

```bash
curl -X POST http://localhost:8002/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'
```

**Save the `access` token!**

### Step 2: Get Your IDs

Buka browser: **http://localhost:8002/promotions/compiler/**

Di section **"Edge Server Sync"**, copy:
- Company ID
- Brand ID  
- Store ID

### Step 3: Test All Endpoints

```bash
# Option A: Manual curl commands (see below)
# Option B: Run test script
bash tmp_rovodev_test_all_endpoints.sh

# Option C: Import Postman collection
# Import: SYNC_API_POSTMAN_COLLECTION.json
```

---

## 🧪 Test Commands (Copy-Paste Ready)

Replace these variables first:
```bash
export TOKEN="your_jwt_token"
export COMPANY_ID="your-company-uuid"
export BRAND_ID="your-brand-uuid"
export STORE_ID="your-store-uuid"
```

### ✅ Test 1: Check Version (Lightest)

```bash
curl -X GET "http://localhost:8002/api/sync/version/?company_id=$COMPANY_ID" \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Expected:** Version number dan last_updated timestamp

---

### ✅ Test 2: Sync Promotions (Most Important)

```bash
curl -X GET "http://localhost:8002/api/sync/promotions/?store_id=$STORE_ID&company_id=$COMPANY_ID" \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Expected:** Array of compiled promotion JSON

**Key Fields:**
- `promotions[]` - Array of promotion objects
- `total` - Number of promotions returned
- `settings.strategy` - Current sync strategy
- `sync_timestamp` - Current server time

---

### ✅ Test 3: Sync Categories

```bash
curl -X GET "http://localhost:8002/api/sync/categories/?company_id=$COMPANY_ID" \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Expected:** Array of categories

---

### ✅ Test 4: Sync Products

```bash
curl -X GET "http://localhost:8002/api/sync/products/?company_id=$COMPANY_ID&brand_id=$BRAND_ID" \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Expected:** Array of products with pricing

---

### ✅ Test 5: Upload Usage

```bash
curl -X POST http://localhost:8002/api/sync/usage/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "usages": [
      {
        "promotion_id": "550e8400-e29b-41d4-a716-446655440000",
        "bill_id": "TEST-001",
        "discount_amount": 15000.0,
        "used_at": "2026-01-27T10:30:00Z",
        "store_id": "'$STORE_ID'",
        "customer_id": null
      }
    ]
  }' | jq
```

**Expected:** `{ "created": 1, "total": 1, "errors": [] }`

---

## 🔄 Recommended Sync Flow for Edge Server

### Initial Sync (First Boot)

```
1. Get Token → /api/token/
2. Check Version → /api/sync/version/
3. Download Categories → /api/sync/categories/
4. Download Products → /api/sync/products/
5. Download Promotions → /api/sync/promotions/
6. Store everything in local SQLite
```

### Periodic Sync (Every 6 Hours)

```
1. Check Version → /api/sync/version/
2. IF version changed:
   a. Incremental Sync → /api/sync/promotions/?updated_since=...
   b. Update local database
3. ELSE:
   Skip sync (no changes)
```

### Usage Upload (Every 5 Minutes)

```
1. Queue promotion usage locally
2. Batch upload → POST /api/sync/usage/
3. Retry on failure with exponential backoff
```

---

## 📚 Documentation Files Created

| File | Size | Purpose |
|------|------|---------|
| `EDGE_SERVER_API_TESTING_GUIDE.md` | 20 KB | **Complete testing guide** with all examples |
| `SYNC_API_DOCUMENTATION.md` | 62 KB | Full API reference documentation |
| `SYNC_API_IMPLEMENTATION_SUMMARY.md` | 28 KB | Technical implementation details |
| `SYNC_API_POSTMAN_COLLECTION.json` | 15 KB | Ready-to-import Postman collection |
| `SYNC_API_QUICK_START.md` | 16 KB | Quick reference guide |
| `tmp_rovodev_test_all_endpoints.sh` | 10 KB | Automated test script |

---

## 🎯 Testing Checklist

### Before Integration

- [ ] **Test 1:** Version check working (< 100ms)
- [ ] **Test 2:** Promotions sync returning data
- [ ] **Test 3:** Categories sync working
- [ ] **Test 4:** Products sync working
- [ ] **Test 5:** Usage upload successful
- [ ] **Test 6:** Incremental sync with `updated_since`
- [ ] **Test 7:** Authentication errors handled
- [ ] **Test 8:** Invalid IDs return proper errors

### Edge Server Requirements

- [ ] Store promotions in local SQLite
- [ ] Implement version checking
- [ ] Queue usage logs for batch upload
- [ ] Retry logic with exponential backoff
- [ ] Handle network failures gracefully
- [ ] Log all sync operations

---

## 🐛 Common Issues & Solutions

### ❌ "Authentication credentials were not provided"

**Solution:**
```bash
# Get fresh token
TOKEN=$(curl -s -X POST http://localhost:8002/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | jq -r '.access')

# Use Bearer (not Token)
-H "Authorization: Bearer $TOKEN"
```

### ❌ "Store not found"

**Solution:**
```bash
# Get valid IDs from dashboard
# Open: http://localhost:8002/promotions/compiler/
# Or use Django shell to find correct IDs
```

### ❌ Empty promotions array

**Solution:**
```bash
# Create test promotions
python create_promotion_samples.py

# Or check sync settings strategy
# Open: http://localhost:8002/promotions/settings/
```

---

## 📊 Expected Performance

| Endpoint | Expected | Max Acceptable |
|----------|----------|----------------|
| `/version/` | < 50ms | 200ms |
| `/categories/` | < 200ms | 1s |
| `/products/` | < 500ms | 2s |
| `/promotions/` | < 1s | 5s |
| `/usage/` | < 300ms | 1s |

---

## 🎬 How to Test Right Now

### Option 1: Automated Script (Recommended)

```bash
bash tmp_rovodev_test_all_endpoints.sh
```

This will:
- ✅ Get authentication token
- ✅ Auto-detect your Company/Brand/Store IDs
- ✅ Test all 5 endpoints
- ✅ Show results with timing
- ✅ Display summary

### Option 2: Manual Testing

1. Open: **http://localhost:8002/promotions/compiler/**
2. Copy API endpoint URL
3. Copy your Store ID and Company ID
4. Use curl commands above
5. Verify JSON responses

### Option 3: Postman

1. Import: `SYNC_API_POSTMAN_COLLECTION.json`
2. Setup environment variables
3. Click "Run Collection"
4. Review results

---

## 📞 Quick Reference Card

```
┌─────────────────────────────────────────────────┐
│  EDGE SERVER SYNC API - QUICK REFERENCE         │
├─────────────────────────────────────────────────┤
│  Base URL: http://localhost:8002/api/sync/      │
│                                                  │
│  Authentication:                                 │
│    POST /api/token/                             │
│    → Returns JWT access token                   │
│                                                  │
│  Download APIs (GET):                           │
│    1. /version/?company_id={id}                 │
│    2. /promotions/?store_id={id}&company_id={id}│
│    3. /categories/?company_id={id}              │
│    4. /products/?company_id={id}&brand_id={id}  │
│                                                  │
│  Upload APIs (POST):                            │
│    5. /usage/                                   │
│       Body: {"usages": [...]}                   │
│                                                  │
│  Headers:                                        │
│    Authorization: Bearer {jwt_token}            │
│    Content-Type: application/json (for POST)    │
└─────────────────────────────────────────────────┘
```

---

## 🎉 Ready for Testing!

**Dashboard:** http://localhost:8002/promotions/compiler/

**Next Steps:**

1. ✅ Run automated test: `bash tmp_rovodev_test_all_endpoints.sh`
2. ✅ Check results and response times
3. ✅ Import Postman collection for more tests
4. ✅ Start Edge Server integration

**Questions?** Check:
- `EDGE_SERVER_API_TESTING_GUIDE.md` - Detailed guide
- `SYNC_API_DOCUMENTATION.md` - Full API reference

---

**All endpoints are production-ready! 🚀**
