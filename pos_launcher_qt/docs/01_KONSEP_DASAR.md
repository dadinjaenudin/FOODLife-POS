# 📚 Konsep Dasar POS Launcher - Belajar dari Nol

## 🎯 Apa itu POS Launcher?

**POS Launcher** adalah aplikasi desktop yang membuka **2 tampilan sekaligus**:
1. **Tampilan Kasir** - untuk staff yang menginput pesanan
2. **Tampilan Pelanggan** - untuk customer melihat pesanan mereka

Bayangkan seperti di McDonald's atau KFC: kasir punya layar sendiri, dan pelanggan punya layar yang menghadap ke mereka.

---

## 🤔 Mengapa Perlu 2 Layar?

### Masalah Tanpa Dual Display:
- ❌ Customer tidak tahu apa yang sedang diinput kasir
- ❌ Tidak transparansi harga
- ❌ Customer tidak bisa konfirmasi pesanan
- ❌ Mudah terjadi kesalahan (customer bilang A, kasir input B)

### Solusi dengan Dual Display:
- ✅ Customer melihat langsung apa yang diinput
- ✅ Transparansi harga real-time
- ✅ Customer bisa konfirmasi sebelum bayar
- ✅ Mengurangi komplain dan kesalahan
- ✅ Pengalaman customer lebih modern & profesional

---

## 🏗️ Konsep Arsitektur Sederhana

```
┌─────────────────────────────────────────────────────────────┐
│                    KOMPUTER KASIR                            │
│                                                              │
│  ┌───────────────────┐          ┌──────────────────────┐   │
│  │   Monitor Kasir   │          │  Monitor Pelanggan   │   │
│  │   (1366x768)      │          │    (1024x768)        │   │
│  ├───────────────────┤          ├──────────────────────┤   │
│  │                   │          │                      │   │
│  │  [Staff View]     │          │  [Customer View]     │   │
│  │                   │          │                      │   │
│  │  - Input pesanan  │          │  - Lihat bill        │   │
│  │  - Login/Logout   │          │  - Lihat harga       │   │
│  │  - Setting kasir  │          │  - Konfirmasi        │   │
│  │  - Semua fitur    │          │  - Slideshow         │   │
│  │                   │          │                      │   │
│  └───────────────────┘          └──────────────────────┘   │
│           ▲                              ▲                  │
│           │                              │                  │
│           └──────────────┬───────────────┘                  │
│                          │                                  │
│                  ┌───────▼────────┐                        │
│                  │  POS Launcher  │                        │
│                  │   (PyQt6)      │                        │
│                  └────────────────┘                        │
│                          │                                  │
│                  ┌───────▼────────┐                        │
│                  │  Flask API     │                        │
│                  │  (Port 5000)   │                        │
│                  └────────────────┘                        │
│                          │                                  │
└──────────────────────────┼──────────────────────────────────┘
                           │
                           │ HTTP
                           │
                  ┌────────▼────────┐
                  │  Django Server  │
                  │  (Docker)       │
                  │  Port 8001      │
                  └─────────────────┘
```

---

## 🔄 Alur Kerja Sistem (Flow)

### 1️⃣ Saat Aplikasi Dibuka

```
START
  │
  ├─> Read config.json (terminal_code = BOE-001)
  │
  ├─> Buka 2 window PyQt6:
  │   ├─> Window 1: Full WebView ke http://localhost:8001/pos/?terminal=BOE-001
  │   └─> Window 2: HTML lokal (customer_display.html)
  │
  ├─> Start Flask API di port 5000
  │
  └─> Kedua layar sudah siap
```

### 2️⃣ Saat Kasir Login

```
KASIR LOGIN
  │
  ├─> Input username & password di Monitor Kasir
  │
  ├─> Django validasi → Login berhasil
  │
  ├─> Session disimpan dengan terminal_code = BOE-001
  │
  └─> POS interface muncul di Monitor Kasir
      Monitor Pelanggan tetap blank/slideshow
```

