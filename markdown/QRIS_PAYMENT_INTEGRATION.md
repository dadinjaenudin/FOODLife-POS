# QRIS Payment Integration — Dokumentasi Teknis

> **Tujuan dokumen**: Panduan lengkap untuk mengimplementasikan QRIS payment gateway production (Midtrans/Xendit/BCA) menggantikan MockQRISGateway yang dipakai saat development.
>
> **Terakhir diupdate**: 2026-02-12
> **Status saat ini**: MockQRISGateway (development/testing only)

---

## 1. Arsitektur QRIS Payment

### Flow Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  QRIS PAYMENT FLOW                                                  │
│                                                                     │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────┐             │
│  │ Frontend  │───▶│ Django Views │───▶│ PaymentGateway│             │
│  │ Alpine.js │◀───│ (REST API)   │◀───│ (ABC Layer)   │             │
│  │           │    │              │    │               │             │
│  │ - Modal   │    │ - qris_create│    │ MOCK (dev):   │             │
│  │ - Numpad  │    │ - qris_status│    │  DB-based     │             │
│  │ - QR Code │    │ - qris_cancel│    │               │             │
│  │ - Polling │    │ - process_pay│    │ PROD (future): │             │
│  └──────────┘    └──────────────┘    │  Midtrans API  │             │
│                                      │  Xendit API    │             │
│       Customer Display (opsional)    │  BCA API       │             │
│       ┌─────────────┐               └───────┬───────┘             │
│       │ Qt Launcher  │                       │                     │
│       │ Flask :5000  │        ┌──────────────▼──────────┐         │
│       │ /api/qr      │        │  QRISTransaction Model  │         │
│       └─────────────┘        │  (Database storage)     │         │
│                               └─────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────┘
```

### Sequence Diagram

```
Kasir              Frontend            Django View         Gateway            Database
  │                   │                    │                  │                  │
  │ Klik "Generate QR"│                    │                  │                  │
  ├──────────────────▶│                    │                  │                  │
  │                   │ POST qris/create/  │                  │                  │
  │                   ├───────────────────▶│                  │                  │
  │                   │                    │ create_qris_txn()│                  │
  │                   │                    ├─────────────────▶│                  │
  │                   │                    │                  │ INSERT txn       │
  │                   │                    │                  ├─────────────────▶│
  │                   │                    │◀─ QRISCreateResult                  │
  │                   │◀─ JSON {qr_image,  │                  │                  │
  │                   │    transaction_id}  │                  │                  │
  │  QR Code tampil   │                    │                  │                  │
  │◀──────────────────│                    │                  │                  │
  │                   │                    │                  │                  │
  │  [Customer scan]  │ POLL setiap 3 dtk  │                  │                  │
  │                   ├───────────────────▶│ check_status()   │                  │
  │                   │                    ├─────────────────▶│                  │
  │                   │                    │◀─ status='paid'  │                  │
  │                   │◀─ {status:'paid'}  │                  │                  │
  │                   │                    │                  │                  │
  │                   │ AUTO-SUBMIT form   │                  │                  │
  │                   │ POST /pay/         │                  │                  │
  │                   ├───────────────────▶│                  │                  │
  │                   │                    │ Create Payment   │                  │
  │                   │                    │ Close Bill       │                  │
  │                   │                    │ Print Receipt    │                  │
  │                   │◀─ payment_success  │                  │                  │
  │ Sukses!           │                    │                  │                  │
  │◀──────────────────│                    │                  │                  │
```

---

## 2. File & Code Map

| File | Fungsi |
|------|--------|
| `apps/pos/payment_gateway.py` | Abstract PaymentGateway + MockQRISGateway |
| `apps/pos/views.py` | QRIS views (create, status, cancel, simulate) |
| `apps/pos/models.py` | QRISTransaction model |
| `apps/pos/urls.py` | QRIS URL routes |
| `templates/pos/partials/payment_modal.html` | Frontend Alpine.js (QR display, polling, auto-submit) |
| `pos_launcher_qt/local_api.py` | Customer display QR (Flask API, opsional) |

---

## 3. Database: QRISTransaction Model

```python
# apps/pos/models.py
class QRISTransaction(models.Model):
    id              = UUIDField(primary_key=True, default=uuid.uuid4)
    bill            = ForeignKey(Bill, CASCADE, related_name='qris_transactions')
    created_by      = ForeignKey('core.User', SET_NULL, null=True)

    # Transaction data
    transaction_id  = CharField(max_length=100, unique=True, db_index=True)
    amount          = DecimalField(max_digits=12, decimal_places=2)
    qr_string       = TextField(blank=True)

    # Lifecycle
    status          = CharField(max_length=20, default='pending')
                      # pending → paid | expired | failed | cancelled
    gateway_name    = CharField(max_length=50, default='mock')
    gateway_response = JSONField(default=dict, blank=True)

    # Timing
    expires_at      = DateTimeField(null=True)
    paid_at         = DateTimeField(null=True)
    created_at      = DateTimeField(auto_now_add=True)
