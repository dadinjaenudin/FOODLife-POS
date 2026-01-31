# Setup Store Integration with Master Data API - Summary

## ✅ Yang Sudah Dikerjakan

### 1. Menu "Setup Store" di Sidebar Management
- **File**: `templates/management/base.html`
- **Perubahan**: Menambahkan menu "Setup Store" di sidebar dengan section "System Setup"
- **Link**: `/setup/`
- **Status**: ✅ **SELESAI**

### 2. Template Setup Store dengan JavaScript
- **File**: `templates/core/setup_store.html`
- **Fitur**:
  - Dropdown Company yang auto-load dari API `/api/sync/companies/`
  - Dropdown Brand yang auto-load berdasarkan company dari API `/api/sync/brands/?company_id={uuid}`
  - Button "Sync from HO API" untuk sync data dari HQ Server
  - Form validation dan auto-uppercase store code
- **Status**: ✅ **SELESAI**

### 3. Master Data API (Sudah Ada)
- **Files**: `apps/core/views_sync.py`, `apps/core/urls.py`
- **Endpoints**:
  - `GET /api/sync/companies/` - List all companies
  - `GET /api/sync/brands/?company_id={uuid}` - List brands by company
  - `GET /api/sync/stores/?brand_id={uuid}` - List stores by brand
- **Status**: ✅ **SUDAH ADA & BERFUNGSI**

### 4. Sync from HO API dengan JWT Authentication
- **File**: `apps/core/views_setup.py`
- **Function**: `sync_from_remote_api()`
- **Fitur**:
  - Mendapatkan JWT token dari HQ Server
  - Fetch companies dan brands dari HQ
  - Sync ke Edge Server database
- **Status**: ✅ **KODE SELESAI**

### 5. Settings Configuration
- **File**: `pos_fnb/settings.py`
- **Ditambahkan**:
  ```python
  HO_API_URL = os.environ.get('HO_API_URL', None)
  HO_API_USERNAME = os.environ.get('HO_API_USERNAME', 'admin')
  HO_API_PASSWORD = os.environ.get('HO_API_PASSWORD', 'admin123')
  ```
- **Status**: ✅ **SELESAI**

### 6. Environment Variables
- **File**: `.env.edge`, `docker-compose.edge.yml`
- **Variables**:
  ```bash
  HO_API_URL=http://host.docker.internal:8002
  HO_API_USERNAME=admin
  HO_API_PASSWORD=admin123
  ```
- **Status**: ✅ **SELESAI**

---

## ⚠️ Issue yang Masih Ada

### Network Connectivity Issue
**Problem**: Edge Server container tidak bisa mengakses HQ Server di `host.docker.internal:8002`

**Error**: 
```
400 Client Error: Bad Request for url: http://host.docker.internal:8002/api/token/
DisallowedHost at /api/token/
```

**Root Cause**:
1. `host.docker.internal` di-reject oleh Django ALLOWED_HOSTS di HQ Server
2. HQ Server (foodbeverages-cms) menggunakan network berbeda dari Edge Server

---

## 🔧 Solusi yang Perlu Diterapkan

### Opsi 1: Tambahkan ALLOWED_HOSTS di HQ Server (RECOMMENDED)
Tambahkan `host.docker.internal` ke ALLOWED_HOSTS di HQ Server:

**File**: HQ Server `config/settings.py` atau `.env`
```python
ALLOWED_HOSTS = ['*']  # atau lebih spesifik
# ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'host.docker.internal', 'fnb_ho_web']
```

### Opsi 2: Gunakan IP Host Machine
Ganti HO_API_URL dengan IP address host machine (contoh Windows WSL):
```bash
HO_API_URL=http://172.17.0.1:8002  # Gateway IP
```

### Opsi 3: Join ke Network yang Sama
Tambahkan Edge container ke network HQ:
```yaml
# docker-compose.edge.yml
networks:
  - default
  - foodbeverages-cms_default

# Lalu gunakan:
HO_API_URL=http://fnb_ho_web:8000
```

---

## 📋 Testing Manual

### Test 1: API HQ Berfungsi (dari Host Machine)
```powershell
# Get Token
$body = @{username='admin';password='admin123'} | ConvertTo-Json
$response = Invoke-RestMethod -Uri "http://localhost:8002/api/token/" -Method POST -Body $body -ContentType "application/json"
$token = $response.access

# Test Companies API
$headers = @{Authorization = "Bearer $token"}
Invoke-RestMethod -Uri "http://localhost:8002/api/sync/companies/" -Method GET -Headers $headers
```

**Result**: ✅ **BERHASIL** - HQ memiliki 2 companies (YOGYA GROUP, YOMART)

### Test 2: Edge Server Local API
```powershell
Invoke-RestMethod -Uri "http://localhost:8001/api/sync/companies/" -Method GET
```

**Result**: ✅ **BERHASIL** - Edge memiliki 1 company (TEST Company)

### Test 3: Sync from HO (akan berhasil setelah network issue diperbaiki)
```powershell
Invoke-RestMethod -Uri "http://localhost:8001/setup/sync-from-ho/" -Method GET
```

**Current Result**: ❌ **GAGAL** - Network connectivity issue

---

## 🎯 Next Steps

1. **Perbaiki ALLOWED_HOSTS di HQ Server** (solusi tercepat)
2. **Test sync dari browser**: 
   - Buka http://localhost:8001/setup/
   - Klik button "🔄 Sync from Head Office API"
3. **Verifikasi dropdown menampilkan data dari HQ**:
   - Select Company → harus muncul YOGYA GROUP dan YOMART
   - Select Brand → harus muncul brands dari company yang dipilih
4. **Submit form untuk create Store**

---

## 📊 Data Summary

### HQ Server (Port 8002)
- **Companies**: 2 (YOGYA GROUP, YOMART)
- **Brands**: Multiple (tergantung data yang ada)
- **Authentication**: JWT Token Required
- **API Base**: `http://localhost:8002/api/`

### Edge Server (Port 8001)
- **Companies**: 1 (TEST Company - untuk testing)
- **Brands**: 1 (TEST Brand)
- **Stores**: 0 (belum di-create)
- **Authentication**: None (local API)
- **API Base**: `http://localhost:8001/api/`

---

## 🚀 Cara Menggunakan (Setelah Network Fixed)

1. **Buka Setup Page**:
   ```
   http://localhost:8001/setup/
   ```

2. **Sync dari HQ (Opsional)**:
   - Klik button "🔄 Sync from Head Office API"
   - Data company/brand dari HQ akan ter-sync ke Edge

3. **Pilih Company & Brand**:
   - Dropdown otomatis load dari local Edge database
   - Pilih company dan brand yang sesuai

4. **Input Store Details**:
   - Store Code (contoh: JKT-001)
   - Store Name (contoh: Senayan City)
   - Address (optional)
   - Phone (optional)

5. **Submit**:
   - Klik "Configure Store →"
   - Edge Server siap digunakan!

---

## 📝 Files Modified

1. `templates/management/base.html` - Menu sidebar
2. `apps/core/views_setup.py` - Sync logic dengan JWT
3. `pos_fnb/settings.py` - HO API settings
4. `.env.edge` - Environment variables
5. `docker-compose.edge.yml` - Environment variables untuk container

---

**Status Akhir**: 95% Complete - Tinggal fix network connectivity issue di ALLOWED_HOSTS HQ Server.
