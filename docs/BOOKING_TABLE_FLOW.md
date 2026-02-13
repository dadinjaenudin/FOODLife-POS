# Design Document: Table Booking & Payment Flow - FoodLife POS

## Context

FoodLife POS saat ini sudah memiliki table management dasar (Table, TableArea, TableGroup) dengan status available/occupied/reserved/billing/dirty, namun **belum ada sistem reservasi/booking yang dedicated**. Dokumen ini merancang flow lengkap untuk fitur Booking Table yang mencakup 3 skenario: reservasi biasa, reservasi dengan minimum spend, dan event/private dining. Termasuk bagaimana alur pembayaran deposit dan settlement akhir.

---

## A. Data Model Design (ERD)

### Model Baru

#### 1. `ReservationConfig` — Konfigurasi Booking per Store
| Field | Type | Keterangan |
|-------|------|------------|
| id | UUID | PK |
| store | FK(Store) | OneToOne per store |
| is_booking_enabled | bool | Aktifkan/nonaktifkan fitur booking |
| default_slot_duration | int | Durasi default per slot (menit), default: 120 |
| max_advance_days | int | Maks booking berapa hari ke depan, default: 30 |
| grace_period_minutes | int | Toleransi keterlambatan sebelum no-show, default: 30 |
| require_deposit | bool | Default apakah deposit wajib |
| default_deposit_type | enum | `percentage` / `fixed` |
| default_deposit_value | decimal | Nilai deposit (misal 50% atau Rp 100.000) |
| min_deposit_amount | decimal | Minimum deposit (jika percentage) |
| cancellation_hours | int | Batas jam pembatalan tanpa penalty, default: 24 |
| cancellation_fee_pct | decimal | Persentase penalty pembatalan, default: 0 |
| auto_noshow_minutes | int | Menit setelah grace period → otomatis no-show |
| overbooking_buffer | int | Buffer menit antar booking di meja yang sama, default: 30 |

#### 2. `Reservation` — Data Booking Utama
| Field | Type | Keterangan |
|-------|------|------------|
| id | UUID | PK |
| reservation_code | char(12) | Auto-generated, unique, human-readable (RSV-YYYYMMDD-XXX) |
| company | FK(Company) | Multi-tenant |
| brand | FK(Brand) | Multi-tenant |
| store | FK(Store) | Multi-tenant |
| **Tipe & Status** | | |
| type | enum | `standard` / `min_spend` / `event` |
| status | enum | Lihat lifecycle di bawah |
| **Jadwal** | | |
| reservation_date | date | Tanggal booking |
| time_start | time | Jam mulai |
| time_end | time | Jam selesai (estimasi) |
| duration_minutes | int | Durasi (menit) |
| **Tamu** | | |
| guest_name | varchar(100) | Nama tamu |
| guest_phone | varchar(20) | No. HP |
| guest_email | varchar(100) | Email (opsional) |
| party_size | int | Jumlah tamu |
| **Meja** | | |
| tables | M2M(Table) | Meja yang di-assign (bisa lebih dari 1 untuk group) |
| table_area | FK(TableArea) | Area preferensi (opsional, bisa null) |
| **Keuangan** | | |
| minimum_spend | decimal | Min. spend requirement (0 jika tidak ada) |
| deposit_required | bool | Apakah booking ini butuh DP |
| deposit_amount | decimal | Jumlah DP yang harus dibayar |
| deposit_paid | decimal | Jumlah DP yang sudah dibayar |
| deposit_status | enum | `pending` / `paid` / `partial` / `refunded` / `forfeited` |
| **Event** | | |
| package | FK(ReservationPackage) | Paket event (null jika bukan event) |
| special_requests | text | Request khusus (dekorasi, kue, dll) |
| **Relasi** | | |
| bill | FK(Bill) | Bill yang dibuat saat check-in (null sampai check-in) |
| member | FK(Member) | Member loyalty (opsional) |
| created_by | FK(User) | Staff yang input |
| confirmed_by | FK(User) | Staff yang konfirmasi |
| **Audit** | | |
| created_at | datetime | |
| updated_at | datetime | |
| cancelled_at | datetime | Null jika belum cancel |
| cancellation_reason | text | Alasan cancel |
| noshow_at | datetime | Null jika bukan no-show |