```

### Status Lifecycle

```
                ┌──────────┐
                │ pending  │ (QR created, waiting customer scan)
                └────┬─────┘
                     │
          ┌──────────┼──────────┬──────────┐
          ▼          ▼          ▼          ▼
     ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐
     │  paid  │ │expired │ │ failed │ │cancelled │
     └────────┘ └────────┘ └────────┘ └──────────┘
     (customer  (timeout   (gateway   (kasir
      scanned)   5 min)    error)     batal)
```

---

## 4. Gateway Abstraction Layer

### Abstract Base Class

```python
# apps/pos/payment_gateway.py

class PaymentGateway(ABC):
    @abstractmethod
    def create_qris_transaction(self, bill, amount: Decimal, **kwargs) -> QRISCreateResult:
        """Buat transaksi QRIS, return QR code data."""
        pass

    @abstractmethod
    def check_status(self, transaction_id: str) -> QRISStatusResult:
        """Cek status pembayaran (dipanggil polling setiap 3 detik)."""
        pass

    @abstractmethod
    def cancel_transaction(self, transaction_id: str) -> bool:
        """Batalkan transaksi pending."""
        pass
```

### Data Classes

```python
@dataclass
class QRISCreateResult:
    success: bool
    transaction_id: str = ''      # ID unik dari gateway
    qr_string: str = ''           # QRIS EMV string (untuk generate QR image)
    qr_url: str = ''              # URL QR image dari gateway (opsional)
    expires_at: Optional[object] = None
    error_message: str = ''

@dataclass
class QRISStatusResult:
    status: str                   # pending | paid | expired | failed | cancelled
    transaction_id: str = ''
    paid_at: Optional[object] = None
    error_message: str = ''
```

### Factory Function

```python
def get_payment_gateway() -> PaymentGateway:
    gateway_type = getattr(settings, 'PAYMENT_GATEWAY', 'mock')
    if gateway_type == 'mock':
        return MockQRISGateway()
    elif gateway_type == 'midtrans':
        return MidtransQRISGateway()   # TODO: implement
    elif gateway_type == 'xendit':
        return XenditQRISGateway()     # TODO: implement
    else:
        raise ValueError(f"Unknown payment gateway: {gateway_type}")
```

---

## 5. API Endpoints

### 5.1 Create QRIS Transaction

```
POST /pos/bill/<bill_id>/qris/create/
```

**Request:**
```
Content-Type: application/x-www-form-urlencoded
X-CSRFToken: <token>

amount=150000
pending_payments=[]   (JSON string, untuk split payment)
```

**Response (success):**
```json
{
    "success": true,
    "transaction_id": "MOCK-A1B2C3D4E5F6",
    "qr_string": "00020101021226610014...",
    "qr_image": "data:image/png;base64,...",
    "expires_at": "2026-02-12T10:05:00+07:00",
    "amount": 150000.0
}
```

**Response (error):**
```json
{
    "success": false,
    "error": "Amount exceeds remaining balance (Rp 150000)"
}
```

**Logic:**
1. Validasi bill ada dan status `open`/`hold`
2. Validasi amount > 0 dan <= sisa tagihan
3. Cancel transaksi QRIS pending sebelumnya (per bill)
4. Panggil `gateway.create_qris_transaction()`
5. Generate QR image server-side (library `qrcode`)
6. Return transaction_id + QR image

### 5.2 Check Status (Polling)

```
GET /pos/bill/<bill_id>/qris/<transaction_id>/status/
```

**Response:**
```json
{
    "status": "pending",
    "transaction_id": "MOCK-A1B2C3D4E5F6",
    "paid_at": null
}
```

Status values: `pending`, `paid`, `expired`, `failed`, `cancelled`

**Logic:**
- Panggil `gateway.check_status(transaction_id)`
- Gateway otomatis cek expiration (pending + past expires_at → expired)

### 5.3 Cancel Transaction

```
POST /pos/bill/<bill_id>/qris/<transaction_id>/cancel/
X-CSRFToken: <token>
```

**Response:**
```json
{"success": true}
```

### 5.4 Simulate Payment (DEV ONLY)

```
POST /pos/bill/<bill_id>/qris/<transaction_id>/simulate-modal/
X-CSRFToken: <token>
```

**Catatan**: Endpoint ini HANYA ubah status transaksi jadi `paid`. TIDAK membuat Payment record atau menutup bill. Form submission di payment modal yang handle itu.

Berbeda dengan `/simulate/` (tanpa `-modal`) yang langsung auto-complete bill — itu untuk standalone QRIS flow.

---

## 6. Frontend: Payment Modal QRIS Flow

### Alpine.js State

```javascript
// Di dalam paymentModal() — templates/pos/partials/payment_modal.html
qrisState: 'idle',            // idle | generating | polling | paid | error
qrisTransactionId: '',        // ID transaksi dari gateway
qrisQrImage: '',              // Base64 PNG QR code image
qrisFieldName: '',            // Nama prompt field (biasanya 'qrcontent')
qrisError: '',                // Pesan error
qrisAmount: 0,                // Nominal QRIS
_qrisTimer: null,             // setInterval handle untuk polling
```

### State Transitions

```
idle ─── generateQR() ───▶ generating ─── response ───▶ polling
  ▲                                                        │
  │              cancelQRIS()                               │
  ├──────────────────────────────────────────────────────────┤
  │                                                        │
  │         status='paid' (800ms delay)                     │
  ├◀──── paid ◀──────────────────────────────────────────────┤
  │                                                        │
  │         status='expired'/'failed'/'cancelled'           │
  └──── error ◀────────────────────────────────────────────┘
