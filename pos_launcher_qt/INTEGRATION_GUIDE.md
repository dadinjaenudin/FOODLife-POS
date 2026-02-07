# POS Launcher Integration Guide
**Event-Based Hybrid Architecture**

## 🎯 Overview
Implementasi Event-Based Hybrid untuk integrasi antara POS Web (Edge Server) dengan Local API (pos_launcher_qt) untuk:
- ✅ **Customer Display**: Real-time cart updates
- ✅ **Receipt Print**: Local ESC/POS printer
- ❌ **Kitchen Print**: TIDAK dalam scope (trigger dari fire order)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Edge Server                            │
│  (Django POS Web - Running on http://edge-server:8001)     │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Loaded with ?kiosk=1 parameter
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    PyQt6 WebView Launcher                    │
│  (pos_launcher_qt - Embedded Chromium Engine)               │
│                                                              │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │  Main Window     │         │  Customer Window  │         │
│  │  (Monitor 1)     │         │  (Monitor 2)      │         │
│  │  POS Web         │         │  Customer Display │         │
│  └──────────────────┘         └──────────────────┘         │
│                                                              │
│         │                              ▲                     │
│         │ JavaScript Events            │ SSE Stream         │
│         ▼                              │                     │
│  ┌──────────────────────────────────────────────────┐       │
│  │         Local API Server (Flask)                 │       │
│  │         http://127.0.0.1:5000                    │       │
│  │                                                   │       │
│  │  POST /api/customer-display/update               │       │
│  │  POST /api/print                                 │       │
│  │  GET  /api/customer-display/stream (SSE)         │       │
│  └──────────────────────────────────────────────────┘       │
│                            │                                  │
└────────────────────────────┼──────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │ ESC/POS Printer│
                    │ (Windows/Linux)│
                    └────────────────┘
```

---

## 📋 Implementation Details

### 1. **Kiosk Mode Detection**
POS launcher adds `?kiosk=1` parameter when loading POS web:
```python
# pos_launcher_qt/pos_launcher_qt.py
separator = '&' if '?' in pos_url else '?'
pos_url = f"{pos_url}{separator}kiosk=1"
```

JavaScript checks kiosk mode:
```javascript
function isKioskMode() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('kiosk') === '1';
}
```

### 2. **Customer Display Updates** (Real-time)
Triggered on every cart change:

#### Trigger Points:
- `quickOrder().addItem()` - Add product
- `quickOrder().removeItem()` - Remove product
- `quickOrder().increaseQty()` - Increase quantity
- `quickOrder().decreaseQty()` - Decrease quantity

#### Data Flow:
```javascript
// templates/pos/main.html
function updateCustomerDisplay(items, total, paymentAmount, paymentMethod) {
    if (!isKioskMode()) return;
    
    fetch('http://127.0.0.1:5000/api/customer-display/update', {
        method: 'POST',
        body: JSON.stringify({
            items: [...],  // Product list
            subtotal: total,
            total: total,
            payment_amount: paymentAmount,
            payment_method: paymentMethod
        })
    });
}
```

#### Local API Handling:
```python
# pos_launcher_qt/local_api.py
@app.route('/api/customer-display/update', methods=['POST'])
def update_customer_display():
    global customer_display_data
    customer_display_data = request.json
    return jsonify({'success': True})
```

#### SSE Stream:
Customer display window subscribes to real-time updates via Server-Sent Events:
```javascript
// pos_launcher_qt/customer_display.html
const eventSource = new EventSource('http://127.0.0.1:5000/api/customer-display/stream');
eventSource.onmessage = function(event) {
    const data = JSON.parse(event.data);
    updateDisplay(data);  // Update UI
};
```

### 3. **Receipt Print** (Post-Payment)
Triggered after payment completes:

#### Trigger Point:
- `paymentComplete` event fired by Django view after successful payment

#### Data Flow:
```javascript
// templates/pos/main.html
document.body.addEventListener('paymentComplete', function(e) {
    // Extract bill ID from success modal
    const billId = extractBillIdFromModal();
    
    // Fetch complete bill data from server
    fetch(`/pos/bill/${billId}/data/`)
        .then(response => response.json())
        .then(billData => {
            // Send to local printer
            fetch('http://127.0.0.1:5000/api/print', {
                method: 'POST',
                body: JSON.stringify(billData)
            });
        });
});
```

#### Django API Endpoint:
```python
# apps/pos/views.py
@login_required
def bill_data_json(request, bill_id):
    """Return bill data as JSON for local printer integration"""
    bill = get_object_or_404(Bill, id=bill_id)
    data = {
        'outlet_name': bill.outlet.name,
        'bill_number': bill.bill_number,
        'items': [...],
        'payments': [...],
        'total': float(bill.total),
        ...
    }
    return JsonResponse(data)