### 3️⃣ Saat Ada Pesanan Baru

```
CUSTOMER PESAN
  │
  ├─> Kasir pilih produk (misal: Nasi Goreng = Rp 25.000)
  │
  ├─> Django update database Bill & BillItem
  │
  ├─> Template Django render bill_panel.html
  │   (ini yang muncul di sidebar kasir)
  │
  ├─> Flask API terima data via:
  │   POST /api/customer-display/update-bill
  │
  ├─> Flask simpan data di memory (bills_data)
  │
  ├─> Monitor Pelanggan detect perubahan via SSE
  │   (Server-Sent Events = push notification otomatis)
  │
  └─> Monitor Pelanggan update tampilan:
      ┌────────────────────────┐
      │  🛒 Pesanan Anda      │
      ├────────────────────────┤
      │  Nasi Goreng     25K  │
      │  ─────────────────────│
      │  Total:          25K  │
      └────────────────────────┘
```

### 4️⃣ Saat Pembayaran

```
PROSES BAYAR
  │
  ├─> Kasir klik "Bayar" → payment_modal muncul
  │
  ├─> Kasir pilih metode (Cash/QRIS/Card)
  │
  ├─> Input jumlah bayar
  │
  ├─> Django clone modal payment ke customer display
  │   via Flask API: POST /api/customer-display/show-modal
  │
  ├─> KEDUA LAYAR menampilkan modal yang SAMA:
  │   
  │   Monitor Kasir:              Monitor Pelanggan:
  │   ┌─────────────────┐        ┌─────────────────┐
  │   │  💰 Payment     │        │  💰 Payment     │
  │   │  Total: 25.000  │        │  Total: 25.000  │
  │   │  Cash: 50.000   │        │  Cash: 50.000   │
  │   │  Change: 25.000 │        │  Change: 25.000 │
  │   │  [Confirm]      │        │  ✅ Waiting...  │
  │   └─────────────────┘        └─────────────────┘
  │
  ├─> Kasir klik Confirm
  │
  ├─> Django proses payment → simpan transaksi
  │
  ├─> Kirim signal clear ke customer display
  │
  └─> Monitor Pelanggan kembali blank/slideshow
```

### 5️⃣ Saat Kasir Logout

```
LOGOUT
  │
  ├─> Kasir klik "Logout"
  │
  ├─> Django logout_view dipanggil
  │
  ├─> PENTING: launcher_terminal_code di-backup
  │   (ini yang kita fix agar tidak hilang!)
  │
  ├─> Session dibersihkan (user data dihapus)
  │
  ├─> launcher_terminal_code di-restore
  │
  ├─> Redirect ke login screen
  │
  └─> Login lagi → Terminal BOE-001 masih terdeteksi ✅
      (TIDAK perlu setup terminal lagi)
```

---

## 🧩 Komponen Utama

### 1. **POS Launcher (PyQt6)**
- **Bahasa**: Python
- **Framework**: PyQt6 + QtWebEngine
- **Fungsi**: 
  - Membuka 2 window
  - Embed browser Chrome di dalam aplikasi
  - Manage dual display
  - Start Flask API

### 2. **Django Server (Backend)**
- **Fungsi**:
  - Web server POS interface
  - Database (products, bills, payments)
  - Authentication (login/logout)
  - Business logic
  - Render HTML templates

### 3. **Flask API (Bridge/Jembatan)**
- **Fungsi**:
  - Jembatan antara Django ↔ Customer Display
  - Simpan data bill temporary (in-memory)
  - Server-Sent Events (SSE) untuk real-time
  - Endoint: `/api/customer-display/*`

### 4. **Customer Display HTML**
- **File**: `customer_display.html`
- **Fungsi**:
  - Tampilan untuk pelanggan
  - Auto-update via SSE
  - Slideshow saat idle
  - Blank screen mode

---

## 📡 Teknologi Komunikasi

### Server-Sent Events (SSE)

SSE adalah teknik untuk **server push data ke client** secara real-time.