#### 3. `ReservationDeposit` — Tracking Pembayaran DP
| Field | Type | Keterangan |
|-------|------|------------|
| id | UUID | PK |
| reservation | FK(Reservation) | |
| amount | decimal | Jumlah DP |
| payment_method | varchar(20) | cash/card/qris/transfer/ewallet |
| payment_profile | FK(PaymentMethodProfile) | Profile pembayaran yang digunakan |
| payment_metadata | JSON | Data tambahan (no. ref, approval code, dll) |
| status | enum | `paid` / `refunded` / `forfeited` |
| paid_at | datetime | |
| refunded_at | datetime | |
| refund_amount | decimal | Jumlah yang di-refund |
| refund_reason | text | |
| receipt_number | varchar(50) | Nomor kwitansi DP |
| created_by | FK(User) | |

#### 4. `ReservationPackage` — Paket Event/Private Dining
| Field | Type | Keterangan |
|-------|------|------------|
| id | UUID | PK |
| company | FK(Company) | |
| brand | FK(Brand) | |
| name | varchar(100) | Nama paket (Birthday Package, Gathering, dll) |
| description | text | Deskripsi |
| min_pax | int | Minimum jumlah tamu |
| max_pax | int | Maksimum jumlah tamu |
| price_per_pax | decimal | Harga per orang |
| fixed_price | decimal | Harga paket flat (alternatif per-pax) |
| includes_menu | bool | Paket sudah termasuk menu? |
| menu_items | JSON | Daftar menu yang termasuk |
| duration_hours | int | Durasi event (jam) |
| deposit_percentage | decimal | Override deposit % untuk paket ini |
| is_active | bool | |

#### 5. `ReservationLog` — Audit Trail
| Field | Type | Keterangan |
|-------|------|------------|
| id | BigAutoField | PK |
| reservation | FK(Reservation) | |
| action | enum | `created`, `confirmed`, `deposit_paid`, `checked_in`, `no_show`, `cancelled`, `completed`, `modified` |
| details | JSON | Detail perubahan |
| created_by | FK(User) | |
| created_at | datetime | |

### Relasi dengan Model Existing

```
Company ──┬── Brand ──┬── Store ──── ReservationConfig (1:1)
           │           │
           │           ├── ReservationPackage (1:N)
           │           │
           └───────────┴── Reservation (N)
                                │
                                ├── Table (M2M) ← existing tables app
                                ├── Bill (FK) ← existing pos app (saat check-in)
                                ├── Member (FK) ← existing core app
                                ├── ReservationDeposit (1:N)
                                └── ReservationLog (1:N)

Saat checkout:
  Bill.payments[] ← include deposit sebagai payment record
  ReservationDeposit.status → 'applied' saat dikonversi ke Payment
```

---

## B. Reservation Lifecycle & Status Flow

### Status Diagram

```
                    ┌──────────────┐
                    │   PENDING    │ ← Baru dibuat, belum dikonfirmasi
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
     ┌────────────┐  ┌──────────┐  ┌───────────┐
     │ CONFIRMED  │  │DEPOSIT   │  │ CANCELLED │
     │(tanpa DP)  │  │PENDING   │  │           │
     └─────┬──────┘  └────┬─────┘  └───────────┘
           │               │
           │          DP dibayar
           │               │
           │               ▼
           │        ┌──────────┐
           ├───────►│CONFIRMED │
           │        │(dgn DP)  │
           │        └────┬─────┘
           │             │
           ▼             ▼
    ┌─────────────────────────┐
    │      CHECKED_IN         │ ← Tamu datang, bill dibuat
    └────────────┬────────────┘
                 │
          ┌──────┼──────┐
          │             │
          ▼             ▼
   ┌────────────┐ ┌──────────┐
   │  COMPLETED │ │  NO_SHOW │
   │ (bill paid)│ │(tdk dtg) │
   └────────────┘ └──────────┘
```

