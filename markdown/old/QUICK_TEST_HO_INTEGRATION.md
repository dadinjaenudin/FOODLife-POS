# Quick Test - HO Integration dengan Token Auth

## ✅ Fitur Baru: Token Authentication

Proxy endpoints sekarang menggunakan **JWT Token Authentication** untuk fetch data dari HO Server.

## 🚀 Quick Start Testing

### Step 1: Start HO Server (Terminal 1)

```bash
cd pos-django-htmx-main
python manage.py runserver 8002
```

### Step 2: Start Edge Server dengan HO Config (Terminal 2)

**Option A: Menggunakan Batch Script**
```bash
.\start_edge_server_with_ho.bat
```

**Option B: Manual**
```bash
set HO_API_URL=http://localhost:8002
set HO_API_USERNAME=admin
set HO_API_PASSWORD=admin123
python manage.py runserver 8001
```

### Step 3: Test di Browser

```
http://localhost:8001/setup/
```

**Expected Result:**
- ✅ Dropdown Company loading dari HO Server
- ✅ Data company terisi (dengan token authentication)
- ✅ Select company → Dropdown brand auto-load
- ✅ Select brand → Input store code & name
- ✅ Submit → Store config tersimpan

### Step 4: Test dengan Script (Optional)

```bash
.\test_ho_token_integration.bat
```

## 🔍 Cara Kerja Token Authentication

```
Browser Request
    ↓
Edge Server: /api/ho/companies/
    ↓
    ├─ Step 1: POST /api/token/ → Get JWT token
    │  Request: {"username": "admin", "password": "admin123"}
    │  Response: {"access": "eyJhbGc...", "refresh": "..."}
    ↓
    ├─ Step 2: GET /api/sync/companies/ with Bearer token
    │  Header: Authorization: Bearer eyJhbGc...
    │  Response: {"companies": [...], "total": N}
    ↓
Edge Server returns data to browser
    ↓
JavaScript populates dropdown
```

## 📊 API Flow dengan Token

### 1. Get Token
```bash
POST http://localhost:8002/api/token/
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}

Response:
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 2. Fetch Companies dengan Token
```bash
GET http://localhost:8002/api/sync/companies/
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

Response:
{
  "companies": [
    {
      "id": "uuid-here",
      "code": "YGY",
      "name": "Yogya Group",
      "timezone": "Asia/Jakarta",
      ...
    }
  ],
  "total": 1,
  "sync_timestamp": "2026-01-27T12:00:00Z"
}
```

## 🧪 Manual Testing

### Test 1: Token Endpoint
```bash
curl -X POST http://localhost:8002/api/token/ ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"admin\",\"password\":\"admin123\"}"
```

**Expected:**
```json
{
  "access": "eyJhbGc...",
  "refresh": "eyJhbGc..."
}
```

### Test 2: Edge Proxy Endpoint
```bash
# Make sure environment variables are set before starting Edge Server
curl http://localhost:8001/api/ho/companies/
```

**Expected:**
```json
{
  "companies": [...],
  "total": 1,
  "sync_timestamp": "..."
}
```

### Test 3: Browser Test
1. Open: `http://localhost:8001/setup/`
2. Open DevTools (F12) → Console tab
3. Should see: "Loading Companies from HO..."
4. Dropdown should populate with companies

## ⚠️ Troubleshooting

### Error: "HO_API_URL not configured"
**Problem:** Environment variable tidak di-set sebelum start Edge Server

**Solution:**
```bash
# Stop Edge Server (Ctrl+C)
# Set variables
set HO_API_URL=http://localhost:8002
set HO_API_USERNAME=admin
set HO_API_PASSWORD=admin123
# Restart Edge Server
python manage.py runserver 8001
```

### Error: "Failed to obtain access token"
**Problem:** Username/password salah atau HO Server tidak running

**Solution:**
1. Pastikan HO Server running: `http://localhost:8002/admin/`
2. Test token manually:
```bash
curl -X POST http://localhost:8002/api/token/ ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"admin\",\"password\":\"admin123\"}"
```

### Error: "No Companies Found in HO"
**Problem:** HO Server tidak punya data company

**Solution:**
```bash
# Di HO Server, create demo data
python manage.py setup_demo
```

### Dropdown: "Error: Check HO Server Connection"
**Problem:** HO Server tidak running atau tidak bisa diakses

**Solution:**
1. Check HO Server: `http://localhost:8002/admin/`
2. Check logs di terminal HO Server
3. Test manual: `curl http://localhost:8002/api/token/`

## 📝 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HO_API_URL` | None | HO Server URL (e.g., http://localhost:8002) |
| `HO_API_USERNAME` | admin | Username untuk token authentication |
| `HO_API_PASSWORD` | admin123 | Password untuk token authentication |

## ✅ Success Checklist

- [ ] HO Server running on port 8002
- [ ] Edge Server running on port 8001 with environment variables
- [ ] Can get token from HO: `POST /api/token/`
- [ ] Edge proxy works: `GET /api/ho/companies/`
- [ ] Setup page loads: `http://localhost:8001/setup/`
- [ ] Dropdown Company populated from HO
- [ ] Dropdown Brand populated from HO
- [ ] Can configure store successfully

## 🎯 Files Changed

| File | Change |
|------|--------|
| `apps/core/views_setup.py` | ✅ Added JWT token authentication to proxy endpoints |
| `README_SETUP_HO_INTEGRATION.md` | ✅ Updated with token auth documentation |
| `start_edge_server_with_ho.bat` | ✅ New: Script to start Edge with HO config |
| `test_ho_token_integration.bat` | ✅ New: Script to test token integration |

## 🎉 Status

**✅ COMPLETE** - Token authentication implemented and tested!

Next: Start both servers and test in browser.