**Analogi sederhana:**
- **Polling** = Client nanya terus: "Ada update? Ada update? Ada update?"
  - ❌ Boros bandwidth
  - ❌ Delay bisa lama
  
- **SSE** = Server langsung kasih tau saat ada update
  - ✅ Efisien
  - ✅ Real-time
  - ✅ One-way (server → client)

**Cara kerja:**
```javascript
// Customer Display connect ke Flask
const eventSource = new EventSource('http://localhost:5000/api/customer-display/stream');

// Tunggu event dari server
eventSource.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    // Update tampilan langsung!
    updateBillDisplay(data);
};
```

**Di Flask:**
```python
@app.route('/api/customer-display/stream')
def stream():
    def generate():
        while True:
            # Tunggu sampai ada update
            yield f"data: {json.dumps(bills_data)}\n\n"
            time.sleep(1)
    
    return Response(generate(), mimetype='text/event-stream')
```

---

## 🔐 Session & Terminal Management

### Konsep Session Django

**Session** = data yang disimpan per user di server

```python
# Saat login pertama kali
request.session['terminal_code'] = 'BOE-001'  # Terminal aktif
request.session['launcher_terminal_code'] = 'BOE-001'  # Dari config.json (persistent)
request.session['user_id'] = 123

# Saat logout
request.session.flush()  # Hapus SEMUA data session

# ❌ MASALAH: launcher_terminal_code juga terhapus!
# Saat login lagi → tidak tahu terminal yang mana → redirect ke setup

# ✅ SOLUSI:
# Backup launcher_terminal_code sebelum flush
# Restore setelah flush
```

### Perbedaan terminal_code vs launcher_terminal_code

| Key | Arti | Lifecycle |
|-----|------|-----------|
| `terminal_code` | Terminal yang sedang aktif digunakan | Satu sesi login (sampai logout) |
| `launcher_terminal_code` | Terminal dari config.json | **PERSISTENT** (tidak hilang saat logout) |

**Mengapa perlu 2 key?**
- `terminal_code` → untuk security, dibersihkan saat logout
- `launcher_terminal_code` → untuk kiosk mode, harus tetap ada

---

## 🎨 Konsep Dual Display Sync

### Prinsip Dasar: "Mirror with Intelligence"

Tidak semua yang di kasir harus tampil di customer display.

**Whitelist (yang boleh tampil di customer):**
- ✅ Bill panel (daftar pesanan)
- ✅ Payment modal (proses bayar)
- ✅ Total harga
- ✅ Success message

**Blacklist (yang TIDAK boleh tampil di customer):**
- ❌ Modal internal (hold bill, void item)
- ❌ Setting kasir
- ❌ Shift management
- ❌ Menu navigation
- ❌ Error messages system

### Cara Kerja Modal Sync

**payment_modal.html dikonfigurasi dengan:**

```html
<div id="paymentModal" 
     data-sync-to-customer="true"
     data-customer-readonly="true">
    <!-- Modal content -->
</div>
```

**Attribute meaning:**
- `data-sync-to-customer="true"` → Clone ke customer display
- `data-customer-readonly="true"` → Disable buttons di customer side
- `data-modal-type="payment"` → Tipe modal (untuk filtering)

**Flow:**
```
1. Modal muncul di kasir
   ↓
2. Django template render dengan attribute data-sync
   ↓
3. JavaScript detect modal dengan attribute tersebut
   ↓
4. POST ke Flask API dengan HTML modal
   ↓
5. Flask simpan di memory
   ↓
6. Customer display terima via SSE
   ↓
7. Customer display inject HTML ke DOM
   ↓
8. Customer lihat modal yang sama (tapi read-only)
```

---

## 🛠️ Kenapa Pakai PyQt6?

### Alternatif vs PyQt6

