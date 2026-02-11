# FoodLife POS - Dokumentasi Teknis Lengkap

> **Tujuan dokumen**: Agar developer baru atau LLM lain bisa memahami detail aplikasi POS ini tanpa harus eksplorasi dari awal.
>
> **Terakhir diupdate**: 2026-02-11 (added Kitchen Agent HTTP health server & widget Alpine.js rewrite)

---

## 1. Overview & Tech Stack

### Konsep Aplikasi
FoodLife POS adalah aplikasi Point of Sale untuk restoran/food court yang berjalan di **Edge Server** (server lokal di toko). Setiap toko punya server sendiri yang sinkronisasi dengan Head Office (HO).

### Tech Stack
| Layer | Teknologi |
|-------|-----------|
| Backend | Django 5.x (Python) |
| Frontend Dynamic | HTMX (server-rendered partials) |
| Frontend Reactive | Alpine.js (client-side state) |
| CSS | Tailwind CSS (utility-first) |
| Database | SQLite / PostgreSQL (per Edge Server) |
| Image Storage | MinIO (S3-compatible, self-hosted) |
| Print System | Kitchen Printer Agent (Docker service + HTTP health server port 5001) |

### Target Environment
- **Resolusi**: 1024x768 (POS terminal touchscreen)
- **Network**: LAN (offline-first, tidak butuh internet)
- **Browser**: Chromium-based (via POS Launcher Qt)
- **OS**: Linux (Edge Server)

### Multi-Tenant Hierarchy
```
Company (Holding)
  └── Brand (Merek F&B, misal: "Solaria", "Ichiban")
       └── Store (Toko fisik, 1 per Edge Server)
            └── POSTerminal (Mesin kasir, bisa banyak per Store)
```
Satu Store bisa punya banyak Brand (konsep food court via `StoreBrand` model).

---

## 2. Layout POS (3-Column Fixed Width)

```
┌──────────┬──────────────────────────────┬────────────────┐
│ SIDEBAR  │       MAIN CONTENT           │  BILL PANEL    │
│  160px   │         576px                │    288px       │
│          │                              │                │
│ - Logo   │ [Search Bar] [Shift Status]  │ [Bill Header]  │
│ - User   │ [Category Filter]            │ [Bill Items]   │
│ - Menu   │ [Product Grid - scrollable]  │ [Totals]       │
│ - Tables │                              │ [Action Btns]  │
│ - Shift  │                              │ [Pay Button]   │
│ - Recent │ [Footer: Store/Terminal Info] │                │
│ -Kitchen │                              │                │
│  Printer │                              │                │
│ -Receipt │                              │                │
│  Printer │                              │                │
│ - Logout │                              │                │
└──────────┴──────────────────────────────┴────────────────┘
                      Total: 1024px
```

---

## 3. File Structure (Templates)

### Main Template
```
templates/pos/main.html          ← Skeleton (~198 baris), include semua partial
```

### Partial Templates
```
templates/pos/partials/
├── bill_panel.html              ← Panel kanan: info bill, items summary, action buttons
├── bill_items.html              ← Daftar item dalam bill (HTMX swappable)
├── product_card.html            ← Satu kartu produk (di-include dari product_grid)
├── product_grid.html            ← Grid produk + JS quickAdd/quickRemove
├── payment_modal.html           ← Modal pembayaran (Alpine.js component)
├── confirm_hold_modal.html      ← Modal konfirmasi hold bill
├── move_table_modal.html        ← Modal pindah meja
├── merge_bills_modal.html       ← Modal gabung bill
├── split_bill_modal.html        ← Modal split bill
├── recent_bills_modal.html      ← Modal 15 bill terakhir
├── stock_warning_modal.html     ← Modal warning stok habis saat send to kitchen
│
├── main/                        ← Sub-partials untuk main.html
│   ├── sidebar.html             ← Sidebar navigasi (160px)
│   ├── category_filter.html     ← Filter kategori 2 level
│   ├── header_search.html       ← Search bar + shift indicator
│   ├── pos_styles.html          ← CSS custom (animasi, typography)
│   ├── shift_overlay.html       ← Overlay "Shift Not Active"
│   ├── footer_info.html         ← Footer company/terminal info
│   ├── kitchen_printer_widget.html ← Widget status printer dapur (sidebar)
│   │
├── printer_status.html             ← Widget status receipt printer (sidebar, heartbeat)
│
│   └── js/                      ← JavaScript modules
│       ├── alpine_components.html    ← Alpine: posModal(), quickOrder()
│       ├── shift_management.html     ← Buka/tutup shift, load terminal config
│       ├── htmx_handlers.html        ← Event handler HTMX
│       ├── modal_functions.html      ← closeModal(), showToast(), reprint
│       ├── floor_plan.html           ← Modal floor plan (denah meja)
│       ├── keyboard_shortcuts.html   ← Shortcut F1-F4, F8, Esc
│       └── launcher_integration.html ← Integrasi POS Launcher Qt
```

### Floor Plan (standalone page)
```
templates/tables/
├── floor_plan.html              ← Halaman floor plan lengkap (Alpine.js + JS)
└── partials/
    └── table_grid.html          ← Grid meja sederhana
```

### JavaScript Include Order (di main.html)
Urutan penting karena ada dependency antar file:
1. `launcher_integration.html` - Defines `isKioskMode()`, `updateCustomerDisplay()`
2. `alpine_components.html` - Defines `posModal()`, `quickOrder()`
3. `shift_management.html` - Uses `openShiftModal()`, `loadTerminalConfig()`
4. `htmx_handlers.html` - Uses `isKioskMode()`, `updateCustomerDisplay()`
5. `modal_functions.html` - Standalone: `closeModal()`, `showToast()`
6. `floor_plan.html` - Standalone: `openFloorPlanModal()`, `closeFloorPlanModal()`
7. `keyboard_shortcuts.html` - Event listeners (harus terakhir)

