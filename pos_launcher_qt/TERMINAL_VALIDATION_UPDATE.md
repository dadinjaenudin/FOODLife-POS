# Terminal Configuration Validation - Security Update

## Perubahan

### SEBELUM (❌ TIDAK AMAN)
- POS Launcher bisa login TANPA validasi config.json
- Terminal bisa akses data store lain jika `terminal_code` salah
- Aplikasi tetap jalan bahkan jika validasi gagal

### SESUDAH (✅ AMAN)
- **WAJIB validasi SEBELUM login**
- Terminal harus cocok dengan `store_code`, `company_code`, `brand_code`
- Aplikasi **EXIT** jika validasi gagal dengan error dialog

---

## File yang Diupdate

### 1. Backend API: `apps/core/api_terminal.py`
Semua endpoint terminal sekarang **WAJIB validasi**:

- **POST `/api/terminal/validate`**
  - WAJIB: `terminal_code`, `store_code`, `company_code`
  - Optional: `brand_code`
  
- **GET `/api/terminal/config`**
  - WAJIB: `terminal_code`, `store_code`, `company_code`
  - Optional: `brand_code`
  
- **GET `/api/terminal/receipt-template`**
  - WAJIB: `terminal_code`, `store_code`, `company_code`
  - Optional: `brand_code`

**Validasi Query:**
```python
query_filters = {
    'terminal_code': terminal_code,
    'store__store_code': store_code,         # WAJIB
    'store__company__code': company_code,     # WAJIB
    'is_active': True,
}
if brand_code:
    query_filters['brand__code'] = brand_code
```

**Error Response jika tidak cocok:**
```json
{
  "valid": false,
  "error": "Terminal \"BOE-001\" not found, inactive, or does not belong to store \"KPT\""
}
```

---

### 2. Frontend Launcher: `pos_launcher_qt/pos_launcher_qt.py`

#### Function `validate_terminal(config)` - Updated
**Return Value:** `tuple(success, data, error_message)`

**Validasi Mandatory:**
- Cek `terminal_code`, `store_code`, `company_code` ada di config.json
- Call API dengan validasi penuh
- Return error message yang descriptive

**Error Messages:**
1. **Missing config.json:**
   ```
   Configuration file (config.json) is missing or invalid.
   Please check terminal_code, store_code, company_code.
   ```

2. **Incomplete config:**
   ```
   Configuration incomplete:
   
   terminal_code: BOE-001
   store_code: MISSING
   company_code: MISSING
   
   Please update config.json with all required fields.
   ```

3. **Invalid terminal:**
   ```
   Terminal not found or invalid:
   
   Terminal "BOE-001" not found, inactive, or does not belong to store "SDN"
   
   Config values:
     terminal_code: BOE-001
     store_code: SDN
     company_code: YOGYA
     brand_code: BOE
   ```

4. **Connection error:**
   ```
   Cannot connect to Edge Server:
   http://127.0.0.1:8001
   
   Please check:
   1. Edge server is running
   2. Network connection
   3. Firewall settings
   ```

#### Function `main()` - Updated
**Flow:**
1. Load config.json
2. Fetch device config (optional - untuk customer display)
3. **VALIDATE terminal (MANDATORY)**
4. If validation failed:
   - Show QMessageBox error dialog
   - Print error to console
   - **EXIT aplikasi dengan sys.exit(1)**
5. If validation success:
   - Continue load POS webview

**Code:**
```python
# VALIDATE TERMINAL CONFIGURATION (MANDATORY)
success, validation_data, error_message = validate_terminal(config)

if not success:
    # Show error dialog
    error_dialog = QMessageBox()
    error_dialog.setIcon(QMessageBox.Icon.Critical)
    error_dialog.setWindowTitle("Terminal Validation Failed")
    error_dialog.setText("Cannot start POS application")
    error_dialog.setInformativeText(error_message)
    error_dialog.exec()
    
    # EXIT aplikasi
    sys.exit(1)

# Lanjut load POS window...
```

---

## Testing

