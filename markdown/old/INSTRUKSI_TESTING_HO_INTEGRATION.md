# 🚨 INSTRUKSI TESTING HO INTEGRATION

## ⚠️ PENTING: Environment Variables Must Be Set BEFORE Starting Server!

Error 500 terjadi karena Edge Server tidak punya environment variables `HO_API_URL`.

## ✅ Cara Testing yang BENAR

### Step 1: Stop Edge Server Jika Sedang Running

Jika Edge Server sedang running, **STOP** dulu (Ctrl+C di terminal).

### Step 2: Start HO Server (Terminal 1)

```bash
# Terminal 1
cd D:\YOGYA-Kiosk\pos-django-htmx-main
python manage.py runserver 8002
```

**Biarkan terminal ini tetap running!**

### Step 3: Start Edge Server dengan Environment Variables (Terminal 2)

**PILIH SALAH SATU:**

#### Option A: Menggunakan Script (RECOMMENDED)

```bash
# Terminal 2
cd D:\YOGYA-Kiosk\pos-django-htmx-main
.\start_edge_server_with_ho.bat
```

#### Option B: Manual (Set Environment Variables terlebih dahulu)

```bash
# Terminal 2
cd D:\YOGYA-Kiosk\pos-django-htmx-main

# Set environment variables SEBELUM start server
set HO_API_URL=http://localhost:8002
set HO_API_USERNAME=admin
set HO_API_PASSWORD=admin123

# BARU kemudian start server
python manage.py runserver 8001
```

### Step 4: Verifikasi di Console Edge Server

Setelah Edge Server start, Anda harus melihat di console:

```
Django version 4.2.x, using settings 'pos_fnb.settings'
Starting development server at http://127.0.0.1:8001/
Quit the server with CTRL-BREAK.
```

### Step 5: Test di Browser

Buka: `http://localhost:8001/setup/`

**Expected behavior:**
1. Dropdown Company menampilkan "Loading Companies from HO..."
2. Di console Edge Server (terminal 2), Anda akan melihat:
   ```
   [HO API] Getting token from http://localhost:8002/api/token/
   [HO API] Token obtained successfully
   [HO API] Companies fetched successfully
   ```
3. Dropdown Company akan terisi dengan data dari HO Server

### Step 6: Check Console Logs

**Console Edge Server harus menampilkan:**
```
[HO API] Getting token from http://localhost:8002/api/token/
[HO API] Token obtained successfully
[HO API] Companies fetched successfully
```

**Jika muncul:**
```
[HO API] Error: ...
```
Berarti ada masalah koneksi ke HO Server.

## 🐛 Troubleshooting

### Problem: Error 500 di browser

**Penyebab:** Environment variables tidak di-set sebelum start Edge Server

**Solusi:**
1. Stop Edge Server (Ctrl+C)
2. Set environment variables (lihat Step 3)
3. Start ulang Edge Server

### Problem: Dropdown tetap "Error: Check HO Server Connection"

**Penyebab:** HO Server tidak running atau tidak bisa diakses

**Solusi:**
1. Cek HO Server running: buka `http://localhost:8002/admin/`
2. Cek console HO Server ada error atau tidak
3. Test manual token:
   ```bash
   curl -X POST http://localhost:8002/api/token/ ^
     -H "Content-Type: application/json" ^
     -d "{\"username\":\"admin\",\"password\":\"admin123\"}"
   ```

### Problem: "No Companies Found in HO"

**Penyebab:** HO Server tidak punya data company

**Solusi:**
```bash
# Di terminal HO Server (buka terminal baru)
cd D:\YOGYA-Kiosk\pos-django-htmx-main
python manage.py setup_demo
```

## 📝 Checklist Testing

- [ ] HO Server running di port 8002
- [ ] Edge Server **STOPPED** (jika sebelumnya running)
- [ ] Environment variables di-set di terminal Edge Server
- [ ] Edge Server di-start SETELAH environment variables di-set
- [ ] Browser buka `http://localhost:8001/setup/`
- [ ] Dropdown Company loading dari HO
- [ ] Console Edge Server menampilkan log `[HO API]`

## ✅ Success Indicators

Jika berhasil, Anda akan melihat:

1. **Di Browser:**
   - Dropdown Company terisi dengan nama company dari HO
   - Misal: "Yogya Group (YGY)"

2. **Di Console Edge Server:**
   ```
   [HO API] Getting token from http://localhost:8002/api/token/
   [HO API] Token obtained successfully
   [HO API] Companies fetched successfully
   ```

3. **Di DevTools Browser (F12 → Network tab):**
   - Request ke `/api/ho/companies/` → Status 200 OK
   - Response body berisi data companies

## 🎯 Summary

**INGAT:** Environment variables HARUS di-set **SEBELUM** start Edge Server!

```bash
# SALAH - Ini tidak akan bekerja:
python manage.py runserver 8001
# kemudian set environment variables  ❌

# BENAR - Urutan yang benar:
set HO_API_URL=http://localhost:8002
set HO_API_USERNAME=admin
set HO_API_PASSWORD=admin123
python manage.py runserver 8001  ✅
```

Atau gunakan script: `.\start_edge_server_with_ho.bat` ✅