### Status Definitions

| Status | Keterangan | Trigger |
|--------|-----------|---------|
| `pending` | Booking dibuat, menunggu konfirmasi / DP | Saat booking baru di-input |
| `deposit_pending` | Booking butuh DP tapi belum bayar | Saat booking dgn deposit required |
| `confirmed` | Booking terkonfirmasi (DP dibayar atau tanpa DP) | Setelah DP dibayar / langsung confirm |
| `checked_in` | Tamu sudah datang, bill aktif | Saat staff check-in tamu |
| `completed` | Selesai dining, bill lunas | Saat bill status = paid |
| `cancelled` | Dibatalkan (oleh tamu/staff) | Saat pembatalan |
| `no_show` | Tamu tidak datang melewati grace period | Manual oleh staff / auto setelah timeout |

### Aturan Transisi
- `pending` → `confirmed` (tanpa DP) / `deposit_pending` (butuh DP) / `cancelled`
- `deposit_pending` → `confirmed` (DP paid) / `cancelled` (refund DP)
- `confirmed` → `checked_in` / `cancelled` / `no_show`
- `checked_in` → `completed` (bill paid)
- **Tidak bisa mundur status** (irreversible transitions)

---

## C. Booking Creation Flow

### Flow 1: Reservasi Biasa (Standard)

```
Staff membuka menu Booking
        │
        ▼
┌──────────────────────────────┐
│ FORM BOOKING                 │
│                              │
│ Tipe: [Standard]             │
│ Tanggal: [📅 Date Picker]    │
│ Jam: [🕐 Time Picker]        │
│ Durasi: [2 jam] (default)    │
│ Jumlah Tamu: [4]             │
│                              │
│ Nama Tamu: [Budi Santoso]    │
│ No. HP: [0812-xxxx-xxxx]    │
│ Member: [🔍 Search] (opsional)│
│                              │
│ Area: [Indoor ▼]             │
│ Meja: [Auto-assign / Pilih]  │
│                              │
│ Catatan: [______________]    │
│                              │
│ □ Require Deposit            │
│   Amount: Rp [________]     │
│                              │
│ [Batal]        [Simpan]      │
└──────────────────────────────┘
        │
        ▼
  Sistem validasi:
  ✓ Meja tersedia di tanggal & jam tersebut
  ✓ Kapasitas meja cukup untuk party size
  ✓ Tidak overlap dengan booking lain (+ buffer)
  ✓ Tanggal tidak melebihi max_advance_days
        │
        ▼
  ┌─ Tanpa DP ── Status: CONFIRMED ── Selesai
  │
  └─ Dengan DP ── Status: DEPOSIT_PENDING ── Lanjut ke Pembayaran DP
```

### Flow 2: Reservasi Minimum Spend

```
Sama seperti Flow 1, tetapi:
  │
  ▼
┌──────────────────────────────┐
│ TAMBAHAN FIELD:              │
│                              │
│ Tipe: [Minimum Spend]       │
│ Minimum Spend: Rp [500.000] │
│                              │
│ ℹ️ Tamu wajib belanja minimal │
│   Rp 500.000. Jika kurang,  │
│   selisih akan ditagihkan.   │
│                              │
│ Deposit: Rp [250.000]       │
│ (50% dari min spend)        │
└──────────────────────────────┘
        │
        ▼
  Saat checkout nanti:
  - Jika total bill ≥ min spend → normal checkout
  - Jika total bill < min spend → charge selisihnya
```

### Flow 3: Event / Private Dining