```

### Safety Rules (PENTING)

1. **Tombol "Bayar" DISABLED saat QRIS polling** — `canPay` return false jika `qrisState === 'polling' || 'generating'`
2. **Tombol "Cancel" DISABLED saat QRIS polling/paid** — Mencegah kasir batal setelah customer bayar
3. **Auto-submit setelah QRIS paid** — Setelah 800ms, form otomatis di-submit via `form.requestSubmit()`. Ini BYPASS `canPay` karena QRIS sudah terbayar dan HARUS diproses
4. **Cleanup saat ganti metode** — `setMethod()` panggil `cancelQRIS()` jika QRIS aktif
5. **Cleanup saat tutup modal** — `closeModal()` panggil `window._qrisCleanup()`

### Auto-Submit Mechanism

```javascript
// Setelah polling detect status='paid':
setTimeout(function() {
    self.qrisState = 'idle';
    self.$nextTick(function() {
        // Force submit — bypass canPay karena QRIS sudah terbayar
        var form = document.getElementById('payment-form');
        if (form) {
            // requestSubmit() trigger native submit event yang HTMX intercept
            if (form.requestSubmit) {
                form.requestSubmit();
            } else {
                form.dispatchEvent(new Event('submit', {bubbles: true, cancelable: true}));
            }
        }
    });
}, 800);
```

**Kenapa `requestSubmit()` bukan `htmx.trigger()`?**
- `htmx.trigger(form, 'submit')` fire CustomEvent, bukan native SubmitEvent
- HTMX intercept native submit event untuk proses `hx-post`
- `requestSubmit()` trigger native submit → HTMX tangkap → POST ke `process_payment`

---

## 7. Implementasi Production Gateway

### 7.1 Langkah-langkah

1. **Buat class baru** di `apps/pos/payment_gateway.py`:

```python
class MidtransQRISGateway(PaymentGateway):
    """Production QRIS gateway via Midtrans API."""

    def __init__(self):
        self.server_key = settings.MIDTRANS_SERVER_KEY
        self.base_url = settings.MIDTRANS_BASE_URL  # sandbox vs production
        self.is_production = settings.MIDTRANS_IS_PRODUCTION

    def create_qris_transaction(self, bill, amount: Decimal, **kwargs) -> QRISCreateResult:
        """
        Panggil Midtrans API untuk buat QRIS transaction.

        Midtrans endpoint: POST /v2/charge
        Body: {
            "payment_type": "qris",
            "transaction_details": {
                "order_id": "FOODLIFE-{bill.id}-{timestamp}",
                "gross_amount": int(amount)
            },
            "qris": {
                "acquirer": "gopay"  // atau "airpay shopee"
            }
        }
        """
        from .models import QRISTransaction
        import requests

        timeout_minutes = getattr(settings, 'QRIS_TIMEOUT_MINUTES', 5)
        expires_at = timezone.now() + timezone.timedelta(minutes=timeout_minutes)

        order_id = f"FOODLIFE-{bill.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"

        try:
            response = requests.post(
                f"{self.base_url}/v2/charge",
                json={
                    "payment_type": "qris",
                    "transaction_details": {
                        "order_id": order_id,
                        "gross_amount": int(amount),
                    },
                    "qris": {
                        "acquirer": "gopay"
                    }
                },
                auth=(self.server_key, ''),
                timeout=30,
            )
            data = response.json()

            if data.get('status_code') != '201':
                return QRISCreateResult(
                    success=False,
                    error_message=data.get('status_message', 'Gateway error'),
                )

            # Extract QR string from response
            qr_string = ''
            qr_url = ''
            actions = data.get('actions', [])
            for action in actions:
                if action.get('name') == 'generate-qr-code':
                    qr_url = action.get('url', '')
                    break

            transaction_id = data.get('transaction_id', order_id)

            # Store in database
            QRISTransaction.objects.create(
                bill=bill,
                transaction_id=transaction_id,
                amount=amount,
                qr_string=qr_string or qr_url,
                status='pending',
                gateway_name='midtrans',
                gateway_response=data,
                expires_at=expires_at,
                created_by=kwargs.get('user'),
            )

            return QRISCreateResult(
                success=True,
                transaction_id=transaction_id,
                qr_string=qr_string,
                qr_url=qr_url,        # Midtrans sediakan URL QR image
                expires_at=expires_at,
            )

        except requests.RequestException as e:
            return QRISCreateResult(
                success=False,
                error_message=f"Network error: {str(e)}",
            )

    def check_status(self, transaction_id: str) -> QRISStatusResult:
        """
        Cek status transaksi via Midtrans API.

        GET /v2/{transaction_id}/status
        Response status_code mapping:
            200 = success (paid)
            201 = pending
            202 = denied
            407 = expired
        """
        from .models import QRISTransaction
        import requests

        try:
            txn = QRISTransaction.objects.get(transaction_id=transaction_id)
        except QRISTransaction.DoesNotExist:
            return QRISStatusResult(
                status='failed',
                transaction_id=transaction_id,
                error_message='Transaction not found in DB',
            )

        # Jika sudah terminal state, return langsung
        if txn.status in ('paid', 'expired', 'failed', 'cancelled'):
            return QRISStatusResult(
                status=txn.status,
                transaction_id=txn.transaction_id,
                paid_at=txn.paid_at,
            )

        # Poll Midtrans API
        try:
            response = requests.get(
                f"{self.base_url}/v2/{transaction_id}/status",
                auth=(self.server_key, ''),
                timeout=10,
            )
            data = response.json()
            txn.gateway_response = data

            midtrans_status = data.get('transaction_status', '')

            if midtrans_status == 'settlement':
                txn.status = 'paid'
                txn.paid_at = timezone.now()
            elif midtrans_status == 'expire':
                txn.status = 'expired'
            elif midtrans_status in ('deny', 'cancel'):
                txn.status = 'failed'

            txn.save()

            return QRISStatusResult(
                status=txn.status,
                transaction_id=txn.transaction_id,
                paid_at=txn.paid_at,
            )

        except requests.RequestException:
            # Network error — return current DB status, keep polling
            return QRISStatusResult(
                status=txn.status,
                transaction_id=txn.transaction_id,
            )

    def cancel_transaction(self, transaction_id: str) -> bool:
        """
        Cancel transaksi via Midtrans API.

        POST /v2/{transaction_id}/cancel
        """
        from .models import QRISTransaction
        import requests

        try:
            txn = QRISTransaction.objects.get(
                transaction_id=transaction_id, status='pending'
            )
        except QRISTransaction.DoesNotExist:
            return False

        try:
            response = requests.post(
                f"{self.base_url}/v2/{transaction_id}/cancel",
                auth=(self.server_key, ''),
                timeout=10,
            )
            data = response.json()
            txn.gateway_response = data
            txn.status = 'cancelled'
            txn.save()
            return True
        except requests.RequestException:
            # Cancel di DB saja jika API gagal
            txn.status = 'cancelled'
            txn.save()
            return True
