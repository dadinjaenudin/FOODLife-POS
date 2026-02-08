# Print Receipt Integration Guide

## Overview
POS Launcher sekarang mendukung print struk otomatis menggunakan template dari database (`core_receipttemplate`).

## Architecture

```
POS Django (Browser)  →  Local API (Flask)  →  Receipt Printer
                         Port 5000
```

### Flow:
1. User klik "Bayar" di POS Django
2. Django POST bill data ke `http://127.0.0.1:5000/api/print/receipt`
3. Local API fetch template dari Django API `/api/terminal/receipt-template`
4. Generate formatted receipt text
5. Send to printer via ESC/POS commands

---

## API Endpoints

### 1. Get Receipt Template (Django API)
**Endpoint:** `GET /api/terminal/receipt-template?terminal_code=BOE-001`

**Response:**
```json
{
  "success": true,
  "template": {
    "id": 1,
    "template_name": "Standard Receipt",
    "paper_width": 42,
    "show_logo": false,
    "header_line_1": "BOE KOPI TIAM",
    "header_line_2": "Jl. ABC Bandung",
    "header_line_3": "0833333332",
    "show_receipt_number": true,
    "show_date_time": true,
    "show_cashier_name": true,
    "show_customer_name": true,
    "show_table_number": true,
    "show_item_code": true,
    "show_modifiers": true,
    "price_alignment": "right",
    "show_currency_symbol": true,
    "show_subtotal": true,
    "show_tax": true,
    "show_service_charge": true,
    "show_discount": true,
    "show_payment_method": true,
    "show_paid_amount": true,
    "show_change": true,
    "footer_line_1": "Terima kasih!",
    "footer_line_2": "Selamat datang kembali",
    "auto_print": true,
    "auto_cut": true,
    "feed_lines": 4
  }
}
```

### 2. Print Receipt (Local API)
**Endpoint:** `POST http://127.0.0.1:5000/api/print/receipt`

**Request Body:**
```json
{
  "bill_number": "INV-20260208-001",
  "date": "08/02/2026",
  "time": "14:30:25",
  "cashier": "Kasir 1",
  "customer_name": "John Doe",
  "table_number": "T-05",
  "items": [
    {
      "code": "ESP001",
      "name": "Espresso",
      "quantity": 2,
      "price": 25000,
      "category": "Coffee",
      "modifiers": [
        {"name": "Extra Shot"},
        {"name": "Less Sugar"}
      ]
    },
    {
      "code": "CAP001",
      "name": "Cappuccino",
      "quantity": 1,
      "price": 30000,
      "category": "Coffee",
      "modifiers": []
    }
  ],
  "subtotal": 80000,
  "tax": 8000,
  "service_charge": 4000,
  "discount": 2000,
  "total": 90000,
  "payment_method": "Cash",
  "paid_amount": 100000,
  "change": 10000,
  "qr_code": null,
  "printer_name": null
}
```

**Response:**
```json
{
  "success": true,
  "printer": "POS-58 USB Printer",
  "template": "Standard Receipt"
}
```

---

## Django POS Integration

### Step 1: Add to payment confirmation view
File: `apps/pos/views.py`

```python
def confirm_payment(request, bill_id):
    # ... existing payment processing code ...
    
    # After successful payment, trigger print
    if bill.payment_status == 'paid':
        # Prepare receipt data
        receipt_data = {
            'bill_number': bill.bill_number,
            'date': bill.created_at.strftime('%d/%m/%Y'),
            'time': bill.created_at.strftime('%H:%M:%S'),
            'cashier': request.user.get_full_name() or request.user.username,
            'customer_name': bill.customer_name or '',
            'table_number': bill.table.table_number if bill.table else '',
            'items': [
                {
                    'code': item.product.product_code,
                    'name': item.product.name,
                    'quantity': item.quantity,
                    'price': float(item.unit_price),
                    'category': item.product.category.name if item.product.category else '',
                    'modifiers': [
                        {'name': mod.modifier.name}
                        for mod in item.modifiers.all()
                    ]
                }
                for item in bill.items.all()
            ],
            'subtotal': float(bill.subtotal),
            'tax': float(bill.tax_amount or 0),
            'service_charge': float(bill.service_charge or 0),
            'discount': float(bill.discount_amount or 0),
            'total': float(bill.total_amount),
            'payment_method': bill.payment_method,
            'paid_amount': float(bill.paid_amount or bill.total_amount),
            'change': float(bill.change_amount or 0),
            'qr_code': bill.qr_payment_code if bill.payment_method == 'qris' else None,
        }
        
        # Send to local API for printing
        try:
            import requests
            response = requests.post(
                'http://127.0.0.1:5000/api/print/receipt',
                json=receipt_data,
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"[Print] Receipt printed successfully for {bill.bill_number}")
            else:
                print(f"[Print] Failed to print receipt: {response.status_code}")
        except Exception as e:
            print(f"[Print] Error sending to printer: {e}")
            # Don't fail payment if printing fails
    
    return JsonResponse({'success': True, 'bill_id': str(bill.id)})
```