```
Staff memilih tipe Event
        │
        ▼
┌──────────────────────────────┐
│ FORM BOOKING EVENT           │
│                              │
│ Tipe: [Event / Private]     │
│ Paket: [🔍 Pilih Paket ▼]   │
│  ├─ Birthday Package         │
│  ├─ Gathering Package        │
│  └─ Custom Event             │
│                              │
│ Tanggal: [📅]  Jam: [🕐]     │
│ Durasi: [3 jam] (dari paket) │
│ Jumlah Tamu: [20]           │
│                              │
│ ── Info Harga ──             │
│ Harga Paket: Rp 150.000/pax │
│ × 20 pax = Rp 3.000.000     │
│                              │
│ Deposit (50%): Rp 1.500.000 │
│                              │
│ ── Request Khusus ──         │
│ □ Dekorasi                   │
│ □ Kue Ulang Tahun            │
│ □ Sound System               │
│ Catatan: [______________]    │
│                              │
│ Meja: [Table 10, 11, 12]    │
│ (auto-suggest / manual pick) │
│                              │
│ [Batal]        [Simpan]      │
└──────────────────────────────┘
```

### Validasi Rules (Semua Tipe)

| Rule | Keterangan |
|------|-----------|
| Meja tidak double-book | Cek overlap waktu (time_start - time_end + buffer) |
| Kapasitas meja | Total seat ≥ party_size |
| Advance booking limit | reservation_date ≤ today + max_advance_days |
| Time slot valid | Dalam jam operasional store |
| Party size min/max | Untuk event: sesuai paket min/max_pax |
| Deposit amount valid | ≥ min_deposit_amount (jika configured) |

---

## D. Payment Flow

### D1. Pembayaran Deposit (Saat Booking)

```
Booking dibuat (status: deposit_pending)
        │
        ▼
┌──────────────────────────────┐
│ PAYMENT DEPOSIT MODAL        │
│                              │
│ Booking: RSV-20260214-001    │
│ Tamu: Budi Santoso           │
│ Tanggal: 14 Feb 2026, 19:00 │
│                              │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ Deposit Amount: Rp 250.000   │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                              │
│ Metode Bayar:                │
│ ┌──────┐┌──────┐┌──────┐    │
│ │ Cash ││ QRIS ││ Card │    │
│ └──────┘└──────┘└──────┘    │
│ ┌────────┐┌─────────┐       │
│ │Transfer││E-Wallet │       │
│ └────────┘└─────────┘       │
│                              │
│ Jumlah Bayar: [Rp 250.000]  │
│                              │
│ [Batal]     [Bayar Deposit]  │
└──────────────────────────────┘
        │
        ▼
  Buat record ReservationDeposit
  Status deposit → PAID
  Status reservation → CONFIRMED
  Print kwitansi DP (opsional)
  Kirim notifikasi ke customer (future)
```

**Metode pembayaran DP:** Menggunakan PaymentMethodProfile yang sama dengan payment biasa (reuse infrastruktur existing).

### D2. Checkout / Final Payment (Saat Selesai Dining)

```
Tamu selesai makan → Staff buka Payment Modal
        │
        ▼
┌──────────────────────────────────┐
│ PAYMENT MODAL (Enhanced)         │
│                                  │
│ Bill #1234 — Meja 10             │
│ 🔖 Reservation: RSV-20260214-001│
│                                  │
│ ── Rincian ──                    │
│ Subtotal:           Rp 620.000  │
│ Service Charge 5%:  Rp  31.000  │
│ Tax 11%:            Rp  68.200  │
│ ─────────────────────────────── │
│ TOTAL:              Rp 719.200  │
│                                  │
│ ── Deposit Applied ──            │
│ ✅ Deposit DP:     -Rp 250.000  │
│ (Cash, 10 Feb 2026)             │
│ ─────────────────────────────── │
│ SISA BAYAR:         Rp 469.200  │
│                                  │
│ Metode Bayar: [QRIS ▼]          │
│ Amount: [Rp 469.200]            │
│                                  │
│ [Batal]           [Bayar]        │
└──────────────────────────────────┘
        │
        ▼
  Buat Payment records:
  1. Payment (deposit): amount=250.000, source='deposit'
  2. Payment (final): amount=469.200, method=qris

  Bill status → PAID
  Reservation status → COMPLETED
  Print receipt (menampilkan info deposit)
```