---

## 4. Models (Database)

### Bill Flow (apps/pos/models.py)

#### Bill
```
Status: open → hold → open → paid/cancelled/void
Fields: bill_number, brand, store, table, terminal, bill_type, status,
        customer_name, guest_count, subtotal, discount, tax, service_charge, total,
        member_code, member_name, notes, created_by, closed_by
```

#### BillItem
```
Status: pending → sent → preparing → ready → served
Fields: bill, product, quantity, unit_price, modifier_price, total,
        notes, modifiers(JSON), printer_target, status, is_void, void_reason,
        split_group, created_by
```

#### Payment
```
Methods: cash, card, qris, transfer, ewallet, voucher
Fields: bill, method, amount, reference, created_by
```
Satu bill bisa punya banyak payment (split payment).

#### BillLog
```
Actions: open, add_item, void_item, update_qty, hold, resume,
         send_kitchen, payment, close, completed, cancel, discount, reprint_receipt
Fields: bill, action, details(JSON), user, created_at
```
Audit trail untuk semua aksi pada bill.

#### PrintJob
```
Status: pending → fetched → printing → completed/failed
Types: receipt, kitchen, report, reprint
Fields: job_uuid, terminal_id, bill, job_type, status, content(JSON)
```
Antrian print job untuk Kitchen Printer Agent.

### Table Management (apps/tables/models.py)

#### TableArea
```
Fields: name, brand, company, store, floor_width, floor_height, floor_image,
        sort_order, is_active
```
Area/zone dalam restoran (misal: Indoor, Outdoor, VIP).

#### Table
```
Status: available, occupied, reserved, billing, dirty
Fields: number, area, capacity, status, pos_x, pos_y, shape(rect/round/rectangle),
        table_group, qr_code, is_active
```
Posisi meja (pos_x, pos_y) di-setting dari HO, POS hanya menampilkan.

#### TableGroup
```
Fields: main_table, brand, created_by
```
Untuk join/gabung meja (beberapa meja jadi satu group).

### Store Product Stock (apps/pos/models.py)

#### StoreProductStock
```
Table: pos_store_product_stock
Relasi: 1-to-1 dengan core_product (tanpa FK constraint)
Unique Together: [product_sku, brand]
```

**Latar Belakang:**
Table `core_product` di-sync harian dari HO (Head Office) via DELETE+INSERT atau update_or_create.
Field `track_stock` dan `stock_quantity` di core_product akan ter-overwrite setiap sync.
Oleh karena itu, dibutuhkan table terpisah (`pos_store_product_stock`) yang hanya di-maintain di Store level.

**Design Decisions:**
- `product_id` adalah **UUIDField biasa** (bukan ForeignKey) → survive DELETE+INSERT sync dari HO
- `product_sku` + `brand` sebagai **stable identifier** untuk re-match product setelah sync
- Hanya produk yang **perlu di-manage stock-nya** yang dimasukkan ke table ini
- Produk yang **TIDAK ADA** di table ini → dianggap **selalu available** (no stock tracking)

**Fields:**
```
product_id      : UUID (reference ke core_product.id, bukan FK)
product_sku     : CharField (stable identifier dari HO)
product_name    : CharField (display name, copy dari product)
brand           : ForeignKey → Brand
daily_stock     : Decimal (stok harian yang di-set oleh staff)
sold_qty        : Decimal (jumlah terjual hari ini, auto-increment)
low_stock_alert : Integer (threshold warning, default=5)
is_active       : Boolean (soft delete)
last_reset_date : Date (tanggal terakhir reset stok)
```

**Properties:**
- `remaining_stock` → `daily_stock - sold_qty`
- `is_out_of_stock` → `remaining_stock <= 0`
- `is_low_stock` → `0 < remaining_stock <= low_stock_alert`

**Methods:**
- `deduct_stock(qty)` → Tambah sold_qty (dipanggil saat send_to_kitchen)
- `restore_stock(qty)` → Kurangi sold_qty (dipanggil saat void item yang sudah sent)
- `reset_daily(new_stock=None)` → Reset sold_qty=0, update daily_stock jika ada
- `sync_product_id()` → Re-match product_id berdasarkan sku+brand setelah HO sync

**Alur Stock:**
```
Staff set daily_stock (misal: 50)
  → Kasir send to kitchen → sold_qty +1 (remaining: 49)
  → Kasir send to kitchen → sold_qty +1 (remaining: 48)
  → Kasir void item (yang sudah sent) → sold_qty -1 (remaining: 49)
  → ...
  → remaining = 0 → "Out of Stock" di product card
  → Besok: staff reset daily → sold_qty = 0, daily_stock tetap/update
```

### Core Models (apps/core/models.py)

#### Product
```
Fields: brand, company, name, sku, category, price, cost, image,
        printer_target, track_stock, stock_quantity, low_stock_alert,
        is_active, sort_order
```

#### Category
```
Fields: name, brand, parent(self-FK), sort_order, is_active, icon
```
Mendukung 2 level: Parent Category → Subcategory.

#### POSTerminal
```
Fields: store, brand, terminal_code(unique), device_type, ip_address,
        printer configs, display configs, payment configs, is_active
```
Konfigurasi per mesin kasir (auto-print, paper width, dll).

#### Store (Singleton per Edge Server)
```
Fields: company, store_code, store_name, address, phone
Method: get_current() → returns single Store instance
```

#### Member (dari CRM eksternal)
```
Fields: company, member_code, full_name, phone, tier, points, point_balance
```

---