```

URL Route:
```python
# apps/pos/urls.py
path('bill/<int:bill_id>/data/', views.bill_data_json, name='bill_data_json'),
```

#### Local API Print Handling:
```python
# pos_launcher_qt/local_api.py
@app.route('/api/print', methods=['POST'])
def print_receipt():
    receipt_data = request.json
    
    # Generate ESC/POS commands
    escpos_data = generate_receipt_escpos(receipt_data)
    
    # Print based on OS
    if platform.system() == 'Windows':
        print_windows(escpos_data)
    else:
        print_linux(escpos_data)
    
    return jsonify({'success': True})
```

---

## 🧪 Testing

### Prerequisites:
1. Django server running on `http://127.0.0.1:8001`
2. Active shift opened by cashier
3. Receipt printer configured (Windows: default printer, Linux: CUPS)

### Test Steps:

#### **Test 1: Customer Display Integration**
```bash
# 1. Start launcher
cd pos_launcher_qt
python pos_launcher_qt.py

# Expected:
# - Main POS window opens on monitor 1
# - Customer display window opens on monitor 2
# - Local API starts on port 5000

# 2. In POS web, click "Quick Order"

# 3. Add products to cart
# Expected: Customer display updates in real-time with:
# - Product name, quantity, price
# - Subtotal updates

# 4. Increase/decrease quantity
# Expected: Customer display reflects changes immediately

# 5. Remove product
# Expected: Customer display updates list
```

#### **Test 2: Receipt Print Integration**
```bash
# 1. In Quick Order modal:
# - Add products
# - Select payment method (Cash/Card/QRIS)
# - Enter payment amount
# - Click "Submit"

# Expected:
# - Payment success modal shows
# - Django queue_print_receipt() runs (server-side)
# - JavaScript extracts bill ID
# - Fetches bill data from /pos/bill/{id}/data/
# - Sends to http://127.0.0.1:5000/api/print
# - Receipt prints on local printer

# 2. Check console logs:
# Browser console: "🖨️ Receipt sent to local printer"
# Terminal: "Print job completed"
```

#### **Test 3: Error Handling**
```bash
# Test without launcher (browser only):
# - Go to http://127.0.0.1:8001/pos/ (no ?kiosk=1)
# - Add products in Quick Order
# - Expected: No errors, local API calls skipped

# Test with launcher (port 5000 blocked):
# - Block port 5000
# - Start launcher
# - Expected: Graceful failure with console warnings
```

---

## 🔍 Debugging

### Check Local API Status:
```bash
curl http://127.0.0.1:5000/health
# Should return: {"status": "ok", "service": "POS Local API"}
```

### Monitor SSE Stream:
```bash
curl -N http://127.0.0.1:5000/api/customer-display/stream
# Should show: data: {"items":[],"total":0,...}
```

### Check Browser Console:
```javascript
// Should see:
📺 Customer display updated: {success: true}
💰 Payment complete, sending to local printer...
🖨️ Receipt sent to local printer: {success: true}
```

### Check Flask Logs:
```bash
# Should see:
[POST] /api/customer-display/update - 200
[POST] /api/print - 200
Print job completed
```

---

## 📝 Key Files Modified

### Django Backend:
- `apps/pos/views.py` - Added `bill_data_json()` view
- `apps/pos/urls.py` - Added `/bill/<int:bill_id>/data/` route
- `templates/pos/main.html` - Added JavaScript integration

### Launcher:
- `pos_launcher_qt/pos_launcher_qt.py` - Added `?kiosk=1` parameter
- `pos_launcher_qt/local_api.py` - Customer display & print endpoints (already exists)
- `pos_launcher_qt/customer_display.html` - SSE client (already exists)

---

## ⚙️ Configuration

### config.json (Launcher):
```json
{
    "edge_server": "http://127.0.0.1:8001",
    "terminal_code": "POS-001",
    "company_code": "YOGYA",
    "brand_code": "FOODLIFE",
    "store_code": "YGY01"
}
```

### Printer Configuration:
```python
# Windows: Uses default printer via win32print
# Linux: Uses default CUPS printer

# To change printer:
# - Windows: Control Panel > Devices > Printers > Set as Default
# - Linux: lpadmin -d <printer-name>
```

---

## 🚀 Production Deployment

### Bundle Launcher (optional):
```bash
cd pos_launcher_qt
pip install pyinstaller
pyinstaller --onefile --windowed --add-data "customer_display.html:." pos_launcher_qt.py
```

### Auto-start on Boot:
**Windows:**
- Copy `pos_launcher_qt.exe` to `shell:startup` folder

**Linux:**
- Add to systemd service (see SERVICE_GUIDE_LINUX.md)

---

## 🔐 Security Notes

- Local API runs on `127.0.0.1` (localhost only)
- No authentication needed (local-only access)
- CORS enabled for Edge Server domain
- SSL not required (local network)

---

## 📞 Support

Scope in this integration:
- ✅ Customer display real-time updates
- ✅ Receipt print via local printer
- ❌ Kitchen print (handled separately by fire order flow)

For issues:
- Check browser console for JavaScript errors
- Check Flask terminal for API errors
- Verify port 5000 not blocked by firewall
- Test printer with `echo "test" | lp` (Linux) or Print Test Page (Windows)

---

**Last Updated:** 2026-02-07  
**Status:** ✅ Implementation Complete