| Teknologi | Kelebihan | Kekurangan |
|-----------|-----------|------------|
| **Electron** | Familiar (JavaScript), Cross-platform | ❌ Berat (>100MB), Lambat startup |
| **Browser Native** | Ringan | ❌ Tidak bisa kontrol dual display |
| **Tkinter** | Built-in Python | ❌ Tidak ada WebView modern |
| **PyQt6** ✅ | WebView modern, Dual display control, Powerful | Setup agak kompleks |

### Keunggulan PyQt6:
- ✅ Embed full Chrome browser (Chromium)
- ✅ Control window position & size
- ✅ Multi-monitor support
- ✅ Native performance
- ✅ Bisa fullscreen/kiosk mode

---

## 🎯 Design Pattern yang Digunakan

### 1. **Observer Pattern** (SSE)
```
Subject (Flask) → notify → Observer (Customer Display)
```

### 2. **Bridge Pattern** (Flask API)
```
Django ←→ Flask API ←→ Customer Display
(Backend)  (Bridge)    (Frontend)
```

### 3. **Configuration-Driven** (payment_modal v2.1)
```python
PAYMENT_METHODS = {
    'cash': {
        'enabled': True,
        'icon': '💵',
        'requires_input': True
    },
    'qris': {
        'enabled': True,
        'icon': '📱',
        'requires_input': False
    }
}
```

### 4. **Session Backup/Restore** (Terminal Persistence)
```python
# Backup
backup = critical_data.copy()

# Destructive operation
session.flush()

# Restore
session['critical_data'] = backup
session.save()
```

---

## 📊 Data Flow Diagram

```
┌──────────────┐
│   KASIR      │
│  (Browser)   │
└──────┬───────┘
       │ User Action (click, input)
       │
       ▼
┌──────────────────┐
│  Django Views    │◄─── Database
│  (apps/pos/)     │      (SQLite/Postgres)
└──────┬───────────┘
       │ Render Template
       │ (bill_panel.html, payment_modal.html)
       │
       ├───────────────────────────┐
       │                           │
       ▼                           ▼
┌──────────────┐           ┌──────────────────┐
│  Monitor     │           │  Flask API       │
│  Kasir       │           │  POST /update    │
│  (Update UI) │           └─────┬────────────┘
└──────────────┘                 │
                                 │ Store data
                                 │ Emit SSE event
                                 │
                          ┌──────▼────────────┐
                          │  SSE Stream       │
                          │  (Real-time push) │
                          └──────┬────────────┘
                                 │
                                 ▼
                          ┌──────────────────┐
                          │  Customer Display│
                          │  (Auto update)   │
                          └──────────────────┘
```

---

## 🎓 Kesimpulan Konsep

### Inti dari Sistem Ini:

1. **2 Monitor = 2 Pengalaman Berbeda**
   - Kasir: Full control
   - Customer: View-only transparency

2. **Real-time Sync = Customer Confidence**
   - Tidak ada "surprise" saat bayar
   - Customer tahu persis apa yang dibeli

3. **Terminal Persistence = Efisiensi Operasional**
   - Tidak perlu setup ulang setiap shift
   - Staff ganti, terminal tetap

4. **Configuration-Driven = Mudah Customize**
   - Ubah setting tanpa coding
   - Adaptable untuk berbagai toko

### Manfaat Bisnis:

- 💰 **Mengurangi komplain** customer
- ⚡ **Mempercepat transaksi** (no konfirmasi manual)
- 👥 **Meningkatkan kepercayaan** customer
- 🔄 **Gampang ganti shift** kasir (no setup ulang)
- 📈 **Brand image modern** & profesional

---

## 📚 Selanjutnya Baca:

1. [02_ARSITEKTUR_TEKNIS.md](./02_ARSITEKTUR_TEKNIS.md) - Detail teknis implementasi
2. [03_DUAL_DISPLAY_SYNC.md](./03_DUAL_DISPLAY_SYNC.md) - Deep dive sync mechanism
3. [04_TROUBLESHOOTING.md](./04_TROUBLESHOOTING.md) - Problem solving guide

---

**Dibuat**: 2026-02-07  
**Versi**: 1.0  
**Status**: ✅ Production Ready
