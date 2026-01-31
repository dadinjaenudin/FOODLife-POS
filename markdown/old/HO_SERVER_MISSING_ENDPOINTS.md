# 🚨 HO Server - Missing Sync Endpoints

## Problem
Edge Server mencoba memanggil endpoint-endpoint sync berikut di HO Server (port 8002), tetapi endpoint tersebut **belum ada atau error**:

## ❌ Missing/Error Endpoints di HO Server:

| Endpoint | Status | Issue |
|----------|--------|-------|
| `/api/sync/categories/` | ❌ 500 Error | Server error - mungkin ada tapi broken |
| `/api/sync/products/` | ❌ 400 Error | Bad request - mungkin parameter salah |
| `/api/sync/modifiers/` | ❌ 404 Not Found | Endpoint tidak ada |
| `/api/sync/stores/` | ⚠️ 400 Error | Mungkin parameter issue |

## ✅ Existing Endpoints di HO Server:

| Endpoint | Status | Notes |
|----------|--------|-------|
| `/api/sync/companies/` | ✅ Working | Returns companies |
| `/api/sync/brands/` | ✅ Working | Returns brands per company |

---

## 📋 What Was Done on Edge Server (Port 8001):

Saya sudah membuat endpoint-endpoint ini di **Edge Server** untuk testing:

### Files Changed:
- ✅ `apps/core/views_sync.py` - Added 3 new endpoints
- ✅ `apps/core/urls.py` - Added URL routes

### Endpoints Created on Edge Server:
1. ✅ `GET /api/sync/categories/?company_id={uuid}`
2. ✅ `GET /api/sync/products/?company_id={uuid}`
3. ✅ `GET /api/sync/modifiers/?company_id={uuid}`

**These work on Edge Server (8001) but are NOT available on HO Server (8002)!**

---

## 🎯 Solution Required:

### Option 1: Copy Implementation to HO Server ✅ **RECOMMENDED**
**Copy the same endpoint implementations** from Edge Server to HO Server:

1. Copy the endpoint functions from Edge `apps/core/views_sync.py`:
   - `sync_categories()`
   - `sync_products()`
   - `sync_modifiers()`

2. Add URL routes in HO Server `apps/core/urls.py`

3. Restart HO Server

### Option 2: Fix Existing Broken Endpoints
If HO Server already has these endpoints but they're broken:
- Fix the 500 error on `/api/sync/categories/`
- Fix the 400 error on `/api/sync/products/`
- Create `/api/sync/modifiers/` if missing

---

## 🔄 Current Setup Flow Issue:

When Edge Server runs **"Setup & Sync All Data"** (`/setup/`), it calls:

```python
# From apps/core/views_setup.py line 206-209
sync_results = sync_master_data_from_ho(company_id, access_token)
```

Which internally calls:
```python
# From apps/core/sync_helpers.py
GET {HO_API_URL}/api/sync/categories/  # ❌ 500 Error on HO
GET {HO_API_URL}/api/sync/products/    # ❌ 400 Error on HO
GET {HO_API_URL}/api/sync/modifiers/   # ❌ 404 on HO
```

**All these calls fail because HO Server doesn't have working endpoints!**

---

## 📊 Test Results:

### HO Server (Port 8002):
```bash
✓ /api/sync/companies/           # Working
✓ /api/sync/brands/              # Working
✗ /api/sync/categories/          # 500 Error
✗ /api/sync/products/            # 400 Error
✗ /api/sync/modifiers/           # 404 Not Found
```

### Edge Server (Port 8001):
```bash
✓ /api/sync/companies/           # Working (newly created)
✓ /api/sync/brands/              # Working (newly created)
✓ /api/sync/categories/          # Working (newly created)
✓ /api/sync/products/            # Working (newly created)
✓ /api/sync/modifiers/           # Working (newly created)
```

---

## 🚀 Next Steps:

1. **Access HO Server codebase** (running on port 8002)
2. **Copy endpoint implementations** from Edge Server to HO Server
3. **Restart HO Server**
4. **Test sync flow** from Edge Server `/setup/`

---

## 📝 Notes:

- Edge Server implementation is **complete and working** ✅
- HO Server needs the same endpoints to serve data to Edge Servers
- Both servers likely use the same Django codebase but different databases
- Edge Server DB: `fnb_edge_db`
- HO Server DB: (need to check)