## 5. URL Patterns (apps/pos/urls.py)

### Main
| URL | View | Method | Keterangan |
|-----|------|--------|------------|
| `/pos/` | `pos_main` | GET | Halaman utama POS |
| `/pos/products/` | `product_list` | GET | Daftar produk |

### Bill CRUD
| URL | View | Method | Keterangan |
|-----|------|--------|------------|
| `/pos/bill/open/` | `open_bill` | POST | Buat bill baru |
| `/pos/bill/<id>/hold/` | `hold_bill` | POST | Hold bill |
| `/pos/bill/<id>/hold-modal/` | `hold_modal` | GET | Modal konfirmasi hold |
| `/pos/bill/<id>/resume/` | `resume_bill` | POST | Resume bill dari hold |
| `/pos/bill/<id>/cancel/` | `cancel_bill` | POST | Batalkan bill |
| `/pos/bill/<id>/cancel-empty/` | `cancel_empty_bill` | POST | Batalkan bill kosong |
| `/pos/bill/<id>/send-kitchen/` | `send_to_kitchen` | POST | Kirim ke dapur |

### Item Operations
| URL | View | Method | Keterangan |
|-----|------|--------|------------|
| `/pos/bill/<id>/product/<uuid>/add-modal/` | `add_item_modal` | GET | Modal pilih modifier |
| `/pos/bill/<id>/add-item/` | `add_item` | POST | Tambah item + modifier |
| `/pos/bill/<id>/product/<uuid>/quick-add/` | `quick_add_product` | POST | Quick add tanpa modifier |
| `/pos/bill/<id>/product/<uuid>/quick-remove/` | `quick_remove_product` | POST | Quick remove |
| `/pos/item/<id>/void/` | `void_item` | POST | Void item |
| `/pos/item/<id>/update-qty/` | `update_item_qty` | POST | Update quantity |
| `/pos/item/<id>/edit/` | `edit_item_modal` | GET | Modal edit item |

### Payment
| URL | View | Method | Keterangan |
|-----|------|--------|------------|
| `/pos/bill/<id>/payment/` | `payment_modal` | GET | Modal pembayaran |
| `/pos/bill/<id>/pay/` | `process_payment` | POST | Proses bayar |

### Bill Management
| URL | View | Method | Keterangan |
|-----|------|--------|------------|
| `/pos/bill/<id>/split/` | `split_bill_modal` | GET | Modal split |
| `/pos/bill/<id>/merge/` | `merge_bills_modal` | GET | Modal merge |
| `/pos/bill/<id>/move-table/` | `move_table_modal` | GET | Modal pindah meja |
| `/pos/bill/<id>/transfer/` | `transfer_bill_modal` | GET | Modal transfer |
| `/pos/held/` | `held_bills` | GET | Daftar bill hold |
| `/pos/recent/` | `recent_bills` | GET | 15 bill terakhir |

### Shift & Session
| URL | View | Method | Keterangan |
|-----|------|--------|------------|
| `/pos/shift/open-form/` | `shift_open_form` | GET | Form buka shift |
| `/pos/shift/open/` | `shift_open` | POST | Buka shift |
| `/pos/shift/close-form/` | `shift_close_form` | GET | Form tutup shift |
| `/pos/shift/close/` | `shift_close` | POST | Tutup shift |
| `/pos/shift/status/` | `shift_status` | GET | Status shift (auto-refresh 30s) |
| `/pos/shift/my-dashboard/` | `shift_my_dashboard` | GET | Dashboard kasir |

### Stock Management (apps/management/urls.py)
| URL | View | Method | Keterangan |
|-----|------|--------|------------|
| `/management/stock/` | `stock_management` | GET | Dashboard & list stock tracking |
| `/management/stock/add/` | `stock_add_product` | POST | Tambah produk ke stock tracking |
| `/management/stock/<id>/update/` | `stock_update` | POST | Update daily_stock/low_stock_alert |
| `/management/stock/<id>/reset/` | `stock_reset_daily` | POST | Reset sold_qty satu produk |
| `/management/stock/<id>/remove/` | `stock_remove` | POST | Soft delete (is_active=False) |
| `/management/stock/reset-all/` | `stock_reset_all` | POST | Reset semua produk sekaligus |
| `/management/stock/sync-product-ids/` | `stock_sync_product_ids` | POST | Re-match product_id setelah HO sync |

### Table Management (apps/tables/urls.py)
| URL | View | Keterangan |
|-----|------|------------|
| `/tables/` | `table_map` | Floor plan (standalone) |
| `/tables/<uuid>/open/` | `open_table` | Buka meja → buat bill |
| `/tables/<uuid>/clean/` | `clean_table` | Tandai meja bersih |
| `/tables/update-position/` | `update_table_position` | Update posisi meja |
| `/tables/join/` | `join_tables` | Gabung meja |

---

## 6. Fitur-Fitur POS

### 6.1 Keyboard Shortcuts
| Key | Aksi | Kondisi |
|-----|------|---------|
| **F1** | Send to Kitchen | Ada bill aktif |
| **F2** | Buka Payment Modal | Ada bill aktif |
| **F3** | Hold Bill | Ada bill aktif |
| **F4** | Choose Table (Floor Plan) | Tidak ada bill aktif |
| **F8** | Cancel Bill | Ada bill aktif |
| **Esc** | Tutup modal/floor plan | Modal/floor plan terbuka |

Shortcut di-disable saat modal atau floor plan sedang terbuka. Implementasi di `keyboard_shortcuts.html`.

### 6.2 Toast Notifications
Semua `alert()` sudah diganti dengan `showToast(message, type)`. Fungsi didefinisikan di `modal_functions.html`.
```javascript
showToast('Pesan sukses', 'success');  // Hijau
showToast('Pesan error', 'error');     // Merah
showToast('Pesan warning', 'warning'); // Kuning
showToast('Pesan info', 'info');       // Biru
```