```

2. **Tambah settings** di `config/settings.py`:

```python
# Payment Gateway
PAYMENT_GATEWAY = env('PAYMENT_GATEWAY', default='mock')  # 'mock' | 'midtrans' | 'xendit'
QRIS_TIMEOUT_MINUTES = int(env('QRIS_TIMEOUT_MINUTES', default='5'))

# Midtrans (jika PAYMENT_GATEWAY='midtrans')
MIDTRANS_SERVER_KEY = env('MIDTRANS_SERVER_KEY', default='')
MIDTRANS_BASE_URL = env('MIDTRANS_BASE_URL', default='https://api.sandbox.midtrans.com')
MIDTRANS_IS_PRODUCTION = env.bool('MIDTRANS_IS_PRODUCTION', default=False)
```

3. **Update factory** di `payment_gateway.py`:

```python
def get_payment_gateway() -> PaymentGateway:
    gateway_type = getattr(settings, 'PAYMENT_GATEWAY', 'mock')
    if gateway_type == 'mock':
        return MockQRISGateway()
    elif gateway_type == 'midtrans':
        return MidtransQRISGateway()
    else:
        raise ValueError(f"Unknown payment gateway: {gateway_type}")
```

4. **Update `qris_create` view** untuk handle `qr_url` dari production gateway:

```python
# Di apps/pos/views.py, dalam qris_create():

# Jika gateway return qr_url (production), pakai itu
# Jika tidak, generate QR image dari qr_string (mock/fallback)
qr_image = None
if result.qr_url:
    qr_image = result.qr_url  # URL langsung dari gateway
elif result.qr_string:
    # Generate QR image dari string (current behavior)
    import qrcode as qrlib
    import io, base64
    qr = qrlib.QRCode(...)
    qr.add_data(result.qr_string)
    ...
    qr_image = 'data:image/png;base64,' + base64.b64encode(buf.read()).decode()
```

5. **Hapus simulate endpoints** di production:

```python
# Di apps/pos/views.py
def qris_simulate_modal(request, bill_id, transaction_id):
    if not settings.DEBUG:
        return JsonResponse({'error': 'Not available in production'}, status=403)
    ...