### Test 1: Config Valid ✅
**config.json:**
```json
{
  "terminal_code": "BOE-001",
  "store_code": "KPT",
  "company_code": "YOGYA",
  "brand_code": "BOE",
  "edge_server": "http://127.0.0.1:8001"
}
```

**Expected Result:**
- ✅ Validasi sukses
- ✅ Aplikasi load POS window
- ✅ Terminal bisa login

---

### Test 2: Store Code Salah ❌
**config.json:**
```json
{
  "terminal_code": "BOE-001",
  "store_code": "SDN",  // ❌ SALAH! BOE-001 milik store KPT
  "company_code": "YOGYA",
  "brand_code": "BOE",
  "edge_server": "http://127.0.0.1:8001"
}
```

**Expected Result:**
- ❌ Validasi gagal
- ❌ Error dialog muncul
- ❌ Aplikasi EXIT (tidak load POS)

**Error Message:**
```
Terminal not found or invalid:

Terminal "BOE-001" not found, inactive, or does not belong to store "SDN"

Config values:
  terminal_code: BOE-001
  store_code: SDN
  company_code: YOGYA
  brand_code: BOE
```

---

### Test 3: Config Incomplete ❌
**config.json:**
```json
{
  "terminal_code": "BOE-001",
  "edge_server": "http://127.0.0.1:8001"
}
```

**Expected Result:**
- ❌ Validasi gagal (store_code & company_code missing)
- ❌ Error dialog muncul
- ❌ Aplikasi EXIT

**Error Message:**
```
Configuration incomplete:

terminal_code: BOE-001
store_code: MISSING
company_code: MISSING

Please update config.json with all required fields.
```

---

### Test 4: Edge Server Offline ❌
**Expected Result:**
- ❌ Connection error
- ❌ Error dialog muncul
- ❌ Aplikasi EXIT

**Error Message:**
```
Cannot connect to Edge Server:
http://127.0.0.1:8001

Please check:
1. Edge server is running
2. Network connection
3. Firewall settings
```

---

## Cara Test Manual

### 1. Test dengan Config Valid
```bash
# Gunakan config.json yang benar
cd pos_launcher_qt
python pos_launcher_qt.py
```
✅ **Expected:** Aplikasi load normal

---

### 2. Test dengan Config Salah
```bash
# Backup config valid
copy config.json config_backup.json

# Copy config salah
copy config_test_wrong.json config.json

# Run aplikasi
python pos_launcher_qt.py
```
❌ **Expected:** Error dialog muncul, aplikasi EXIT

```bash
# Restore config
copy config_backup.json config.json
```

---

## Security Benefits

1. **✅ Prevent Cross-Store Access**
   - Terminal tidak bisa akses data store lain
   - Validasi WAJIB di backend dan frontend

2. **✅ Early Error Detection**
   - Error terdeteksi SEBELUM login
   - User tidak bingung kenapa tidak bisa login

3. **✅ Clear Error Messages**
   - User tahu persis apa yang salah
   - Error message menunjukkan config values

4. **✅ Centralized Security**
   - Backend API enforce validation
   - Frontend validate early untuk UX

---

## Deployment Checklist

- [x] Update backend API (`api_terminal.py`)
- [x] Update frontend launcher (`pos_launcher_qt.py`)
- [x] Add QMessageBox untuk error dialog
- [x] Test validasi dengan config valid
- [x] Test validasi dengan config salah
- [ ] Update semua terminal config.json di production
- [ ] Test di semua terminal store
- [ ] Monitor error logs setelah deployment

---

## Rollback Plan

Jika ada masalah, rollback dengan:

```bash
# Restore original files
git checkout apps/core/api_terminal.py
git checkout pos_launcher_qt/pos_launcher_qt.py

# Restart edge server
docker-compose restart edge_web
```

---

## Notes

- Config.json WAJIB ada 4 fields: `terminal_code`, `store_code`, `company_code`, `edge_server`
- `brand_code` optional (untuk multi-brand stores)
- Error dialog menggunakan PyQt6 `QMessageBox`
- Aplikasi EXIT dengan code 1 jika validasi gagal
- Validasi dilakukan SEBELUM load webview untuk performance