### 6.3 Product Card
File: `product_card.html`

**Context Variables:**
- `product` - Object produk (nama, harga, foto, stok, dll)
- `bill` - Object bill aktif (None jika belum ada)
- `bill_items_dict` - Dictionary {product_id: quantity} untuk produk di bill
- `stock_status_dict` - Dictionary {product_id: {remaining, daily_stock, is_out, is_low}} dari **StoreProductStock**
- `minio_endpoint` / `minio_bucket` - URL MinIO untuk load gambar

**Stock Logic (dari StoreProductStock):**
```django
{% with stock_status_dict|get_item:product.id as stock_info %}
  stock_info = None → produk TIDAK di-track → selalu available
  stock_info.is_out = True → "Out of Stock" overlay + tombol disabled
  stock_info.is_low = True → "Low: X" badge di pojok kanan atas
{% endwith %}
```

**States:**
1. **Ada bill + stok tersedia + sudah di cart** → Border hijau + stepper quantity (-/+)
2. **Ada bill + stok tersedia + belum di cart** → Tombol "Add to Dish" hijau
3. **Ada bill + stok habis (dari StoreProductStock)** → Overlay "Out of Stock" + tombol disabled
4. **Tidak ada bill** → Opacity rendah + tombol disabled

NOTE: Stok dicek dari `stock_status_dict` (StoreProductStock). Jika produk TIDAK ADA di dict → selalu available.

**Fitur:**
- Gambar dari MinIO (primary), Django ImageField (fallback), atau placeholder SVG
- Badge "Popular" / "25% Off" di pojok kiri atas
- Harga format Rupiah: `Rp. {{ product.price|rupiah }}` (comma separator)
- Badge stok: "Out of Stock" (merah overlay) atau "Low: X" (amber badge) — data dari StoreProductStock
- Badge Veg/Non-Veg berdasarkan nama kategori
- Quick add/remove via JavaScript (`quickAddProduct`, `quickRemoveProduct`)
- Flash hijau saat add, flash merah saat remove (animasi di `product_grid.html`)

### 6.4 Bill Panel
File: `bill_panel.html`

**Header:** Color-coded berdasarkan status bill:
- Hijau (gradient green) = Open / normal
- Kuning (gradient amber) = Hold
- Biru (gradient blue) = Sent to Kitchen
- Merah (gradient red) = Void/Cancelled

**Action Buttons (grid 4 kolom):**
| Tombol | Shortcut | Aksi |
|--------|----------|------|
| Hold | F3 | Simpan bill sementara |
| Void | - | Batalkan seluruh bill |
| Move | - | Pindahkan ke meja lain |
| Merge | - | Gabung dengan bill lain |

**Tombol Utama:**
- **Send to Kitchen** (F1) - Kirim pesanan ke dapur
- **Payment** (F2) - Buka modal pembayaran

### 6.5 Payment Modal
File: `payment_modal.html`

**Metode Pembayaran:** Cash, Card, QRIS, E-Wallet, Transfer, Voucher, Debit
(difilter berdasarkan konfigurasi terminal)

**Fitur:**
- **Numpad visual** (0-9, 00, 000, DEL, C)
- **Quick amount buttons** (Cash only): Exact, 50K, 100K, Round up
- **Split payment** - Bisa bayar dengan beberapa metode
- **Real-time validation** - Warning jika amount > remaining (non-cash)
- **Change display** - Tampil otomatis jika bayar cash lebih
- **Customer display integration** - Update real-time ke layar customer

### 6.6 Floor Plan (Denah Meja)
Files: `templates/pos/partials/main/js/floor_plan.html` (modal POS), `templates/tables/floor_plan.html` (standalone)

**Cara Kerja:**
1. User klik "Tables" di sidebar atau tekan F4
2. Modal floor plan terbuka (overlay di atas area konten)
3. Fetch HTML dari endpoint `/tables/` (table_map view)
4. Parse response, inject konten ke modal
5. Alpine.js parse JSON data meja, render ke canvas
6. User klik meja → buat bill baru

**Data Meja (JSON):**
```json
{
  "id": "uuid", "number": "1", "capacity": 4,
  "status": "available|occupied|reserved|billing|dirty",
  "pos_x": 100, "pos_y": 200, "shape": "rect|round|rectangle",
  "is_joined": false,
  "bill_number": "", "bill_total": 0, "bill_created_at": "",
  "guest_count": 0, "items_count": 0, "bill_status": ""
}
```

**Visual Status Meja:**
| Status | Warna | Keterangan |
|--------|-------|------------|
| Available | Hijau | Meja kosong, bisa dipilih |
| Occupied | Merah | Ada bill aktif (open) |
| Hold | Amber | Bill di-hold |
| Billing | Amber | Sedang proses bayar |
| Dirty | Abu-abu | Perlu dibersihkan |
| Joined | Purple badge | Meja gabungan (group) |

**Fitur tambahan:**
- Elapsed time sejak bill dibuka (misal: "45m", "1h30m")
- Total bill singkat (misal: "150K", "1.2jt")
- Badge jumlah item di pojok kanan atas
- Tooltip detail bill saat hover
- HOLD badge pada meja yang bill-nya di-hold

**PENTING (L10N):**
Template JSON meja harus dibungkus `{% localize off %}...{% endlocalize %}` karena Django L10N Indonesia menggunakan `.` sebagai separator ribuan yang merusak JSON (1200 → 1.200). Load tag: `{% load l10n %}`.

### 6.7 Category Filter
File: `category_filter.html`