```

### 7.2 Webhook (Opsional — Rekomendasi)

Selain polling, production gateway biasanya kirim webhook saat pembayaran berhasil. Ini lebih reliable daripada polling saja.

```python
# apps/pos/urls.py — tambah webhook endpoint
path('webhook/midtrans/', views.midtrans_webhook, name='midtrans_webhook'),
```

```python
# apps/pos/views.py
@csrf_exempt
@require_http_methods(["POST"])
def midtrans_webhook(request):
    """
    Webhook callback dari Midtrans saat status transaksi berubah.
    Midtrans kirim POST dengan body JSON berisi transaction_status.

    PENTING: Verifikasi signature sebelum proses!
    """
    import hashlib, json

    data = json.loads(request.body)
    order_id = data.get('order_id', '')
    status_code = data.get('status_code', '')
    gross_amount = data.get('gross_amount', '')
    signature_key = data.get('signature_key', '')

    # Verify signature
    server_key = settings.MIDTRANS_SERVER_KEY
    expected_signature = hashlib.sha512(
        f"{order_id}{status_code}{gross_amount}{server_key}".encode()
    ).hexdigest()

    if signature_key != expected_signature:
        return HttpResponse(status=403)

    # Update transaction status
    transaction_id = data.get('transaction_id', '')
    txn_status = data.get('transaction_status', '')

    try:
        txn = QRISTransaction.objects.get(transaction_id=transaction_id)
        txn.gateway_response = data

        if txn_status == 'settlement':
            txn.status = 'paid'
            txn.paid_at = timezone.now()
        elif txn_status == 'expire':
            txn.status = 'expired'
        elif txn_status in ('deny', 'cancel'):
            txn.status = 'cancelled'

        txn.save()
    except QRISTransaction.DoesNotExist:
        pass

    return HttpResponse(status=200)
```

### 7.3 Checklist Production

| # | Item | Status |
|---|------|--------|
| 1 | Implementasi gateway class (extend PaymentGateway) | ⬜ |
| 2 | Tambah settings MIDTRANS_SERVER_KEY, dll | ⬜ |
| 3 | Update factory get_payment_gateway() | ⬜ |
| 4 | Handle qr_url dari gateway (selain qr_string) | ⬜ |
| 5 | Disable simulate endpoints di production | ⬜ |
| 6 | Implementasi webhook endpoint (opsional) | ⬜ |
| 7 | Verify webhook signature | ⬜ |
| 8 | Test di Midtrans sandbox | ⬜ |
| 9 | Switch ke production URL + server key | ⬜ |
| 10 | Install `requests` library (pip install requests) | ⬜ |
| 11 | Monitor gateway_response untuk debugging | ⬜ |

---

## 8. Mock vs Production — Perbedaan

| Aspek | MockQRISGateway | Production Gateway |
|-------|-----------------|-------------------|
| **QR Generation** | Fake EMV string di local | Gateway API generate real QRIS |
| **Transaction ID** | `MOCK-{hex}` | Format dari provider |
| **QR String** | Fake format | Real QRIS EMV (ISO 20022) |
| **Payment Detection** | Manual via simulate endpoint | Webhook + polling API gateway |
| **Expiration** | App cek `expires_at` di DB | Gateway manage expiration |
| **gateway_response** | `{'simulated': True}` | Full response dari gateway |
| **Simulate Button** | Ada (untuk testing) | Tidak ada / disabled |
| **Network Required** | Tidak | Ya (API call ke gateway) |

---

## 9. Environment Variables

```env
# .env file
PAYMENT_GATEWAY=mock              # 'mock' untuk dev, 'midtrans' untuk production
QRIS_TIMEOUT_MINUTES=5            # QR code expiration (menit)

# Production only (Midtrans)
MIDTRANS_SERVER_KEY=SB-Mid-server-xxx
MIDTRANS_BASE_URL=https://api.sandbox.midtrans.com
MIDTRANS_IS_PRODUCTION=false

# Production only (Xendit) — jika pakai Xendit
XENDIT_SECRET_KEY=xnd_development_xxx
XENDIT_BASE_URL=https://api.xendit.co
```

---

## 10. Troubleshooting

### QR tidak muncul di modal
- Cek response `qris_create` di browser console — ada `qr_image` atau tidak?
- Jika `qr_image` null → library `qrcode` belum install (`pip install qrcode[pil]`)
- Jika production dan pakai `qr_url` → pastikan URL accessible dari browser

### Polling tidak detect pembayaran
- Cek interval polling (default 3 detik)
- Cek browser console untuk error di `_startQRISPolling()`
- Pastikan `check_status()` di gateway benar-benar call API provider
- Jika pakai webhook, pastikan URL webhook registered di dashboard provider

### Auto-submit tidak bekerja
- Cek `qrisState` di console — harus jadi `'paid'` dulu
- Setelah 800ms, `qrisState` di-set ke `'idle'` lalu `form.requestSubmit()`
- Pastikan form `#payment-form` ada di DOM (bisa hilang jika modal di-close)
- Cek HTMX binding — form harus punya `hx-post` yang valid

### Transaksi paid tapi Payment tidak tercatat
- Ini skenario BAHAYA — cek `_complete_qris_payment()` atau `process_payment()`
- Payment modal auto-submit harusnya create Payment via `process_payment()`
- Cek BillLog untuk trace: action='payment' + method='qris'
- Fallback: cek QRISTransaction status='paid' → manual reconciliation

---

## 11. Keamanan