### D3. Skenario Minimum Spend (Kurang dari Min Spend)

```
Tamu selesai makan, total bill hanya Rp 350.000
Min spend requirement: Rp 500.000
        │
        ▼
┌──────────────────────────────────┐
│ ⚠️ MINIMUM SPEND WARNING         │
│                                  │
│ Total belanja: Rp 350.000       │
│ Minimum spend: Rp 500.000       │
│ Selisih:       Rp 150.000       │
│                                  │
│ Pilihan:                         │
│ ○ Charge selisih Rp 150.000     │
│   (total bayar jadi Rp 500.000) │
│ ○ Waive (tidak charge selisih)  │
│   ⚠️ Butuh approval Manager     │
│                                  │
│ [Kembali]    [Lanjut Bayar]      │
└──────────────────────────────────┘
        │
        ▼
  Jika charge selisih:
    Total = Rp 500.000
    Deposit = -Rp 250.000
    Sisa bayar = Rp 250.000

  Jika waive (approved):
    Total = Rp 350.000
    Deposit = -Rp 250.000
    Sisa bayar = Rp 100.000
```

### D4. Pembatalan & Refund Deposit

```
Staff membuka detail booking → klik Cancel
        │
        ▼
┌──────────────────────────────────┐
│ PEMBATALAN BOOKING               │
│                                  │
│ Booking: RSV-20260214-001       │
│ Tamu: Budi Santoso              │
│ Deposit dibayar: Rp 250.000     │
│                                  │
│ Alasan pembatalan:               │
│ [________________________]      │
│                                  │
│ ── Kebijakan Refund ──          │
│                                  │
│ Jika > 24 jam sebelum jadwal:   │
│   ✅ Full refund Rp 250.000     │
│                                  │
│ Jika < 24 jam sebelum jadwal:   │
│   ⚠️ Penalty 50%                │
│   Refund: Rp 125.000            │
│   Forfeited: Rp 125.000         │
│                                  │
│ Jika No-Show:                    │
│   ❌ Tidak ada refund            │
│   Forfeited: Rp 250.000         │
│                                  │
│ [Kembali]   [Konfirmasi Cancel]  │
└──────────────────────────────────┘
        │
        ▼
  ReservationDeposit.status → 'refunded' / 'forfeited'
  Reservation.status → 'cancelled'
  Log ke ReservationLog
  Proses refund sesuai metode pembayaran asal
```

### D5. Ringkasan Alur Pembayaran

| Skenario | Deposit | Saat Checkout | Sisa Bayar |
|----------|---------|---------------|------------|
| Standard tanpa DP | - | Bayar full | Total bill |
| Standard + DP Rp 250K | Rp 250K (cash) | Total Rp 700K - DP 250K | Rp 450K |
| Min Spend Rp 500K, belanja Rp 350K | Rp 250K | Charge Rp 500K - DP 250K | Rp 250K |
| Min Spend Rp 500K, belanja Rp 800K | Rp 250K | Charge Rp 800K - DP 250K | Rp 550K |
| Event Rp 3jt, DP 50% | Rp 1.5jt | Total Rp 3.2jt - DP 1.5jt | Rp 1.7jt |
| Cancel > 24 jam | Rp 250K | Refund full | - |
| Cancel < 24 jam | Rp 250K | Refund 50% | Forfeited 125K |
| No-Show | Rp 250K | No refund | Forfeited 250K |

---

## E. Day-of-Operations Flow

### E1. Dashboard Booking Hari Ini