- 2 level: Parent Category → Subcategory
- Tombol "All" selalu visible di kiri
- Active category highlighted dengan gradient biru
- Scroll horizontal jika overflow
- Fade effect di ujung kiri/kanan saat overflow

### 6.8 Recent Orders
File: `recent_bills_modal.html`

- Tampilkan 15 bill terakhir (paid/completed)
- Info: bill number, meja, total, status, waktu
- Quick actions: reprint receipt, view detail
- Diakses dari sidebar "Recent" (HTMX modal)

### 6.9 Shift Management
Files: `shift_management.html`, sidebar shift status

- **Buka Shift**: Input initial cash, mulai kerja
- **Tutup Shift**: Hitung total, rekonsiliasi, print laporan
- **Status**: Auto-refresh setiap 30 detik di sidebar
- **Dashboard**: Ringkasan shift kasir saat ini
- **Reprint**: Cetak ulang laporan rekonsiliasi

### 6.10 Quick Order (Takeaway)
Files: `alpine_components.html` (`quickOrder()`)

- Buat bill takeaway tanpa pilih meja
- Auto-generate queue number harian
- Tampil di Queue Display untuk pickup

### 6.11 Store Product Stock Management
Files: `apps/pos/models.py` (StoreProductStock), `apps/management/views.py`, `templates/management/stock_management.html`

**Konsep:**
Table terpisah dari `core_product` untuk manage stok harian di level Store.
Dibutuhkan karena `core_product` di-sync harian dari HO dan field stock-nya ter-overwrite.

**Halaman Management** (`/management/stock/`):
- Dashboard stats: total tracked, out of stock, low stock
- Form tambah produk ke tracking (dropdown dari produk yang belum di-track)
- Tabel stock: inline edit daily_stock, reset individual, remove
- Filter by brand (via `context_brand_id` session)
- Bulk reset all (reset sold_qty semua produk)
- Sync product IDs (re-match setelah HO sync)

**Integrasi di POS:**
1. **pos_main view** → Build `stock_status_dict` dari StoreProductStock, pass ke context
2. **product_card.html** → Cek `stock_status_dict` untuk tampilkan badge Out of Stock / Low Stock
3. **send_to_kitchen** → Cek stock sebelum kirim, tampilkan warning modal jika ada item habis
   - Kasir bisa pilih "Cancel" atau "Continue Anyway" (force=1)
   - Setelah berhasil kirim → deduct stock (`sold_qty += quantity`)
4. **void_item** → Restore stock jika item yang di-void sudah pernah dikirim ke dapur (`sold_qty -= quantity`)

**Stock Warning Modal** (`stock_warning_modal.html`):
- Muncul saat send_to_kitchen jika ada item yang stoknya habis di StoreProductStock
- List item dengan status: HABIS (merah) atau sisa stok (kuning)
- Tombol "Cancel" dan "Continue Anyway" (keduanya grey background, font hitam)
- Header: bg-gray-100, icon amber, judul & subtitle font hitam
- Layout: max-w-sm, flex column max-height 90vh, content scrollable, buttons flex-shrink-0
- Menggunakan `HX-Retarget: #modal-container` agar response ditampilkan sebagai modal (bukan replace bill panel)

### 6.12 Printer Status Widgets (Sidebar)
Dua widget status printer ditampilkan di sidebar kiri, masing-masing dengan flyout panel ke kanan.

**Receipt Printer Widget** (`templates/pos/printer_status.html`):
- Cek status POS Launcher service via `GET http://localhost:5000/health`
- Cek status **hardware printer fisik** via `GET http://localhost:5000/api/printer/status`
- Alpine.js component (`printerStatusWidget()`)
- Auto-check setiap 10 detik (selalu aktif, bukan hanya saat flyout terbuka)
- **Two-level check**: Service up? → Printer hardware ready?
- **Status levels**:
  - Hijau (online): Service running + printer hardware ready (status=0)
  - Amber (warning): Service running + printer ada warning (cover open, toner low, power save)
  - Merah (offline): Service not running ATAU printer error/offline/paper out/not available
- **Heartbeat indicator**: Saat offline, status dot di sidebar berkedip merah (heartbeat pulse + ripple animation)
- **Flyout detail**: Service status, printer hardware status, device name, platform, warning/error messages
- Test Print via `POST http://localhost:5000/api/print`
- AbortController timeout: 3 detik untuk health check, 5 detik untuk printer status (WMI butuh waktu lebih)

**Deteksi Hardware Printer (Backend - `pos_launcher_qt/local_api.py`):**

*Windows (`_get_printer_status_windows`):*
1. `win32print.GetPrinter(handle, 2)` → query spooler untuk status bitmask
2. Jika status=0 (spooler bilang OK) → **verifikasi via WMI** karena spooler sering cache status lama
3. `_wmi_printer_check(printer_name)` → query `Win32_Printer.WorkOffline` via `win32com.client`
   - `WorkOffline=True` → printer USB dicabut/disconnected → status "offline"
   - `PrinterStatus=7` → printer offline
   - Menggunakan `pythoncom.CoInitialize()`/`CoUninitialize()` untuk thread safety di Flask
4. Jika WMI gagal → fallback ke hasil GetPrinter (graceful degradation)

*Linux (`_get_printer_status_linux`):*
1. `pycups` library → `cups.Connection().getPrinters()`
2. CUPS printer states: `3`=idle (ready), `4`=printing, `5`=stopped (offline/error)
3. Membaca `printer-state-message` dan `printer-state-reasons` untuk detail error

**Printer status flags** yang bisa dideteksi (Windows via win32print bitmask):
- Error flags: `error`, `paper_jam`, `paper_out`, `paper_problem`, `offline`, `not_available`, `no_toner`, `user_intervention`
- Warning flags: `door_open`, `toner_low`, `power_save`
- Busy flags: `busy`, `printing`, `initializing`, `warming_up`

