# Setup HO Integration - Summary

## ✅ Implementasi Selesai

Dropdown Company dan Brand di halaman setup Edge Server (`http://localhost:8001/setup/`) sekarang **mengambil data dari HO Server API** di `http://localhost:8002/api/sync/companies/`.

## 📋 Apa yang Sudah Dibuat

### 1. Proxy Endpoints di Edge Server
**File:** `apps/core/views_setup.py`

Dibuat 2 endpoint proxy baru:
- **`/api/ho/companies/`** - Proxy untuk fetch companies dari HO Server
- **`/api/ho/brands/?company_id={uuid}`** - Proxy untuk fetch brands dari HO Server

```python
@csrf_exempt
def fetch_companies_from_ho(request):
    """Proxy endpoint to fetch companies from HO Server API"""
    ho_api_url = getattr(settings, 'HO_API_URL', None)
    
    if not ho_api_url:
        return JsonResponse({
            'success': False,
            'error': 'HO_API_URL not configured in settings',
            'companies': [],
            'total': 0
        }, status=400)
    
    try:
        response = requests.get(
            f"{ho_api_url}/api/sync/companies/",
            timeout=10
        )
        response.raise_for_status()
        return JsonResponse(response.json())
        
    except requests.exceptions.RequestException as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to connect to HO API: {str(e)}',
            'companies': [],
            'total': 0
        }, status=500)
```

### 2. URL Routes
**File:** `apps/core/urls.py`

```python
# HO API Proxy endpoints
path('api/ho/companies/', views_setup.fetch_companies_from_ho, name='fetch_companies_from_ho'),
path('api/ho/brands/', views_setup.fetch_brands_from_ho, name='fetch_brands_from_ho'),
```

### 3. Frontend JavaScript Update
**File:** `templates/core/setup_store.html`

JavaScript diupdate untuk fetch dari HO API:

```javascript
// SEBELUMNYA: fetch('/api/sync/companies/')
// SEKARANG:
fetch('/api/ho/companies/')
    .then(response => response.json())
    .then(data => {
        // Populate dropdown dengan data dari HO Server
        data.companies.forEach(company => {
            const option = document.createElement('option');
            option.value = company.id;
            option.textContent = `${company.name} (${company.code})`;
            companySelect.appendChild(option);
        });
    })
    .catch(error => {
        console.error('Error loading companies from HO:', error);
        companySelect.innerHTML = '<option value="">-- Error: Check HO Server Connection --</option>';
    });
```

### 4. Configuration Files
**File:** `.env.edge.example`

```bash
# HO (Head Office) Server API Configuration
HO_API_URL=http://localhost:8002
HO_API_USERNAME=admin
HO_API_PASSWORD=admin123
```

### 5. Documentation
**File:** `SETUP_HO_INTEGRATION_GUIDE.md`

Dokumentasi lengkap dengan flow diagram, troubleshooting, dan testing guide.

## 🔄 Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     User Opens Setup Page                    │
│                 http://localhost:8001/setup/                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            JavaScript: fetch('/api/ho/companies/')           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│   Edge Server Proxy: /api/ho/companies/ (Port 8001)         │
│   → Forwards request to HO Server                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│   HO Server API: /api/sync/companies/ (Port 8002)           │
│   → Returns JSON: { companies: [...], total: N }            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         Edge Server forwards response to browser             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         JavaScript populates dropdown Company                │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Cara Testing

### Step 1: Start HO Server (Port 8002)

```bash
# Terminal 1
cd pos-django-htmx-main
python manage.py runserver 8002
```

### Step 2: Start Edge Server dengan HO_API_URL (Port 8001)

```bash
# Terminal 2
cd pos-django-htmx-main
set HO_API_URL=http://localhost:8002
python manage.py runserver 8001
```

### Step 3: Buka Setup Page di Browser

```
http://localhost:8001/setup/
```

### Step 4: Verifikasi

✅ Dropdown Company menampilkan "Loading Companies from HO..."
✅ Dropdown Company terisi dengan data dari HO Server (bukan lokal)
✅ Pilih Company → Dropdown Brand otomatis load dari HO
✅ Pilih Brand → Input Store Code & Name
✅ Submit → Store config tersimpan di Edge Server