```
┌──────────────────────────────────────────────────────────┐
│ 📋 BOOKING HARI INI — 14 Feb 2026                        │
│                                                          │
│ [Hari Ini] [Besok] [Minggu Ini] [📅 Pilih Tanggal]      │
│                                                          │
│ ┌─ 17:00 ──────────────────────────────────────────────┐ │
│ │ RSV-001 | Budi S. | 4 pax | Meja 10                 │ │
│ │ Standard | DP: Rp 250K ✅ | ☎ 0812-xxxx              │ │
│ │ [Check-in]  [Detail]  [Cancel]                       │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                          │
│ ┌─ 18:00 ──────────────────────────────────────────────┐ │
│ │ RSV-002 | Sari M. | 2 pax | Meja 5                  │ │
│ │ Standard | Tanpa DP | ☎ 0813-xxxx                    │ │
│ │ Status: CONFIRMED                                    │ │
│ │ [Check-in]  [Detail]  [Cancel]                       │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                          │
│ ┌─ 19:00 ──────────────────────────────────────────────┐ │
│ │ RSV-003 | PT ABC | 20 pax | Meja 10,11,12           │ │
│ │ 🎉 Event: Birthday Package | DP: Rp 1.5jt ✅        │ │
│ │ Special: Dekorasi + Kue                              │ │
│ │ [Check-in]  [Detail]  [Cancel]                       │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                          │
│ ┌─ 19:30 ──────────────────────────────────────────────┐ │
│ │ RSV-004 | Andi K. | 6 pax | Meja 8                  │ │
│ │ ⚠️ NO-SHOW (lewat 30 menit)                          │ │
│ │ [Tandai No-Show]  [Detail]  [Extend Grace]           │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                          │
│ Total: 4 booking | 32 pax | 2 dengan DP                 │
│                                                          │
│ [+ Booking Baru]                                         │
└──────────────────────────────────────────────────────────┘
```

### E2. Check-in Flow

```
Staff klik [Check-in] pada booking
        │
        ▼
┌──────────────────────────────────┐
│ CHECK-IN BOOKING                 │
│                                  │
│ RSV-20260214-001                │
│ Budi Santoso — 4 pax            │
│ Meja 10 (Indoor)                │
│                                  │
│ ✅ Deposit Rp 250.000 (PAID)    │
│                                  │
│ Jumlah tamu aktual: [4]         │
│                                  │
│ [Batal]        [Check-in →]     │
└──────────────────────────────────┘
        │
        ▼
  Sistem otomatis:
  1. Buat Bill baru (type: dine_in, table: Meja 10)
  2. Table.status → 'occupied'
  3. Reservation.status → 'checked_in'
  4. Reservation.bill → Bill baru
  5. Log: action='checked_in'
        │
        ▼
  Redirect ke POS dengan bill aktif
  → Staff bisa langsung ambil order
```

### E3. Floor Plan Integration

```
Di Floor Plan, meja yang di-booking ditampilkan berbeda:

┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
│Meja 1  │  │Meja 2  │  │Meja 3  │  │Meja 4  │
│🟢 Kosong│  │🔴 Terisi│  │🟡 Booked│  │🟡 Booked│
│        │  │Bill#123│  │19:00   │  │18:00   │
│        │  │45 mnt  │  │Budi 4p │  │Sari 2p │
│[Open]  │  │[Resume]│  │[Checkin]│  │[Checkin]│
└────────┘  └────────┘  └────────┘  └────────┘

Legend:
🟢 Available — bisa di-assign walk-in
🔴 Occupied — sedang dipakai
🟡 Reserved — ada booking (tampilkan waktu & nama)
⚫ Dirty — perlu dibersihkan

Klik meja reserved → lihat detail booking → check-in
```

### E4. Walk-in vs Reserved

| Situasi | Action |
|---------|--------|
| Walk-in, meja available | Normal flow, langsung assign |
| Walk-in, meja reserved tapi > 1 jam lagi | Bisa pakai, warning akan tampil |
| Walk-in, meja reserved < 1 jam lagi | Block, suggest meja lain |
| Walk-in, semua reserved | Suggest tunggu atau takeaway |
| Booking check-in, meja masih occupied | Warning: "Meja belum available, pindahkan dulu" |

### E5. No-Show Handling