**Kitchen Printer Widget** (`templates/pos/partials/main/kitchen_printer_widget.html`):
- Alpine.js component (`kitchenPrinterWidget()`) — matching Receipt Printer widget pattern
- **Primary**: Cek status Kitchen Agent via HTTP health server (`GET http://<host>:5001/health`)
- **Secondary**: Cek status printer jaringan via agent (`GET http://<host>:5001/api/printers/status`)
- **Fallback**: Jika agent unreachable → cek via Django endpoint `pos:kitchen_printer_status` (data dari DB, mungkin stale)
- **Agent URL discovery**: `http://` + `window.location.hostname` + `:5001` (default), override via `localStorage.getItem('kitchen_agent_url')`
- Auto-check setiap 10 detik (selalu aktif, bukan hanya saat flyout terbuka)
- **Two-level check**: Agent running? → Network printers reachable?
- **Status levels**:
  - Hijau (online): Agent running + semua printer online
  - Amber (degraded): Agent running + sebagian printer offline
  - Merah (offline): Agent tidak berjalan
- **Heartbeat indicator**: Saat offline, status dot di sidebar berkedip merah (heartbeat pulse + ripple animation)
- **Flyout detail**: Agent status (Running/Offline), agent name, uptime, tickets processed, printer list per-station
- **Offline banner**: Peringatan merah "Kitchen Agent tidak berjalan" dengan catatan data dari database
- Tidak ada tombol Start/Stop agent (removed — agent dikelola via systemd/supervisor di server)

**Kitchen Agent HTTP Health Server** (`kitchen_printer_agent/kitchen_agent.py`):
- Built-in HTTP server di Kitchen Printer Agent (Python stdlib `http.server`, zero dependencies)
- Default port: 5001 (configurable via `kitchen_agent_config.json` atau env `HEALTH_SERVER_PORT`)
- Jalan di daemon thread (`threading.Thread(daemon=True)`) — tidak block main polling loop
- CORS headers (`Access-Control-Allow-Origin: *`) untuk browser cross-origin access
- **Endpoints**:
  - `GET /health` → `{"status":"ok","agent_name":"...","uptime_seconds":...,"tickets_processed":...,"stations":[...]}`
  - `GET /api/printers/status` → `{"printers":[{"station_code":"...","printer_ip":"...","is_online":true,...}],"last_check":"..."}`
- Printer health cache: In-memory dict, populated oleh existing `check_printers_health()` TCP socket checks (interval dari config)
- **Django view fallback** (`pos:kitchen_agent_status`): Try `host.docker.internal:5001` (dari Docker container ke host network), lalu `127.0.0.1:5001` (non-Docker), fallback ke `systemctl is-active` (Linux only)

**Deployment** (via Docker Compose):
- Kitchen Agent dijalankan sebagai Docker service `kitchen_agent` di `docker-compose.yml`
- Reuse image utama (sama dengan Django) — tidak perlu install Python terpisah di server
- Cukup `docker compose up -d` untuk start semua service termasuk Kitchen Agent
- **`network_mode: host`** — container share host network stack, bisa langsung reach printer LAN (TCP socket ke IP:9100)
- DB connection via `localhost:5433` (host-mapped port), bukan Docker DNS `edge_db:5432`
- Environment variables: `DB_HOST=localhost`, `DB_PORT=5433`, `AGENT_NAME`, `STATION_IDS`, `HEALTH_SERVER_PORT`
- Port 5001 langsung tersedia di host (tanpa port mapping, karena host network mode)
- `restart: unless-stopped` — auto-restart on crash (menggantikan systemd)

**Docker Network & Printer LAN (PENTING):**
- Printer kitchen menggunakan IP di range `172.17.x.x` (contoh: 172.17.10.36, 172.17.10.114)
- Docker default bridge (`docker0`) secara default menggunakan subnet `172.17.0.0/16` — **conflict!**
- Traffic ke `172.17.10.x` di-capture oleh `docker0` interface, bukan dikirim ke LAN fisik
- **Fix 1**: Docker Desktop → Settings → Docker Engine → tambah `"bip": "172.30.0.1/16"` di `daemon.json`
- **Fix 2**: `docker-compose.yml` → `pos_network` diberi explicit subnet `172.28.0.0/16` (hindari auto-allocate 172.17.x.x)
- Setelah fix, routing: container → VM default gateway (192.168.65.1) → Windows host → LAN → printer
- **Catatan**: Jika LAN printer tidak di range 172.17.x.x, fix ini tidak diperlukan

**Multi-Brand Food Court Support:**
- Setiap brand punya `StationPrinter` sendiri per station (misal: Brand A punya kitchen printer 192.168.1.10, Brand B punya 192.168.1.20)
- `KitchenTicket` menyimpan `brand_id` — ticket tahu milik brand mana
- Agent routing: `get_printer_for_station(station_code, brand_id)` — lookup printer berdasarkan station + brand
- Satu agent bisa handle semua brand (`STATION_IDS=1,2,3,...`) atau subset tertentu
- Tidak ada cross-brand routing — Brand A ticket selalu ke Brand A printer

---

## 7. Pola Teknis (Patterns)

### 7.1 HTMX Pattern
Mayoritas interaksi menggunakan HTMX untuk server-rendered partials:
```html
<!-- Trigger: klik tombol → GET modal → inject ke #modal-container -->
<button hx-get="{% url 'pos:payment_modal' bill.id %}"
        hx-target="#modal-container"
        hx-swap="innerHTML">
    Payment
</button>

<!-- Container modal (selalu ada di main.html) -->
<div id="modal-container" style="z-index:9999;"></div>
```

