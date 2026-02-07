# POS Launcher - Quick Start Guide

## ✅ STATUS: READY TO USE!

Your POS Launcher with dual display, QR payment, and local printing is fully configured.

---

## 🚀 How to Start

```powershell
cd pos_launcher_qt
python pos_launcher_qt.py
```

This launches:
1. ✅ Flask API Server (port 5000) - Auto-starts
2. ✅ Main POS Window - Edge Server webview
3. ✅ Customer Display - Billing info + slideshow + QR payment

---

## 📺 Screen Layout

### Main POS Window (Cashier)
- **Content**: Edge Server POS interface (`http://192.168.1.100:8000/pos/?kiosk=1`)
- **Screen**: Primary monitor, fullscreen
- **Purpose**: Order entry and management

### Customer Display
- **Content**: Local Flask server (`http://127.0.0.1:5000/`)
- **Screen**: Secondary monitor, fullscreen
- **Layout**:
  ```
  ┌─────────────────────────────────────┐
  │  🏪 Brand Name & Logo (Header)      │
  ├───────────────┬─────────────────────┤
  │               │                     │
  │  Billing Info │  Promo Slideshow    │
  │  (45% Left)   │  (55% Right)        │
  │               │                     │
  │  - Items      │  - Auto-rotating    │
  │  - Prices     │  - Custom slides    │
  │  - Total      │  - Your promos      │
  │               │                     │
  ├───────────────┴─────────────────────┤
  │  📢 Running Text (Footer)           │
  └─────────────────────────────────────┘
  
  When payment: Full-screen QR modal ⬆️
  ```

---

## 🔄 Real-Time Integration

The system uses **Event-Based Hybrid** architecture - everything updates instantly!

### Automatic Updates
```javascript
// In templates/pos/main.html - Already integrated!

// 1. Cart changes → Update customer display
updateCustomerDisplay();  // Called on add/remove items

// 2. Order complete → Print receipt
sendReceiptToLocalPrinter(billId);

// 3. Payment QR → Show on customer display
showQRCode(paymentData);

// 4. Payment done → Hide QR
hideQRCode();
```

---

## 🎨 Customization

### Change Branding, Slides, Running Text

Edit: `customer_display_config.json`

```json
{
    "brand": {
        "name": "YOGYA Food Life",
        "tagline": "Delicious Food, Happy Life",
        "logo_url": "https://your-domain.com/logo.png"
    },
    "slideshow": [
        {
            "title": "🍔 Special Combo!",
            "subtitle": "Get 30% off on combo meals",
            "background_color": "#FF6B6B",
            "duration": 5000
        },
        {
            "title": "🎉 New Menu!",
            "subtitle": "Try our fresh new dishes",
            "background_color": "#4ECDC4",
            "duration": 5000
        }
    ],
    "running_text": "🎁 Welcome! Special promo today: Buy 2 Get 1 Free! Limited time only! 🎉",
    "theme": {
        "primary_color": "#667eea",
        "secondary_color": "#764ba2"
    }
}
```

**Changes apply immediately** (refresh customer display window).

---

## 💳 QR Code Payment

### From POS JavaScript:

```javascript
// Show QR for payment
async function showQRPayment(qrData, amount) {
    await fetch('http://127.0.0.1:5000/api/customer-display/qr', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            qr_data: qrData,          // QRIS string or payment URL
            amount: amount,            // Total amount
            payment_method: 'QRIS'
        })
    });
}

// Hide QR after payment
async function hideQRPayment() {
    await fetch('http://127.0.0.1:5000/api/customer-display/hide-qr', {
        method: 'POST'
    });
}
```

**Features**:
- ✅ Full-screen modal overlay
- ✅ QR code (300x300px)
- ✅ Amount display
- ✅ 5-minute countdown timer
- ✅ Auto-hide on timeout

---

## 🖨️ Receipt Printing

Receipt prints to Windows default printer automatically when calling:

```javascript
sendReceiptToLocalPrinter(billId);
```

**Flow**:
1. Fetches bill data from Edge Server: `/pos/bill/{id}/data/`
2. Formats receipt with bill details
3. Sends to local printer via Flask API
4. Returns success/error

---

## 🧪 Testing

### Test Everything:
```powershell
cd pos_launcher_qt
python test_customer_display.py
```

**What it tests**:
1. ✅ Update customer display with sample items
2. ✅ Generate and show QR code
3. ✅ Hide QR code after 10 seconds

### Test Individual Features:

```powershell
# Test customer display only
Invoke-RestMethod -Method POST -Uri http://127.0.0.1:5000/api/customer-display/update `
  -Body '{"total":50000,"items":[{"name":"Test Item","quantity":1,"price":50000}]}' `
  -ContentType "application/json"

# Test QR display
Invoke-RestMethod -Method POST -Uri http://127.0.0.1:5000/api/customer-display/qr `
  -Body '{"qr_data":"TEST:PAYMENT:50000","amount":50000}' `
  -ContentType "application/json"

# Test health check
Invoke-RestMethod -Uri http://127.0.0.1:5000/health
```

---

## 🔌 API Reference

### Customer Display Endpoints

| Endpoint | Method | Purpose | Params |
|----------|--------|---------|--------|
| `/` | GET | Serve customer display HTML | - |
| `/health` | GET | Health check | - |
| `/api/customer-display/config` | GET | Get configuration | - |
| `/api/customer-display/stream` | GET | SSE real-time updates | - |
| `/api/customer-display/update` | POST | Update billing data | `{total, items, customer_name}` |
| `/api/customer-display/qr` | POST | Show QR code | `{qr_data, amount, payment_method}` |
| `/api/customer-display/hide-qr` | POST | Hide QR code | - |
| `/api/print` | POST | Print receipt | `{bill_id}` |

---

## ⚙️ Configuration Options

### Change Edge Server URL

Edit `pos_launcher_qt.py`:
```python
self.pos_url = "http://YOUR_SERVER_IP:8000/pos/?kiosk=1"
```

### Change Local API Port

Edit `local_api.py` (bottom):
```python
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)  # Change port here
```

And update in:
- `pos_launcher_qt.py` → `CustomerDisplayWindow` URL
- `customer_display.html` → `API_URL`
- `templates/pos/main.html` → JavaScript API calls

### Adjust Display Layout

Edit `customer_display.html` CSS:
```css
.main-content {
    grid-template-columns: 45% 55%;  /* Adjust as needed */
}
```

---

## 🐛 Troubleshooting

### Issue: Customer Display shows "Not Found"
**Solution**:
1. Check Flask is running: `Invoke-RestMethod http://127.0.0.1:5000/health`
2. Restart: Kill Python processes, start `pos_launcher_qt.py` again
3. Check firewall allows port 5000

### Issue: QR Code not showing
**Solution**:
1. Verify library: `pip install qrcode[pil]`
2. Check console for errors (F12 in customer display)
3. Verify API response: `Invoke-RestMethod -Method POST -Uri http://127.0.0.1:5000/api/customer-display/qr -Body '{"qr_data":"test"}' -ContentType "application/json"`

### Issue: Print not working
**Solution**:
1. Check Windows default printer is set
2. Verify `pywin32` installed: `pip install pywin32`
3. Test printer access: `win32print.GetDefaultPrinter()` in Python

### Issue: SSE connection failed
**Solution**:
1. Verify Flask server running
2. Check browser console (F12)
3. Test manually: Open `http://127.0.0.1:5000/api/customer-display/stream` in browser
4. Check antivirus/firewall not blocking

### Issue: POS web not loading
**Solution**:
1. Verify Edge Server is running
2. Check URL in `pos_launcher_qt.py`
3. Test URL in regular browser first
4. Check network connection to Edge Server

---

## 📦 Dependencies

All installed:
- ✅ PyQt6 6.10.2
- ✅ PyQt6-WebEngine 6.10.0  
- ✅ Flask 3.0.0
- ✅ flask-cors 4.0.0
- ✅ qrcode[pil] 8.2
- ✅ pywin32
- ✅ requests

---

## 🎯 Key Features Summary

| Feature | Status | Description |
|---------|--------|-------------|
| **Dual Display** | ✅ | Main POS + Customer Display |
| **Real-Time Updates** | ✅ | SSE streaming, no polling |
| **QR Payment** | ✅ | Full-screen modal with timer |
| **Local Printing** | ✅ | Receipt to Windows printer |
| **Custom Branding** | ✅ | Logo, colors, slides via JSON |
| **Event-Based** | ✅ | Cart change → instant update |
| **No Dependencies** | ✅ | Embedded Chromium (PyQt6) |
| **Cross-Platform** | ✅ | Windows ready, Linux compatible |

---

## 🎉 You're All Set!

Start your POS system now:

```powershell
cd pos_launcher_qt
python pos_launcher_qt.py
```

**What happens**:
1. Flask API starts on port 5000
2. Main POS window opens (Edge Server)
3. Customer display opens (local Flask)
4. System ready for orders!

**Next Steps**:
1. Customize `customer_display_config.json` with your branding
2. Test with `test_customer_display.py`
3. Verify printer works
4. Start taking orders! 🚀

---

**Questions or Issues?**
- Check logs in terminal windows
- Test endpoints individually
- Review troubleshooting section above
- All code is in `pos_launcher_qt/` folder