## 🔍 Testing dengan Script

### Option 1: PowerShell Script

```bash
.\test_ho_integration.bat
```

### Option 2: Python Script

```bash
python tmp_rovodev_test_ho_integration.py
```

Script akan test:
1. ✅ HO Server API responding
2. ✅ Edge Proxy Companies endpoint
3. ✅ Edge Proxy Brands endpoint
4. ✅ Setup page loads with HO endpoints

## 📊 API Endpoints

### Edge Server (Port 8001)

| Endpoint | Method | Description | Source Data |
|----------|--------|-------------|-------------|
| `/setup/` | GET | Setup wizard page | - |
| `/api/ho/companies/` | GET | Fetch companies | **HO Server** |
| `/api/ho/brands/?company_id={uuid}` | GET | Fetch brands | **HO Server** |

### HO Server (Port 8002)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sync/companies/` | GET | List all companies |
| `/api/sync/brands/?company_id={uuid}` | GET | List brands by company |

## ⚠️ Penting: Autentikasi

Jika HO Server API memerlukan autentikasi (JWT Token), proxy endpoint sudah siap untuk diupdate:

```python
# Future enhancement: Add JWT authentication
username = getattr(settings, 'HO_API_USERNAME', 'admin')
password = getattr(settings, 'HO_API_PASSWORD', 'admin123')

# Get token
token_response = requests.post(
    f"{ho_api_url}/api/token/",
    json={'username': username, 'password': password}
)
access_token = token_response.json().get('access')

# Use token in requests
headers = {'Authorization': f'Bearer {access_token}'}
response = requests.get(
    f"{ho_api_url}/api/sync/companies/",
    headers=headers
)
```

## 🐛 Troubleshooting

### Error: "HO_API_URL not configured"
**Solusi:**
```bash
set HO_API_URL=http://localhost:8002
python manage.py runserver 8001
```

### Error: "Failed to connect to HO API"
**Solusi:**
1. Pastikan HO Server running: `python manage.py runserver 8002`
2. Test manual: `curl http://localhost:8002/api/sync/companies/`

### Dropdown: "No Companies Found in HO"
**Solusi:**
1. Cek data di HO Server: `http://localhost:8002/admin/core/company/`
2. Create demo data: `python manage.py setup_demo` di HO Server

### Error: "Data autentikasi tidak diberikan"
**Solusi:**
Jika HO Server memerlukan autentikasi, update proxy endpoint untuk include JWT token (lihat section Autentikasi di atas).

## 📝 Files Modified

1. ✅ `apps/core/views_setup.py` - Added 2 proxy endpoints
2. ✅ `apps/core/urls.py` - Added 2 URL routes
3. ✅ `templates/core/setup_store.html` - Updated JavaScript to use HO API
4. ✅ `.env.edge.example` - Added HO configuration
5. ✅ `SETUP_HO_INTEGRATION_GUIDE.md` - Full documentation
6. ✅ `test_ho_integration.bat` - Testing script
7. ✅ `tmp_rovodev_test_ho_integration.py` - Python testing script

## ✨ Keuntungan

1. **Centralized Master Data** - Company & Brand dikelola di HO Server
2. **Real-time Data** - Edge Server selalu mendapat data terbaru
3. **No Manual Sync** - Tidak perlu sync manual via button
4. **Error Handling** - Graceful fallback jika HO tidak tersedia
5. **Simple Setup** - Hanya perlu set environment variable

## 🎯 Next Steps

Setelah setup berhasil:

1. User pilih **Company** dari dropdown (data dari HO)
2. User pilih **Brand** dari dropdown (data dari HO)
3. User input **Store Code** & **Store Name**
4. Click **"Configure Store"**
5. Edge Server tersimpan dengan Brand ID dari HO
6. Lanjut ke Terminal Setup: `/setup/terminal/`

## 📞 Support

Jika ada masalah:
1. Cek log Edge Server (terminal yang running server)
2. Cek log HO Server (terminal yang running HO)
3. Buka browser console (F12) untuk lihat error JavaScript
4. Review file `SETUP_HO_INTEGRATION_GUIDE.md` untuk troubleshooting detail