### 7.2 Alpine.js Pattern
Untuk state management client-side (payment modal, floor plan, dll):
```html
<div x-data="paymentModal()" x-init="init()">
    <span x-text="formattedTotal"></span>
    <button @click="addPayment()">Pay</button>
</div>
```

### 7.3 Bill Panel Refresh
Setelah aksi pada bill (add item, void, dll), bill panel di-refresh via HTMX:
```python
# Backend: return rendered bill panel + trigger event
response = render_bill_panel(request, bill)
return trigger_client_event(response, 'billUpdated')
```
```javascript
// Frontend: listen event → refresh product grid
document.body.addEventListener('billUpdated', function() {
    htmx.ajax('GET', '/pos/products/', {target: '#product-grid'});
});
```

### 7.4 Session Management
- `active_bill_id` disimpan di Django session
- Saat buka POS: cek `request.GET.get('bill_id')` atau `session.get('active_bill_id')`
- Saat hold/cancel: `session.pop('active_bill_id', None)`
- Redirect ke `/pos/` (bersih, tanpa query param) setelah hold/cancel

### 7.5 Template Tag Custom
File: `apps/pos/templatetags/currency_filters.py`
```python
{{ product.price|rupiah }}    → "200,000" (comma separator, no decimals)
{{ dict|get_item:key }}       → dict[key] (akses dictionary di template)
```

### 7.6 MinIO Image URL
```
{{ minio_endpoint }}/{{ minio_bucket }}/{{ photo.object_key }}?v={{ photo.checksum|slice:':8' }}
```
- `minio_endpoint`: Dinamis berdasarkan IP yang diakses (bukan localhost)
- `checksum`: Cache-busting agar browser refresh jika gambar berubah

---

## 8. Flow Utama

### 8.1 Flow Dine-In
```
1. Kasir login → POS main (empty bill state)
2. Klik "Choose Table" (F4) atau "Tables" di sidebar
3. Floor plan modal terbuka → pilih meja available
4. Bill baru dibuat (status: open, table: occupied)
5. Pilih produk dari grid → klik "Add to Dish" atau quick-add
6. Jika ada modifier → modal modifier muncul → pilih → add
7. Review bill di panel kanan
8. Klik "Send to Kitchen" (F1)
   8a. Jika ada item out-of-stock (StoreProductStock) → warning modal muncul
   8b. Kasir pilih "Cancel" atau "Continue Anyway"
   8c. Item dikirim ke printer dapur, stock di-deduct (sold_qty += qty)
9. Item status: pending → sent
10. Klik "Payment" (F2) → modal payment
11. Pilih metode, input nominal, klik "Pay Now"
12. Bill status: paid, table: available
13. Receipt di-print otomatis (jika auto_print aktif)
```

### 8.2 Flow Takeaway
```
1. Kasir di POS main (empty bill state)
2. Klik "Quick Order" → modal quick order
3. Isi nama customer (opsional) → create
4. Bill baru dibuat (type: takeaway, queue_number auto)
5. Tambah produk → send to kitchen → payment
6. Queue number tampil di Queue Display untuk pickup
```

### 8.3 Flow Hold & Resume
```
Hold:
1. Ada bill aktif → klik "Hold" (F3)
2. Modal konfirmasi → isi reason (opsional) → Hold Bill
3. Bill status: hold, session cleared
4. Redirect ke /pos/ (empty state)

Resume:
1. Klik sidebar "Held Bills" atau icon di shift status
2. List bill yang di-hold muncul
3. Klik resume → bill aktif kembali (status: open)
```

### 8.4 Flow Split Payment
```
1. Bill total Rp 200,000
2. Buka Payment → pilih Cash → input 100,000 → "Add Payment"
3. Payment #1 ditambahkan ke list
4. Remaining: 100,000
5. Pilih QRIS → input 100,000 → "Complete Payment"
6. Bill paid dengan 2 metode pembayaran
```

---

## 9. Konfigurasi Penting

### Django Settings (terkait POS)
- `USE_L10N = True` → Format angka sesuai locale Indonesia
- **PERHATIAN**: Gunakan `{% localize off %}` di template yang output JSON/angka mentah

### Terminal Config (POSTerminal model)
- `auto_print_receipt`: Auto-print receipt saat payment selesai
- `auto_print_kitchen_order`: Auto-print ke dapur saat send to kitchen
- `print_checker_receipt`: Print checker receipt untuk verifikasi
- `default_payment_methods`: JSON array metode pembayaran yang aktif
- `enable_customer_display`: Aktifkan layar customer
- `receipt_paper_width`: Lebar kertas (58mm / 80mm)

---

## 10. Catatan untuk Developer

### Hal yang Perlu Diperhatikan
1. **L10N di JSON template**: Selalu bungkus JSON output dengan `{% localize off %}` untuk mencegah format angka Indonesia (1.200 vs 1200) merusak JSON
2. **Session `active_bill_id`**: Harus di-clear saat hold/cancel, dan redirect ke `/pos/` (bukan reload) untuk menghindari `?bill_id=` di URL yang me-reactivate bill
3. **Bill status filter**: `pos_main` query menggunakan `status__in=['open', 'hold']` - bill hold masih bisa diakses via URL parameter
4. **MinIO endpoint**: Dinamis berdasarkan IP request, bukan hardcoded localhost
5. **Keyboard shortcuts**: Di-disable saat modal/floor plan terbuka (cek `#modal-container` dan `#floor-plan-modal`)
6. **HTMX swap**: Mayoritas menggunakan `hx-target="#modal-container"` untuk modal, `hx-target="#bill-panel"` untuk refresh bill
7. **Table positions**: Di-setting dari HO, POS hanya menampilkan. Drag di POS bersifat temporary dan sync dari HO akan overwrite
8. **StoreProductStock vs core_product**: Stock management menggunakan table `pos_store_product_stock` yang terpisah dari `core_product`. Jangan gunakan `product.track_stock` atau `product.stock_quantity` dari core_product karena akan ter-overwrite saat HO sync. `product_id` di StoreProductStock adalah UUIDField biasa (bukan FK) agar survive DELETE+INSERT sync
9. **Stock warning di send_to_kitchen**: Hanya WARNING (informasi), bukan blocking. Kasir bisa tetap kirim pesanan meski ada item yang stoknya habis (via `force=1` parameter)

