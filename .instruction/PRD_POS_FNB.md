# Product Requirement Document (PRD)
# F&B POS Offline-LAN System

---

## 1. Overview

### 1.1 Product Name
F&B POS Offline-LAN System

### 1.2 Background
Sistem POS F&B ini dirancang untuk restoran dan café multi-store dengan kebutuhan operasional **tetap berjalan meskipun internet mati**, selama jaringan lokal (LAN/WiFi) masih aktif.

Arsitektur menggunakan **Edge Server per store** sebagai pusat transaksi. POS, Kiosk, Tablet, dan Table Order berperan sebagai client berbasis web (HTMX).

Pendekatan ini menghindari kompleksitas POS offline per-kassa dan memusatkan konsistensi data di Edge Server.

### 1.3 Goals
- Operasional POS tetap berjalan saat internet down
- Arsitektur sederhana dan stabil
- Mendukung table service, quick service, kiosk, dan QR table order
- Mudah di-scale ke multi-store

### 1.4 Non-Goals
- Offline penuh per device POS
- Native mobile app (Android/iOS) pada fase awal

---

## 2. Target Users & Roles

| Role | Description |
|----|----|
| Cashier | Input order, payment, close bill |
| Waiter | Open table, input order, merge/split |
| Supervisor | Void, cancel, approval |
| Kitchen Staff | Melihat dan memproses order |
| Store Admin | Setting device, printer, operasional |
| HO Admin | Master data, promo, reporting |

---

## 3. High-Level Architecture

```
HO (Cloud)
 └─ Django + Svelte
     - Master Data
     - Promotion Engine
     - Reporting & Finance

Edge Server (Per Store)
 └─ Django
     - Local Database
     - POS API
     - Printer & KDS Service
     - Promotion Engine Executor
     - Sync Engine

POS / Kiosk / Tablet
 └─ HTMX (Browser-based)
     - Order UI
     - Payment UI
     - Table Order UI
```

---

## 4. Functional Requirements

### 4.1 Core POS
- Open Bill
- Hold / Resume Bill
- Close Bill
- Cancel Bill (role-based)
- Void Item (pre & post kitchen)
- Reprint Receipt

### 4.2 Table Service
- Open Table
- Move Table
- Join Table
- Split Table
- Merge Bill
- Table Status

### 4.3 Quick Service
- Quick Order
- Direct Payment
- Queue Number

### 4.4 Order Management
- Modifier & Notes
- Split Order
- Split Bill
- Partial Payment
- Multi Payment

### 4.5 Kitchen & Bar
- Printer routing
- Reprint kitchen
- KDS status flow

### 4.6 Table Order / QR
- QR per table
- Guest ordering
- Order masuk ke bill

### 4.7 Promotion & Voucher Engine
- Discount, Buy X Get Y, Combo
- Time-based & category-based promo
- Voucher code & QR
- Offline validation

---

## 5. Non-Functional Requirements
- Performance <300ms LAN
- Offline LAN reliability
- Role-based security
- Touch friendly UI

---

## 6. Data Ownership & Sync

| Data | HO | Edge | POS |
|----|----|-----|-----|
| Menu | Master | Cache | View |
| Promo | Master | Cache | View |
| Voucher | Master | Cache | View |
| Order | ❌ | Master | View |
| Payment | ❌ | Master | View |

---

## 7. Roadmap

### Phase 1 – MVP
- Core POS
- Table service
- Basic promo
- Kitchen printer

### Phase 2 – Stability
- Advanced promo
- Voucher rules
- Audit & retry

### Phase 3 – Scale
- Multi-store
- Campaign analytics

---

**END OF PRD**
