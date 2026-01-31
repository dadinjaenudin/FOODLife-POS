# ✅ Setup Page - HO Integration Complete

## 🎯 Tujuan
Dropdown **Company** dan **Brand** di halaman setup Edge Server (`http://localhost:8001/setup/`) sekarang mengambil data dari **HO Server API** (`http://localhost:8002/api/sync/companies/`).

## 📦 Yang Sudah Diimplementasikan

### 1. Proxy Endpoints di Edge Server
- **`GET /api/ho/companies/`** - Fetch companies dari HO Server
- **`GET /api/ho/brands/?company_id={uuid}`** - Fetch brands dari HO Server

### 2. Updated Setup Page JavaScript
File `templates/core/setup_store.html` sekarang menggunakan:
- `fetch('/api/ho/companies/')` - Bukan dari lokal API lagi
- `fetch('/api/ho/brands/?company_id=...')` - Bukan dari lokal API lagi

## 🚀 Cara Menjalankan

### Step 1: Start HO Server (Port 8002)
```bash
cd pos-django-htmx-main
python manage.py runserver 8002
```

### Step 2: Start Edge Server dengan Environment Variables
```bash
cd pos-django-htmx-main
set HO_API_URL=http://localhost:8002
set HO_API_USERNAME=admin
set HO_API_PASSWORD=admin123
python manage.py runserver 8001
```

### Step 3: Akses Setup Page
```
http://localhost:8001/setup/
```

## ✨ Expected Behavior

1. ✅ Buka `http://localhost:8001/setup/`
2. ✅ Dropdown Company loading: "Loading Companies from HO..."
3. ✅ Dropdown Company terisi dengan data dari HO Server (port 8002)
4. ✅ Pilih Company → Dropdown Brand auto-load dari HO Server
5. ✅ Pilih Brand → Input Store Code & Name
6. ✅ Submit → Store config tersimpan di Edge Server

## 🔄 Arsitektur

```
Browser (User)
    ↓
    | HTTP GET /setup/
    ↓
Edge Server (Port 8001)
    | JavaScript: fetch('/api/ho/companies/')
    ↓
Edge Server Proxy: /api/ho/companies/
    | HTTP GET http://localhost:8002/api/sync/companies/
    ↓
HO Server (Port 8002)
    | Returns: { companies: [...], total: N }
    ↓
Edge Server forwards response
    ↓
Browser populates dropdown
```

## 📁 Files Modified

| File | Changes |
|------|---------|
| `apps/core/views_setup.py` | ✅ Added `fetch_companies_from_ho()` and `fetch_brands_from_ho()` |
| `apps/core/urls.py` | ✅ Added `/api/ho/companies/` and `/api/ho/brands/` routes |
| `templates/core/setup_store.html` | ✅ Updated JavaScript to fetch from HO API |
| `.env.edge.example` | ✅ Added `HO_API_URL` configuration |

## 🔧 Configuration

### Environment Variables Required

```bash
HO_API_URL=http://localhost:8002
HO_API_USERNAME=admin
HO_API_PASSWORD=admin123
```

Atau bisa set di PowerShell sebelum start Edge Server:
```powershell
$env:HO_API_URL = "http://localhost:8002"
$env:HO_API_USERNAME = "admin"
$env:HO_API_PASSWORD = "admin123"
python manage.py runserver 8001
```

### Autentikasi Token (JWT)

Proxy endpoints sekarang menggunakan JWT token authentication:

1. **Step 1:** Edge Server request token dari `POST /api/token/`
2. **Step 2:** HO Server return JWT access token
3. **Step 3:** Edge Server use token untuk fetch companies/brands
4. **Step 4:** Return data ke browser

## 🧪 Testing

### Quick Test
```bash
# Test HO Server API
curl http://localhost:8002/api/sync/companies/

# Test Edge Proxy
curl http://localhost:8001/api/ho/companies/
```

### Automated Test Script
```bash
.\test_ho_integration.bat
```

## ⚠️ Error Handling

### Error: "HO_API_URL not configured"
```json
{
  "success": false,
  "error": "HO_API_URL not configured in settings",
  "companies": [],
  "total": 0
}
```
**Fix:** Set environment variable `HO_API_URL=http://localhost:8002`

### Error: "Failed to connect to HO API"
```json
{
  "success": false,
  "error": "Failed to connect to HO API: Connection refused",
  "companies": [],
  "total": 0
}
```
**Fix:** Start HO Server on port 8002

### Dropdown: "No Companies Found in HO"
**Fix:** Create companies in HO Server:
```bash
python manage.py setup_demo  # Run on HO Server (port 8002)
```

## 📊 API Endpoints

### Edge Server (Port 8001)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ho/companies/` | GET | Proxy to HO companies API |
| `/api/ho/brands/?company_id={uuid}` | GET | Proxy to HO brands API |

### HO Server (Port 8002)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sync/companies/` | GET | List all companies |
| `/api/sync/brands/?company_id={uuid}` | GET | List brands by company |

## 🎉 Success Criteria

- [x] Dropdown Company mengambil data dari HO Server (port 8002)
- [x] Dropdown Brand mengambil data dari HO Server (port 8002)
- [x] Error handling jika HO Server tidak tersedia
- [x] Environment variable `HO_API_URL` untuk konfigurasi
- [x] Proxy endpoints di Edge Server
- [x] Documentation dan testing scripts

## 📚 Related Documentation

- `SETUP_HO_INTEGRATION_GUIDE.md` - Detailed guide with troubleshooting
- `SETUP_HO_INTEGRATION_SUMMARY.md` - Complete implementation summary
- `.env.edge.example` - Environment configuration example

## ✅ Status: COMPLETE

Implementasi selesai dan siap digunakan! 🚀