```
Jam booking sudah lewat + grace_period_minutes
        │
        ▼
  Dashboard menampilkan warning ⚠️
  "RSV-001: Budi S. — 30 menit terlambat"
        │
        ▼
  Staff pilih aksi:
  ├─ [Extend Grace +15 mnt] → Tunggu lagi
  ├─ [Tandai No-Show] →
  │       ├─ Reservation.status → 'no_show'
  │       ├─ Table.status → 'available' (bisa dipakai walk-in)
  │       ├─ Deposit → 'forfeited' (sesuai policy)
  │       └─ Log: action='no_show'
  │
  └─ [Hubungi Tamu] → Tampilkan no HP untuk kontak
```

---

## F. Business Rules

### F1. Time Slot & Durasi

| Rule | Default | Configurable |
|------|---------|-------------|
| Durasi minimum booking | 60 menit | Ya |
| Durasi default | 120 menit | Ya |
| Durasi event | 180 menit | Ya, per paket |
| Buffer antar booking | 30 menit | Ya |
| Slot tersedia | Jam operasional store | Ya |
| Max advance booking | 30 hari | Ya |

### F2. Kapasitas & Meja

| Rule | Keterangan |
|------|-----------|
| Auto-assign | Sistem suggest meja berdasarkan kapasitas & area |
| Manual assign | Staff bisa override pilihan meja |
| Multi-table | Untuk group besar, bisa assign >1 meja |
| Table capacity check | party_size ≤ total kapasitas assigned tables |
| Overlap check | Meja tidak boleh double-book (waktu + buffer) |

### F3. Deposit Rules

| Rule | Keterangan |
|------|-----------|
| Deposit wajib/opsional | Per store (ReservationConfig) |
| Tipe deposit | Percentage atau fixed amount |
| Min deposit | Configurable minimum amount |
| Event deposit | Override dari ReservationPackage |
| Metode bayar DP | Semua metode payment yang aktif |
| DP applied at checkout | Otomatis dikurangi dari total bill |
| DP > total bill | Selisih di-refund |

### F4. Cancellation Policy

| Waktu Pembatalan | Refund | Keterangan |
|-----------------|--------|-----------|
| > cancellation_hours sebelum jadwal | 100% | Full refund deposit |
| < cancellation_hours sebelum jadwal | (100% - cancellation_fee_pct) | Partial refund |
| No-show | 0% | Deposit forfeited |
| Dibatalkan oleh restaurant | 100% | Full refund, always |

### F5. Minimum Spend Enforcement

| Skenario | Action |
|----------|--------|
| Bill ≥ min_spend | Checkout normal, deposit applied |
| Bill < min_spend | Warning + opsi charge selisih atau waive (butuh Manager approval) |
| Waive min_spend | Dicatat di log, perlu PIN manager |

### F6. Member Integration

| Feature | Keterangan |
|---------|-----------|
| Member search saat booking | Lookup by code / phone |
| Priority booking | Member gold/platinum bisa booking lebih advance |
| Points earn | Points dihitung dari final bill (bukan deposit) |
| Member history | Riwayat booking tercatat di member profile |

---

## G. Configuration Options (ReservationConfig per Store)

### Settings yang Configurable

| Setting | Type | Default | Keterangan |
|---------|------|---------|-----------|
| is_booking_enabled | bool | false | On/off fitur booking |
| default_slot_duration | int | 120 | Durasi default (menit) |
| max_advance_days | int | 30 | Max booking ke depan |
| grace_period_minutes | int | 30 | Toleransi telat |
| require_deposit | bool | false | Default wajib DP |
| default_deposit_type | enum | percentage | percentage / fixed |
| default_deposit_value | decimal | 50 | 50% atau Rp nominal |
| min_deposit_amount | decimal | 50000 | Min DP Rp 50.000 |
| cancellation_hours | int | 24 | Batas cancel tanpa penalty |
| cancellation_fee_pct | decimal | 0 | Fee cancel (%) |
| auto_noshow_minutes | int | 0 | 0 = manual no-show only |
| overbooking_buffer | int | 30 | Buffer antar booking (menit) |
| sms_notification | bool | false | Kirim SMS reminder (future) |
| max_party_size | int | 50 | Max tamu per booking |