### Step 2: Frontend trigger (JavaScript)
File: `templates/pos/pos_main.html`

```javascript
async function confirmPayment(billId, paymentMethod) {
    const response = await fetch(`/pos/bill/${billId}/payment/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': CSRF_TOKEN
        },
        body: JSON.stringify({
            payment_method: paymentMethod,
            auto_print: true  // Enable auto print
        })
    });
    
    const result = await response.json();
    
    if (result.success) {
        // Print will happen automatically via local API
        showNotification('Pembayaran berhasil! Struk sedang dicetak...', 'success');
    }
}
```

---

## Testing

### Test 1: Template Retrieval
```bash
curl "http://127.0.0.1:8001/api/terminal/receipt-template?terminal_code=BOE-001"
```

### Test 2: Print Receipt
```bash
curl -X POST http://127.0.0.1:5000/api/print/receipt \
  -H "Content-Type: application/json" \
  -d '{
    "bill_number": "TEST-001",
    "date": "08/02/2026",
    "time": "15:00:00",
    "cashier": "Test Cashier",
    "items": [
      {
        "name": "Test Item",
        "quantity": 1,
        "price": 10000
      }
    ],
    "subtotal": 10000,
    "total": 10000,
    "payment_method": "Cash",
    "paid_amount": 10000,
    "change": 0
  }'
```

### Test 3: Check Printer Status
```bash
curl http://127.0.0.1:5000/health
```

---

## Receipt Template Configuration

### Database: `core_receipttemplate`

**Template Fields:**
- `paper_width`: 42 (default), 32 (narrow), 58 (wide)
- `show_logo`: Display logo at top
- `header_line_1-4`: Store name, address, phone
- `show_receipt_number`: Bill number
- `show_date_time`: Date and time
- `show_cashier_name`: Cashier name
- `show_customer_name`: Customer name
- `show_table_number`: Table number
- `show_item_code`: Product code
- `show_modifiers`: Item modifiers
- `price_alignment`: "left" or "right"
- `show_currency_symbol`: Show "Rp"
- `show_subtotal`: Subtotal before tax
- `show_tax`: Tax amount
- `show_service_charge`: Service charge
- `show_discount`: Discount amount
- `show_payment_method`: Payment method
- `show_paid_amount`: Paid amount
- `show_change`: Change returned
- `footer_line_1-3`: Thank you message
- `auto_cut`: Auto cut paper
- `feed_lines`: Feed lines after print

### Update Template via Django Admin:
```
http://127.0.0.1:8001/admin/core/receipttemplate/
```

---

## Troubleshooting

### Print tidak keluar struk
1. Cek POS Launcher running: `netstat -ano | findstr :5000`
2. Cek printer terhubung: Device Manager → Printers
3. Test endpoint: `curl http://127.0.0.1:5000/health`
4. Cek log di console POS Launcher

### Template tidak ditemukan
1. Cek database: `SELECT * FROM core_receipttemplate WHERE is_active = true;`
2. Pastikan template ada untuk brand/store/company
3. Test API: `curl "http://127.0.0.1:8001/api/terminal/receipt-template?terminal_code=BOE-001"`

### Format struk tidak sesuai
1. Edit template di Django Admin
2. Adjust `paper_width` sesuai printer (32, 42, 58, 80)
3. Toggle show/hide fields sesuai kebutuhan

---

## Next Steps

1. ✅ Create receipt template di Django Admin
2. ✅ Test endpoint `/api/terminal/receipt-template`
3. ✅ Test print via local API
4. 🔲 Integrate di POS payment flow
5. 🔲 Add auto-print toggle di terminal settings
6. 🔲 Add reprint button di bill history

---

## Files Modified

### Backend (Django):
- `apps/core/api_terminal.py` - Added `get_receipt_template()` endpoint
- `apps/core/urls_api.py` - Added route for receipt template

### POS Launcher:
- `pos_launcher_qt/local_api.py` - Added:
  - `fetch_receipt_template()` - Get template from Django
  - `format_receipt_text()` - Generate formatted receipt
  - `api_print_receipt()` - POST endpoint for printing
  
### Database:
- `core_receipttemplate` - Template configuration
- `core_posterminal` - Printer settings (receipt_printer_name, auto_print_receipt)

---

**Status:** ✅ Ready for integration
**Last Updated:** 2026-02-08
