# Setup Page HO Integration Guide

## Overview

Halaman setup di Edge Server (`http://localhost:8001/setup/`) sekarang sudah terintegrasi dengan HO Server API. Dropdown **Company** dan **Brand** akan mengambil data langsung dari HO Server di `http://localhost:8002/api/sync/companies/`.

## Arsitektur

```
Edge Server (Port 8001)              HO Server (Port 8002)
┌─────────────────────┐             ┌──────────────────────┐
│ /setup/             │             │ /api/sync/companies/ │
│                     │   Fetch     │                      │
│ Dropdown Company ───┼────────────>│ Returns Companies    │
│                     │             │                      │
│ Dropdown Brand   ───┼────────────>│ /api/sync/brands/    │
│                     │   Fetch     │ Returns Brands       │
└─────────────────────┘             └──────────────────────┘
```

## Implementasi

### 1. Proxy Endpoints di Edge Server

Dibuat 2 endpoint proxy baru di `apps/core/views_setup.py`:

- **`/api/ho/companies/`** - Proxy untuk fetch companies dari HO
- **`/api/ho/brands/`** - Proxy untuk fetch brands dari HO

```python
@csrf_exempt
def fetch_companies_from_ho(request):
    """Fetch companies from HO Server API"""
    ho_api_url = getattr(settings, 'HO_API_URL', None)
    
    if not ho_api_url:
        return JsonResponse({
            'error': 'HO_API_URL not configured',
            'companies': [],
            'total': 0
        }, status=400)
    
    response = requests.get(f"{ho_api_url}/api/sync/companies/", timeout=10)
    return JsonResponse(response.json())
```

### 2. Update JavaScript di Setup Page

File `templates/core/setup_store.html` diupdate untuk menggunakan endpoint HO:

```javascript
// Sebelumnya: fetch('/api/sync/companies/')
// Sekarang:
fetch('/api/ho/companies/')
    .then(response => response.json())
    .then(data => {
        // Populate dropdown dengan data dari HO
        data.companies.forEach(company => {
            // Add option to select
        });
    });
```

## Konfigurasi

### Environment Variables

Tambahkan konfigurasi berikut di file `.env.edge`:

```bash
HO_API_URL=http://localhost:8002
HO_API_USERNAME=admin
HO_API_PASSWORD=admin123
```

### Settings.py

Sudah dikonfigurasi di `pos_fnb/settings.py`:

```python
HO_API_URL = os.environ.get('HO_API_URL', None)
HO_API_USERNAME = os.environ.get('HO_API_USERNAME', 'admin')
HO_API_PASSWORD = os.environ.get('HO_API_PASSWORD', 'admin123')
```

## Testing

### 1. Start HO Server (Port 8002)

```bash
# Terminal 1 - HO Server
python manage.py runserver 8002
```

### 2. Start Edge Server (Port 8001)

```bash
# Terminal 2 - Edge Server
set HO_API_URL=http://localhost:8002
python manage.py runserver 8001
```

### 3. Akses Setup Page

Buka browser: `http://localhost:8001/setup/`

### 4. Verifikasi

1. ✅ Dropdown Company menampilkan "Loading Companies from HO..."
2. ✅ Dropdown Company terisi dengan data dari HO Server
3. ✅ Pilih Company → Dropdown Brand otomatis load dari HO
4. ✅ Error handling jika HO Server tidak tersedia

## Endpoints

### Edge Server Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/setup/` | GET | Setup wizard page |
| `/api/ho/companies/` | GET | Proxy to HO companies API |
| `/api/ho/brands/?company_id={uuid}` | GET | Proxy to HO brands API |

### HO Server Endpoints (Target)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sync/companies/` | GET | List all companies |
| `/api/sync/brands/?company_id={uuid}` | GET | List brands by company |

## Flow Diagram

```
User → Edge Setup Page
  ↓
JavaScript: fetch('/api/ho/companies/')
  ↓
Edge Server: /api/ho/companies/ (Proxy)
  ↓
HTTP Request → HO Server: /api/sync/companies/
  ↓
HO Server: Returns JSON with companies
  ↓
Edge Server: Forward response
  ↓
JavaScript: Populate dropdown
  ↓
User: Selects Company
  ↓
JavaScript: fetch('/api/ho/brands/?company_id=...')
  ↓
Edge Server: /api/ho/brands/ (Proxy)
  ↓
HTTP Request → HO Server: /api/sync/brands/
  ↓
HO Server: Returns JSON with brands
  ↓
Edge Server: Forward response
  ↓
JavaScript: Populate brand dropdown
```

## Error Handling

### Jika HO_API_URL tidak dikonfigurasi

```json
{
  "success": false,
  "error": "HO_API_URL not configured in settings",
  "companies": [],
  "total": 0
}
```

Dropdown akan menampilkan: "-- Error: Check HO Server Connection --"

### Jika HO Server tidak tersedia

```json
{
  "success": false,
  "error": "Failed to connect to HO API: Connection refused",
  "companies": [],
  "total": 0
}
```

## Keuntungan

1. ✅ **Centralized Master Data** - Company dan Brand dikelola di HO Server
2. ✅ **Real-time Sync** - Edge Server selalu mendapat data terbaru dari HO
3. ✅ **Error Handling** - Jika HO tidak tersedia, ada fallback error message
4. ✅ **Simple Configuration** - Cukup set HO_API_URL di environment variable

## Troubleshooting

### Dropdown menampilkan "Error: Check HO Server Connection"

**Solusi:**
1. Pastikan HO Server running di port 8002
2. Cek environment variable `HO_API_URL` sudah di-set
3. Test manual: `curl http://localhost:8002/api/sync/companies/`

### Dropdown kosong (No Companies Found)

**Solusi:**
1. Pastikan ada data Company di HO Server
2. Cek di HO Server admin: `http://localhost:8002/admin/core/company/`
3. Atau create via management command: `python manage.py setup_demo`

## Next Steps

Setelah setup berhasil:

1. User pilih Company dari HO
2. User pilih Brand dari HO  
3. User input Store Code & Store Name
4. System create Store Config di Edge Server
5. User setup Terminal di `/setup/terminal/`

## Files Modified

1. `apps/core/views_setup.py` - Added proxy endpoints
2. `apps/core/urls.py` - Added URL routes
3. `templates/core/setup_store.html` - Updated JavaScript to use HO API
4. `.env.edge.example` - Added HO configuration example
