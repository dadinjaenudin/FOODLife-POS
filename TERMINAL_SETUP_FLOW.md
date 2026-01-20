# Terminal Setup Flow - Updated ✅

## Alur Baru (Menggunakan localStorage)

### 1. Setup Terminal (Sekali Saja)
**URL**: `/setup/terminal/`

**Proses:**
1. Admin/Kasir akses halaman setup terminal
2. Pilih Device Type (POS/Tablet/Kiosk/Kitchen Display)
3. Input Terminal Code (contoh: POS-001, TAB-001)
4. Input Terminal Name
5. Submit form

**Yang Disimpan di localStorage:**
- `terminal_id` (UUID)
- `terminal_code` (POS-001)
- `terminal_name`
- `terminal_type` (pos/tablet/kiosk/kitchen_display)
- `store_id` (UUID)
- `store_code`
- `company_id` (UUID)
- `company_name`
- `setup_completed` (true)
- `setup_date` (timestamp)

**Backup**: Data juga disimpan di IndexedDB untuk persistence

---

### 2. Login Kasir
**URL**: `/login/`

**Proses:**
1. Halaman login cek localStorage
2. Jika **belum ada terminal_id**:
   - Muncul warning kuning di pojok kanan atas
   - "⚠️ Terminal Not Setup"
   - Button "Setup Terminal Now" → redirect ke `/setup/terminal/`
3. Jika **sudah ada terminal_id**:
   - Console log menampilkan terminal info
   - Form login bisa digunakan
4. Saat submit login:
   - Terminal ID dari localStorage dikirim via hidden input
   - Simpan terminal_id ke session
5. Login berhasil → redirect ke POS

---

### 3. POS Usage
**URL**: `/pos/`

**Middleware Check:**
1. Cek `request.session['terminal_id']`
2. Jika tidak ada → cek localStorage via login
3. Validate terminal dari database
4. Jika terminal valid:
   - Inject `request.terminal`
   - Inject `request.store`
   - Tampil info terminal di header
5. Jika terminal tidak valid:
   - Redirect ke `/setup/terminal/`

---

### 4. Reset Terminal (Ganti Device)
**Lokasi**: Button "🔄 Reset Terminal" di `/setup/terminal/`

**Proses:**
1. Klik button reset
2. Confirm dialog
3. Clear localStorage (semua key terminal*)
4. Delete IndexedDB
5. Reload page → form kosong untuk register ulang

---

## Keuntungan Alur Baru

### ✅ Setup Sekali Saja
- Terminal ID permanent di localStorage
- Tidak perlu setup ulang setiap restart browser
- Tetap tersimpan meskipun clear cookies

### ✅ Validasi di Login
- Kasir tahu sejak awal jika terminal belum setup
- Visual warning yang jelas
- Easy access ke setup page

### ✅ Info Lengkap di Header
- Terminal Code
- Store Code
- Outlet Name
- Hover untuk detail (IDs, IP, status online/offline)

### ✅ Mudah Ganti Terminal
- Button reset yang jelas
- Tidak perlu manual clear localStorage
- Confirm untuk avoid accident

---

## Data Flow

```
1. Setup Terminal → localStorage + IndexedDB + Session
                 ↓
2. Login → Read localStorage → Inject to session
                 ↓
3. Middleware → Validate session terminal_id → Inject request.terminal
                 ↓
4. POS Header → Display terminal info from request.terminal
```

---

## Testing Steps

### First Time Setup:
1. Akses `/setup/terminal/`
2. Register sebagai POS-001
3. Data tersimpan di localStorage
4. Redirect ke login
5. Login berhasil
6. POS tampil dengan terminal info di header

### Subsequent Logins:
1. Buka browser (localStorage masih ada)
2. Login langsung
3. Terminal ID otomatis terdeteksi
4. POS langsung bisa digunakan

### Reset Terminal:
1. Akses `/setup/terminal/`
2. Klik "🔄 Reset Terminal"
3. Confirm
4. Form kosong → register terminal baru
5. Login dengan terminal baru

---

## Troubleshooting

**Q: Terminal tidak terdeteksi setelah setup?**
A: Check browser localStorage: F12 → Application → Local Storage → localhost:8000

**Q: Mau ganti terminal tapi stuck?**
A: Akses `/setup/terminal/` dan klik Reset Terminal

**Q: Login tapi redirect ke setup terus?**
A: Terminal ID di localStorage tidak cocok dengan database. Reset dan register ulang.

**Q: Mau lihat terminal info detail?**
A: Hover di kartu terminal di header POS (popup detail muncul)

---

## Status: ✅ IMPLEMENTED
- localStorage storage
- Login validation
- Header terminal info
- Reset terminal function
- Middleware integration