1. **CSRF Token** — Semua POST request butuh `X-CSRFToken` header
2. **Login Required** — Semua QRIS endpoints butuh `@login_required`
3. **Bill Ownership** — Validasi bill_id exist sebelum operasi
4. **Idempotency** — `_complete_qris_payment()` cek Payment sudah ada sebelum create
5. **Webhook Signature** — Verifikasi signature dari payment provider
6. **Auto-cancel** — Transaksi pending di-cancel otomatis saat buat transaksi baru
7. **Auto-submit** — Setelah QRIS paid, form HARUS auto-submit (bypass canPay) agar tidak ada uang masuk tanpa tercatat

---

## 12. Data Flow Summary

```
Frontend POST amount=150000
         │
         ▼
qris_create() → gateway.create_qris_transaction()
         │        → INSERT QRISTransaction (status=pending)
         │        → Return QRISCreateResult
         │
         ▼
Return JSON {transaction_id, qr_image, qr_string}
         │
         ▼
Frontend: Show QR, start polling setiap 3 detik
         │
         ▼
qris_status() → gateway.check_status()
         │        → SELECT QRISTransaction WHERE transaction_id=X
         │        → Cek expired? → Update status
         │
         ▼
Jika status='paid':
  Frontend → auto-submit form → process_payment()
         │     → CREATE Payment (method=qris, reference=transaction_id)
         │     → Bill.status = 'paid'
         │     → Print receipt
         │
         ▼
Return payment_success.html
```

---

## 13. Logging & Audit Trail

Logging detail untuk analisa bank dan debugging. Ada 2 layer: **Backend (Python)** dan **Frontend (Browser Console)**.

### 13.1 Backend Logging (Python `pos.qris` logger)

Logger name: `pos.qris` — bisa dikonfigurasi di Django `LOGGING` settings.

#### Log Events

| Event | Level | Kapan | Data |
|-------|-------|-------|------|
| `QRIS_CREATE_OK` | INFO | Transaksi berhasil dibuat | bill, txn_id, amount, remaining, has_qr_image, expires_at, elapsed_ms, user |
| `QRIS_CREATE_GATEWAY_ERROR` | ERROR | Gateway gagal buat transaksi | bill, amount, error, elapsed_ms |
| `QRIS_CREATE_INVALID_AMOUNT` | WARN | Amount tidak valid | bill, raw_amount, user |
| `QRIS_CREATE_ZERO_AMOUNT` | WARN | Amount ≤ 0 | bill, amount, user |
| `QRIS_CREATE_OVER_REMAINING` | WARN | Amount > sisa tagihan | bill, amount, remaining, user |
| `QRIS_QR_IMAGE_ERROR` | WARN | QR image generation gagal | txn_id, error |
| `QRIS_AUTO_CANCELLED` | INFO | Transaksi lama di-cancel otomatis | bill, count |
| `QRIS_STATUS` | INFO | Status berubah (non-pending) | bill, txn_id, status, paid_at, elapsed_ms |
| `QRIS_STATUS_CHANGE` | INFO | Transisi status pending→terminal | txn_id, bill, status, prev, amount, elapsed_s, paid_at, gateway |
| `QRIS_STATUS_NOT_FOUND` | WARN | Transaksi tidak ditemukan | txn_id |
| `QRIS_EXPIRED` | INFO | Transaksi expired (timeout) | txn_id, bill, amount, elapsed_s, timeout |
| `QRIS_CANCELLED` | INFO | Transaksi di-cancel kasir | txn_id, bill, amount, elapsed_s |
| `QRIS_CANCEL_OK` | INFO | Cancel berhasil (view level) | bill, txn_id, user |
| `QRIS_CANCEL_FAILED` | WARN | Cancel gagal (not found/not pending) | bill, txn_id, user |
| `QRIS_SIMULATED` | INFO | DEV: Transaksi disimulasi paid | txn_id, bill, amount, elapsed_s, paid_at |
| `QRIS_SIMULATE_MODAL_OK` | INFO | DEV: Simulate modal berhasil | bill, txn_id, user |

#### Contoh Log Output

```
INFO pos.qris QRIS_CREATE_OK bill=42 txn_id=MOCK-A1B2C3D4E5F6 amount=150000 remaining=150000 has_qr_image=True expires_at=2026-02-12T10:05:00+07:00 elapsed=45ms user=kasir01
INFO pos.qris QRIS_STATUS bill=42 txn_id=MOCK-A1B2C3D4E5F6 status=paid paid_at=2026-02-12T10:03:22+07:00 elapsed=3ms
INFO pos.qris QRIS_STATUS_CHANGE txn_id=MOCK-A1B2C3D4E5F6 bill=42 status=paid prev=pending amount=150000 elapsed=198.5s paid_at=2026-02-12T10:03:22+07:00 gateway=mock
```

#### Konfigurasi Django Logging