### File yang Sering Dimodifikasi
| File | Alasan |
|------|--------|
| `apps/pos/views.py` | Tambah view baru, modifikasi logic |
| `templates/pos/partials/bill_panel.html` | UI bill panel, action buttons |
| `templates/pos/partials/product_card.html` | UI kartu produk |
| `templates/pos/partials/product_grid.html` | Logic add/remove product |
| `templates/pos/partials/payment_modal.html` | Flow pembayaran |
| `templates/pos/partials/main/js/keyboard_shortcuts.html` | Tambah shortcut |
| `templates/tables/floor_plan.html` | Floor plan visual |
| `apps/pos/urls.py` | Tambah URL endpoint baru |
| `apps/pos/models.py` | StoreProductStock model |
| `apps/management/views.py` | Stock management CRUD views |
| `templates/management/stock_management.html` | UI stock management |
| `pos_launcher_qt/local_api.py` | POS Launcher Flask API (print, printer status, customer display) |
| `templates/pos/printer_status.html` | Receipt printer widget (sidebar, Alpine.js) |
| `templates/pos/partials/main/kitchen_printer_widget.html` | Kitchen printer widget (sidebar, Alpine.js) |
| `kitchen_printer_agent/kitchen_agent.py` | Kitchen Agent daemon (polling, printing, HTTP health server) |

---

## 11. Changelog / Improvement History

### Phase 1: Quick Wins (Completed)
- [x] Ganti semua `alert()` → `showToast()` di semua template POS
- [x] Inline validation di payment modal (real-time feedback)
- [x] Keyboard shortcut F1-F4, F8 untuk cashier
- [x] Animasi feedback visual saat add/remove product (flash hijau/merah)

### Phase 2: UX Flow Improvements (Completed)
- [x] Category filter UX improvement (All button, active state, scroll indicator)
- [x] Color-coded bill panel header berdasarkan status
- [x] Stock availability badge di product card (Out of Stock, Low Stock)

### Phase 3: Feature Improvements (Completed)
- [x] Numpad visual untuk payment cash
- [x] Recent orders quick access (15 bill terakhir)
- [x] Floor plan status visual enhancement (warna meja, timer, bill info, hold badge)
- [x] Store Product Stock Management (StoreProductStock model, management UI, send_to_kitchen warning, product card integration)

### Printer & Hardware (Completed)
- [x] Receipt Printer widget di sidebar dengan heartbeat animation saat offline
- [x] Two-level check: Service health → Printer hardware status
- [x] Deteksi hardware printer fisik via `GET /api/printer/status` (Windows: win32print + WMI, Linux: CUPS)
- [x] WMI `Win32_Printer.WorkOffline` untuk deteksi USB disconnect (win32print spooler cache tidak reliable)
- [x] Status flags: paper_jam, paper_out, offline, door_open, toner_low, dll
- [x] Kitchen Printer widget rewrite: vanilla JS → Alpine.js, matching Receipt Printer widget pattern
- [x] Kitchen Agent HTTP health server (port 5001) — embedded di `kitchen_agent.py`, zero new dependencies
- [x] Two-level check untuk kitchen: Agent running? → Network printers reachable? (TCP socket health)
- [x] Fallback strategy: widget cek agent HTTP dulu, fallback ke Django DB endpoint jika agent unreachable
- [x] Django `kitchen_agent_status` view: try HTTP health endpoint first, fallback ke systemctl
- [x] Removed start/stop agent buttons dari widget (agent dikelola via Docker/systemd)
- [x] Dockerize Kitchen Agent: tambah service `kitchen_agent` di `docker-compose.yml` (reuse image utama)
- [x] Kitchen Agent `network_mode: host` — agar bisa reach printer LAN tanpa Docker bridge subnet conflict
- [x] Fix Docker subnet conflict: `bip: 172.30.0.1/16` + `pos_network` explicit subnet `172.28.0.0/16` (hindari 172.17.x.x)
- [x] Django view `kitchen_agent_status`: try `host.docker.internal` → localhost → systemctl fallback
- [x] Test Print functionality via `POST /api/print`

### Bug Fixes
- [x] Fix multi-brand printer routing: `get_printer_for_station()` sekarang filter by `brand_id` — food court ticket dikirim ke printer brand yang benar
- [x] Fix `print_attempts` tidak pernah di-increment — ticket retry tanpa batas. Fix: increment di `mark_ticket_printing()`
- [x] Fix Docker bridge subnet conflict (172.17.0.0/16) dengan printer LAN (172.17.10.x) — traffic ke printer di-capture oleh docker0
- [x] Fix floor plan JSON error akibat Django L10N (1200 → 1.200) - Solusi: `{% localize off %}`
- [x] Fix hold bill tidak kembali ke menu utama - Solusi: `window.location.href = '/pos/'` (bukan reload)
- [x] Fix product card currency format ($200000.00 → Rp. 200,000) - Gunakan `|rupiah` filter
- [x] Fix floor plan enrichment error handling - try/except + default values pada semua table objects