---

## H. Skenario Real-World

### Skenario 1: Buka Puasa Ramadan
- Tipe: Min Spend (Rp 150.000/pax)
- Party: 8 orang
- Deposit: 50% = Rp 600.000
- Jam: 17:30 (fixed slot buka puasa)
- Special: Menu paket iftar
- Checkout: Total Rp 1.5jt - DP 600K = bayar 900K

### Skenario 2: Weekend Dinner Date
- Tipe: Standard
- Party: 2 orang
- Deposit: Tidak
- Jam: 19:00, durasi 2 jam
- Meja: Window seat (area preference)
- Checkout: Normal, full payment

### Skenario 3: Birthday Party
- Tipe: Event (Birthday Package)
- Party: 25 orang
- Paket: Rp 175.000/pax = Rp 4.375.000
- Deposit: 50% = Rp 2.187.500
- Durasi: 3 jam (19:00 - 22:00)
- Meja: 5 meja joined (area VIP)
- Special: Dekorasi balon, kue ultah, sound system
- Checkout: Total final Rp 5.2jt - DP 2.187.500 = bayar Rp 3.012.500

### Skenario 4: Cancel Last Minute
- Booking Rp 250K deposit, cancel 6 jam sebelumnya
- Policy: cancel < 24 jam → penalty 50%
- Refund: Rp 125.000 (via metode pembayaran asal)
- Forfeited: Rp 125.000

### Skenario 5: VIP Member Priority
- Member Platinum call untuk booking weekend
- Advance booking: 45 hari (premium vs 30 hari standard)
- Priority table assignment
- No deposit required (trusted member)

---

## Summary Flow Diagram (End-to-End)

```
┌─────────────────────────────────────────────────────────────────┐
│                    TABLE BOOKING LIFECYCLE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  BOOKING CREATION          CONFIRMATION         DAY-OF          │
│  ═══════════════          ════════════         ══════           │
│                                                                 │
│  Customer call/WA  ──→  Staff input form  ──→  Validasi        │
│                                                   │             │
│                              ┌────────────────────┤             │
│                              │                    │             │
│                         Tanpa DP            Dengan DP           │
│                              │                    │             │
│                         CONFIRMED          DEPOSIT PENDING      │
│                              │                    │             │
│                              │              Bayar DP            │
│                              │                    │             │
│                              │              CONFIRMED           │
│                              │                    │             │
│                              └────────┬───────────┘             │
│                                       │                         │
│  HARI-H                               ▼                        │
│  ═════                          Dashboard Booking               │
│                                       │                         │
│                    ┌──────────────────┼──────────────┐          │
│                    │                  │              │          │
│               Tamu Datang        Terlambat      Tidak Datang    │
│                    │                  │              │          │
│               CHECK-IN          Grace Period     NO-SHOW       │
│                    │                  │              │          │
│               Buat Bill          Extend/NS      Forfeit DP     │
│                    │                                │          │
│               Order & Dine                    Meja Available    │
│                    │                                            │
│  CHECKOUT          ▼                                            │
│  ════════     Payment Modal                                     │
│               ┌─────────────┐                                   │
│               │Total:  700K │                                   │
│               │DP:    -250K │                                   │
│               │Sisa:   450K │                                   │
│               └──────┬──────┘                                   │
│                      │                                          │
│                 Bayar Sisa                                       │
│                      │                                          │
│                 COMPLETED                                        │
│                 Print Receipt                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

*Dokumen ini adalah design reference untuk fitur Table Booking di FoodLife POS. Untuk implementasi, model-model baru akan ditambahkan di `apps/tables/`, views di `apps/tables/views.py` dan `apps/pos/views.py`, serta templates baru di `templates/pos/partials/` dan `templates/tables/`.*