```python
# config/settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'qris': {
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'qris_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/qris.log',
            'formatter': 'qris',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'qris',
        },
    },
    'loggers': {
        'pos.qris': {
            'handlers': ['qris_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

### 13.2 Frontend Logging (Browser Console)

Semua log frontend pakai prefix `[QRIS]` agar mudah di-filter di browser DevTools.

#### Console Log Events

| Event | Level | Kapan | Data |
|-------|-------|-------|------|
| `[QRIS] Creating transaction` | log | Mulai generate QR | bill, amount, field, timestamp |
| `[QRIS] Create response` | log | HTTP response diterima | status, response_time_ms |
| `[QRIS] Transaction created` | log | Transaksi berhasil | txn_id, amount, expires_at, has_qr_image, response_time_ms |
| `[QRIS] Create failed` | error | Gateway error | error_msg, response_time_ms |
| `[QRIS] Create network error` | error | Network timeout/gagal | error_msg, response_time_ms |
| `[QRIS] Polling started` | log | Mulai polling | interval, txn_id |
| `[QRIS] Polling #N` | log | Setiap 5 poll | status, elapsed_s, response_time_ms |
| `[QRIS] ✓ PAYMENT CONFIRMED` | log | Pembayaran dikonfirmasi | txn_id, paid_at, poll_count, wait_time_s, response_time_ms, amount, bill, timestamp |
| `[QRIS] ✗ Transaction ended` | warn | Expired/cancelled/failed | txn_id, status, poll_count, elapsed_s, response_time_ms, amount, bill, timestamp |
| `[QRIS] Poll #N network error` | error | Polling gagal | error_msg, response_time_ms, total_errors, txn_id |
| `[QRIS] Auto-submitting` | log | Form auto-submit | txn_id, amount, total, method, timestamp |
| `[QRIS] CRITICAL — form not found` | error | Form hilang dari DOM | — |
| `[QRIS] Cancelling` | log | Cancel dipanggil | txn_id, state, poll_count, elapsed_s, bill, timestamp |
| `[QRIS] DEV Simulate` | log | Simulate button | txn_id, amount, elapsed_s, timestamp |

#### Contoh Console Output

```
[QRIS] Creating transaction — bill: 42 amount: 150000 field: qrcontent time: 2026-02-12T10:00:00.000Z
[QRIS] Create response — status: 200 time: 45ms
[QRIS] Transaction created — txn_id: MOCK-A1B2C3D4E5F6 amount: 150000 expires_at: 2026-02-12T03:05:00Z has_qr_image: true response_time: 45ms
[QRIS] Polling started — interval: 3000ms, txn_id: MOCK-A1B2C3D4E5F6
[QRIS] Polling #5 — status: pending elapsed: 15.2s response: 12ms
[QRIS] Polling #10 — status: pending elapsed: 30.1s response: 8ms
[QRIS] ✓ PAYMENT CONFIRMED — txn_id: MOCK-A1B2C3D4E5F6 status: paid paid_at: 2026-02-12T03:03:22Z poll_count: 11 wait_time: 33.5s last_poll_response: 10ms amount: 150000 bill: 42 time: 2026-02-12T10:03:22.000Z
[QRIS] Auto-submitting payment form — txn_id: MOCK-A1B2C3D4E5F6 amount: 150000 total: 150000 method: qris_bca_cpm time: 2026-02-12T10:03:23.000Z
```

#### Cara Filter di Browser

1. Buka DevTools (F12) → Console
2. Filter: ketik `[QRIS]` di filter box
3. Untuk export: klik kanan di console → "Save as..." → simpan sebagai `.log` file

### 13.3 Key Metrics untuk Bank

Data penting yang bisa diekstrak dari log untuk laporan ke bank:

| Metric | Sumber | Contoh |
|--------|--------|--------|
| **Response time create** | Backend `elapsed_ms` | 45ms (gateway API call) |
| **Total wait time** | Frontend `wait_time` | 33.5s (dari QR muncul sampai paid) |
| **Poll count** | Frontend `poll_count` | 11 (berapa kali polling sebelum confirmed) |
| **Poll response time** | Frontend `last_poll_response` | 10ms (terakhir sebelum confirmed) |
| **Status transitions** | Backend `QRIS_STATUS_CHANGE` | pending→paid, pending→expired |
| **Expiry rate** | Count `QRIS_EXPIRED` vs `QRIS_CREATE_OK` | Berapa % expired |
| **Cancel rate** | Count `QRIS_CANCELLED` vs `QRIS_CREATE_OK` | Berapa % di-cancel kasir |
| **Gateway errors** | Backend `QRIS_CREATE_GATEWAY_ERROR` | Error dari API gateway |
| **Network errors** | Frontend `poll network error` | Masalah koneksi ke server |
| **Transaction ID** | Semua log | Untuk trace end-to-end |
| **paid_at timestamp** | Backend `QRIS_STATUS_CHANGE` | Waktu exact pembayaran |
| **gateway_response** | QRISTransaction model | Raw response dari bank (JSON) |

### 13.4 Reconciliation Query

Untuk mencocokkan data QRIS dengan bank:

```sql
-- Semua transaksi QRIS hari ini
SELECT
    transaction_id,
    amount,
    status,
    gateway_name,
    gateway_response,
    created_at,
    paid_at,
    expires_at,
    EXTRACT(EPOCH FROM (paid_at - created_at)) AS wait_seconds,
    bill_id
FROM pos_qris_transaction
WHERE created_at >= CURRENT_DATE
ORDER BY created_at DESC;

-- Transaksi PAID yang tidak punya Payment record (BAHAYA)
SELECT qt.transaction_id, qt.amount, qt.bill_id, qt.paid_at
FROM pos_qris_transaction qt
LEFT JOIN pos_payment p ON p.reference = qt.transaction_id AND p.method = 'qris'
WHERE qt.status = 'paid'
  AND qt.created_at >= CURRENT_DATE
  AND p.id IS NULL;

-- Summary per status
SELECT
    status,
    COUNT(*) AS count,
    SUM(amount) AS total_amount,
    AVG(EXTRACT(EPOCH FROM (COALESCE(paid_at, NOW()) - created_at))) AS avg_wait_seconds
FROM pos_qris_transaction
WHERE created_at >= CURRENT_DATE
GROUP BY status;
```

### 13.5 Database Audit Log — `QRISAuditLog` (`pos_qris_audit_log`)

Selain file log dan console log, **semua event QRIS juga disimpan ke database table** `pos_qris_audit_log` untuk kemudahan query, export CSV, dan analisa oleh pihak bank.

#### Table Schema

| Column | Type | Keterangan |
|--------|------|-----------|
| `id` | BigAutoField | Primary key |
| `transaction_id` | FK → QRISTransaction | Link ke transaksi (nullable) |
| `bill_id` | FK → Bill | Link ke bill (nullable) |
| `event` | CharField(30) | Jenis event (lihat tabel di bawah) |
| `txn_ref` | CharField(100) | QRIS transaction_id string (indexed) |
| `status_before` | CharField(20) | Status sebelum event |
| `status_after` | CharField(20) | Status sesudah event |
| `amount` | Decimal(12,2) | Jumlah transaksi |
| `gateway_name` | CharField(50) | Nama gateway (mock/midtrans/xendit) |
| `response_time_ms` | Integer | Response time dari gateway (ms) |
| `elapsed_since_create_s` | Float | Detik sejak QR dibuat (wait time) |
| `error_message` | Text | Pesan error jika ada |
| `extra_data` | JSONField | Data tambahan (expires_at, paid_at, dll) |
| `user` | FK → User | Kasir yang melakukan aksi |
| `ip_address` | GenericIPAddress | IP address client |
| `created_at` | DateTime | Timestamp event (auto, indexed) |

#### Event Types

| Event | Kapan Dicatat |
|-------|--------------|
| `create` | QR code berhasil dibuat |
| `status_check` | Status poll mengembalikan non-pending (paid/expired/cancelled/failed) |
| `status_change` | Status berubah dari pending ke non-paid terminal state |
| `payment_confirmed` | Pembayaran berhasil dikonfirmasi (status → paid) |
| `expired` | Transaksi expired karena timeout |
| `cancelled` | Kasir cancel manual |
| `auto_cancel` | Cancel otomatis karena kasir generate QR baru |
| `simulate` | DEV: pembayaran disimulasi |
| `error` | Error: invalid amount, over remaining, not found, dll |
| `gateway_timeout` | Gateway tidak merespons dalam waktu yang ditentukan |
| `gateway_error` | Gateway mengembalikan error |

#### Query Audit Log untuk Bank

```sql
-- Semua event QRIS hari ini (kronologis)
SELECT
    created_at,
    event,
    txn_ref,
    status_before,
    status_after,
    amount,
    response_time_ms,
    elapsed_since_create_s,
    error_message,
    gateway_name
FROM pos_qris_audit_log
WHERE created_at >= CURRENT_DATE
ORDER BY created_at;

-- Rata-rata response time per event type
SELECT
    event,
    COUNT(*) AS total,
    AVG(response_time_ms) AS avg_response_ms,
    MAX(response_time_ms) AS max_response_ms,
    MIN(response_time_ms) AS min_response_ms
FROM pos_qris_audit_log
WHERE created_at >= CURRENT_DATE
  AND response_time_ms IS NOT NULL
GROUP BY event;

-- Waktu tunggu pembayaran (dari create sampai paid)
SELECT
    txn_ref,
    amount,
    elapsed_since_create_s AS wait_seconds,
    response_time_ms,
    created_at AS paid_at,
    extra_data
FROM pos_qris_audit_log
WHERE event = 'payment_confirmed'
  AND created_at >= CURRENT_DATE
ORDER BY created_at DESC;

-- Error log untuk debugging
SELECT
    created_at,
    event,
    txn_ref,
    error_message,
    extra_data,
    ip_address
FROM pos_qris_audit_log
WHERE event IN ('error', 'gateway_error', 'gateway_timeout')
  AND created_at >= CURRENT_DATE
ORDER BY created_at DESC;

-- Transaksi yang di-cancel (manual + auto) — analisa kenapa banyak cancel
SELECT
    created_at,
    event,
    txn_ref,
    elapsed_since_create_s,
    extra_data ->> 'reason' AS cancel_reason
FROM pos_qris_audit_log
WHERE event IN ('cancelled', 'auto_cancel')
  AND created_at >= CURRENT_DATE
ORDER BY created_at DESC;
```

#### Akses via Django Admin

Buka `/admin/pos/qrisauditlog/` — bisa filter by event type, gateway, tanggal. Search by txn_ref atau bill number.
