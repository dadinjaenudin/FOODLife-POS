# 🔧 Troubleshooting & FAQ

## 📋 Daftar Isi

1. [Masalah Startup](#masalah-startup)
2. [Masalah Koneksi](#masalah-koneksi)
3. [Masalah Sinkronisasi](#masalah-sinkronisasi)
4. [Masalah Terminal](#masalah-terminal)
5. [Masalah Performance](#masalah-performance)
6. [FAQ](#faq)

---

## 🚀 Masalah Startup

### ❌ Error: "ModuleNotFoundError: No module named 'PyQt6'"

**Penyebab:** PyQt6 belum terinstall atau virtual environment tidak aktif

**Solusi:**
```powershell
# Di folder pos_launcher_qt
python -m pip install -r requirements.txt

# Atau install manual
python -m pip install PyQt6==6.10.2 PyQt6-WebEngine==6.10.2
```

**Verifikasi:**
```powershell
python -c "import PyQt6; print(PyQt6.__version__)"
# Expected output: 6.10.2
```

---

### ❌ Error: "Address already in use: 127.0.0.1:5000"

**Penyebab:** Flask API sudah running di background atau port conflict

**Solusi:**
```powershell
# Kill semua process Python
taskkill /F /IM python.exe

# Tunggu 2 detik
Start-Sleep -Seconds 2

# Jalankan lagi
cd D:\YOGYA-FOODLIFE\FoodLife-POS\pos_launcher_qt
python pos_launcher_qt.py
```

**Atau cari process spesifik:**
```powershell
# Cek port 5000
netstat -ano | findstr :5000

# Kill by PID
taskkill /F /PID <PID_NUMBER>
```

---

### ❌ Window customer display tidak muncul

**Penyebab:** Multi-monitor tidak terdeteksi atau config salah

**Debug:**
```python
# Tambahkan di pos_launcher_qt.py setelah line 250
screens = QApplication.screens()
print(f"[DEBUG] Available screens: {len(screens)}")
for i, screen in enumerate(screens):
    print(f"  Screen {i}: {screen.geometry()}")
```

**Solusi:**
1. **Single monitor mode** (untuk testing):
   ```python
   # pos_launcher_qt.py line 260
   # Ubah dari:
   customer_screen = screens[1] if len(screens) > 1 else screens[0]
   
   # Jadi:
   customer_screen = screens[0]  # Same monitor
   self.customer_window.move(1400, 0)  # Geser ke kanan
   ```

2. **Extend display di Windows:**
   - Windows + P
   - Pilih "Extend"
   - Arrange monitors di Settings

---

### ❌ White screen / blank di kedua monitor

**Penyebab:** Django server belum jalan atau URL salah

**Debug:**
```powershell
# Test Django server
curl http://localhost:8001/pos/

# Expected: HTML response atau redirect to login
```

**Solusi:**
```powershell
# Start Docker containers
cd D:\YOGYA-FOODLIFE\FoodLife-POS
docker-compose up -d

# Wait for ready
Start-Sleep -Seconds 10

# Check logs
docker logs fnb_edge_web --tail 20

# Should see: "Listening on TCP address 0.0.0.0:8000"
```

---

## 🌐 Masalah Koneksi

### ❌ Customer display tidak update saat add item

**Penyebab:** SSE connection tidak terbentuk

**Debug checklist:**
```markdown
1. ✅ Flask API running?
   curl http://localhost:5000/
   
2. ✅ SSE endpoint accessible?
   curl http://localhost:5000/api/customer-display/stream
   (should hang/keep connection open)
   
3. ✅ Browser console errors?
   F12 → Console → Filter "SSE"
   Should see: "[SSE] Connected successfully"
   
4. ✅ Network tab shows stream?
   F12 → Network → Filter "stream"
   Should see: stream (pending...) with Type: text/event-stream
```

**Solusi:**

1. **Restart Flask** (via launcher restart):
   ```powershell
   taskkill /F /IM python.exe
   cd pos_launcher_qt
   python pos_launcher_qt.py
   ```

2. **Check CORS:**
   ```python
   # local_api.py - pastikan ada:
   from flask_cors import CORS
   CORS(app)  # Enable CORS for all routes
   ```

3. **Firewall blocking:**
   ```powershell
   # Allow Python through firewall
   New-NetFirewallRule -DisplayName "Python Flask" -Direction Inbound -Program "C:\Python314\python.exe" -Action Allow
   ```

---

### ❌ Error: "Failed to load resource: net::ERR_CONNECTION_REFUSED"

**Penyebab:** Flask API tidak jalan atau customer display salah URL

**Debug:**
```javascript
// customer_display.html - Check API_BASE
const API_BASE = 'http://localhost:5000';  // ✅ Correct
// NOT: http://127.0.0.1:5000  // ❌ Might cause issues
```

**Solusi:**
```powershell
# Test Flask dari customer display window
# Buka F12 Console, run:
fetch('http://localhost:5000/').then(r => r.json()).then(console.log)

# Expected: {status: "ok", message: "..."}
```

---

### ❌ SSE keeps reconnecting every 3 seconds

**Penyebab:** Connection dropping, possible cause:
- Flask error in stream generator
- Network instability
- Browser memory limit

**Debug:**
```python
# local_api.py - Add debug logging
@app.route('/api/customer-display/stream')
def stream():
    def generate():
        client_id = id(request.environ)
        print(f"[SSE] Client {client_id} connected")
        
        try:
            # ... generator code ...
            
        except Exception as e:
            print(f"[SSE ERROR] Client {client_id}: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    return Response(generate(), mimetype='text/event-stream')
```

**Solusi:**
1. Check Flask logs for errors
2. Increase browser memory limit (close other tabs)
3. Reduce SSE frequency (increase sleep time)

---

## 🔄 Masalah Sinkronisasi

### ❌ Bill panel updated di kasir, tapi customer tidak

**Penyebab:** Django tidak memanggil Flask API

**Debug:**
```python
# apps/pos/views.py - Add logging
def sync_bill_to_customer_display(bill):
    logger.info(f"[SYNC] Syncing bill {bill.bill_number}")
    
    try:
        response = requests.post(
            'http://localhost:5000/api/customer-display/update-bill',
            json=data,
            timeout=1
        )
        logger.info(f"[SYNC] Flask response: {response.status_code}")
        
    except Exception as e:
        logger.error(f"[SYNC ERROR] {e}")
```

**Check Django logs:**
```powershell
docker logs fnb_edge_web --tail 50 -f

# Saat add item, should see:
# [SYNC] Syncing bill INV-2026-0001
# [SYNC] Flask response: 200
```

**Solusi:**
```python
# Pastikan sync dipanggil di semua tempat yang mengubah bill:
# - add_item_view
# - remove_item_view
# - update_quantity_view
# - update_discount_view
# etc.
```

---

### ❌ Payment modal muncul di kasir tapi tidak di customer

**Penyebab:** Modal sync script tidak berjalan

**Debug:**
```html
<!-- payment_modal.html - Add debug log -->
<script>
function syncModalToCustomerDisplay(modalElement) {
    console.log('[Modal Sync] Starting sync');
    console.log('[Modal Sync] Modal type:', modalElement.dataset.modalType);
    
    // ... existing code ...
    
    fetch('http://localhost:5000/api/customer-display/show-modal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    }).then(response => {
        console.log('[Modal Sync] Response:', response.status);
        return response.json();
    }).then(result => {
        console.log('[Modal Sync] Result:', result);
    }).catch(error => {
        console.error('[Modal Sync] ERROR:', error);
    });
}
</script>
```

**Solusi:**
1. Check browser console for errors
2. Verify `data-sync-to-customer="true"` attribute
3. Check Flask logs for POST /show-modal

---

### ❌ Customer display shows old data

**Penyebab:** Browser caching atau tidak auto-refresh

**Solusi:**

1. **Hard refresh customer display:**
   ```powershell
   # Add to pos_launcher_qt.py startup
   self.customer_page.load(QUrl(customer_url))
   
   # Force reload
   self.customer_page.reload()
   ```

2. **Disable caching:**
   ```python
   # pos_launcher_qt.py - After creating profile
   self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.NoCache)
   ```

3. **Add cache busting:**
   ```html
   <!-- customer_display.html -->
   <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
   <meta http-equiv="Pragma" content="no-cache">
   <meta http-equiv="Expires" content="0">
   ```

---

## 🖥️ Masalah Terminal

### ❌ Login ke-2 minta setup terminal lagi

**Penyebab:** `launcher_terminal_code` hilang dari session saat logout

**Verifikasi masalah:**
```powershell
# Check Django logs after logout → login
docker logs fnb_edge_web --tail 30

# Should see:
# [Terminal Detection] terminal_code=None, launcher_terminal_code=BOE-001
# Using launcher terminal code: BOE-001

# If see:
# [Terminal Detection] terminal_code=None, launcher_terminal_code=None
# ❌ Bug! launcher_terminal_code not preserved
```

**Solusi sudah diimplementasi:**
```python
# apps/core/views.py - logout_view
def logout_view(request):
    # ✅ Backup
    launcher_terminal = request.session.get('launcher_terminal_code')
    
    auth_logout(request)
    request.session.flush()
    
    # ✅ Restore
    if launcher_terminal:
        request.session['launcher_terminal_code'] = launcher_terminal
        request.session.save()
    
    return redirect('core:login')
```

**Jika masih terjadi:**
1. Restart Django container
2. Clear session table:
   ```sql
   docker exec -it fnb_edge_postgres psql -U fnb_user -d fnb_pos_edge
   DELETE FROM django_session;
   ```

---

### ❌ Terminal tidak terdeteksi pada startup

**Penyebab:** URL parameter `terminal` tidak dikirim atau salah

**Debug:**
```python
# pos_launcher_qt.py - Check URL construction
print(f"[DEBUG] Main URL: {main_url}")
# Should be: http://localhost:8001/pos/?terminal=BOE-001&token=...&kiosk=1
```

**Solusi:**
```python
# pos_launcher_qt.py - Verify config.json
with open('config.json', 'r') as f:
    config = json.load(f)
    print(f"[DEBUG] Terminal code: {config.get('terminal_code')}")
    # Should print: BOE-001 (or your terminal code)
```

---

### ❌ Error: "Terminal not found: BOE-001"

**Penyebab:** Terminal belum dibuat di database

**Solusi:**
```python
# Via Django shell
docker exec -it fnb_edge_web python manage.py shell

# Create terminal
from apps.pos.models import POSTerminal
from apps.core.models import Store
import uuid

store = Store.objects.first()  # Get your store

terminal = POSTerminal.objects.create(
    terminal_code='BOE-001',
    terminal_name='Kasir 1',
    store=store,
    is_active=True,
    session_token=uuid.uuid4()
)

print(f"Terminal created: {terminal.terminal_code}")
```

---

## ⚡ Masalah Performance

### ❌ Customer display lag / slow update

**Penyebab:** Too frequent updates atau large data

**Diagnosis:**
```javascript
// customer_display.html - Measure update time
let updateCount = 0;
let totalTime = 0;

eventSource.addEventListener('bill-update', (event) => {
    const start = performance.now();
    
    updateBillDisplay(JSON.parse(event.data));
    
    const duration = performance.now() - start;
    updateCount++;
    totalTime += duration;
    
    console.log(`[PERF] Update #${updateCount}: ${duration.toFixed(2)}ms`);
    console.log(`[PERF] Average: ${(totalTime / updateCount).toFixed(2)}ms`);
});
```

**Solusi:**

1. **Add debouncing:**
   ```python
   # apps/pos/views.py
   from django.core.cache import cache
   
   def sync_bill_to_customer_display(bill):
       cache_key = f'last_sync_{bill.id}'
       last_sync = cache.get(cache_key)
       
       if last_sync:
           elapsed = time.time() - last_sync
           if elapsed < 0.5:  # Less than 500ms
               return  # Skip sync
       
       # Proceed with sync
       # ...
       
       cache.set(cache_key, time.time(), timeout=5)
   ```

2. **Reduce HTMX polling:**
   ```html
   <!-- main.html -->
   <!-- Change from: hx-trigger="every 2s" -->
   <div hx-trigger="every 5s">
   ```

3. **Optimize DOM updates:**
   ```javascript
   // Use DocumentFragment for batch updates
   function updateBillDisplay(data) {
       const fragment = document.createDocumentFragment();
       
       data.items.forEach(item => {
           const div = document.createElement('div');
           div.className = 'bill-item';
           div.innerHTML = `...`;
           fragment.appendChild(div);
       });
       
       // Single DOM update
       itemsList.innerHTML = '';
       itemsList.appendChild(fragment);
   }
   ```

---

### ❌ Memory leak - RAM usage terus naik

**Penyebab:** SSE connections tidak di-cleanup atau event listeners bertumpuk

**Diagnosis:**
```javascript
// customer_display.html - Monitor connections
setInterval(() => {
    console.log('[MEMORY] eventSource state:', eventSource.readyState);
    console.log('[MEMORY] DOM nodes:', document.body.getElementsByTagName('*').length);
}, 30000);  // Every 30 seconds
```

**Solusi:**

1. **Proper SSE cleanup:**
   ```javascript
   function connectSSE() {
       // Close old connection first
       if (eventSource) {
           eventSource.close();
           eventSource = null;
       }
       
       eventSource = new EventSource(`${API_BASE}/api/customer-display/stream`);
       // ... event handlers ...
   }
   
   // Cleanup on page unload
   window.addEventListener('beforeunload', () => {
       if (eventSource) {
           eventSource.close();
       }
   });
   ```

2. **Flask connection cleanup:**
   ```python
   # local_api.py
   @app.route('/api/customer-display/stream')
   def stream():
       def generate():
           try:
               # ... generator code ...
           except GeneratorExit:
               # Clean up
               with sse_lock:
                   if request.environ in sse_clients:
                       sse_clients.remove(request.environ)
               raise  # Re-raise to properly close
       
       return Response(generate(), mimetype='text/event-stream')
   ```

---

## ❓ FAQ

### Q: Berapa kapasitas maksimal customer yang bisa handle?

**A:** Single POS Launcher = 1 kasir + 1 customer display. Untuk multiple kasir:
- Jalankan multiple POS Launcher instance
- Setiap instance dengan terminal_code berbeda
- Setiap instance dengan port Flask berbeda (5000, 5001, 5002, dst)

```json
// config.json untuk terminal 2
{
    "terminal_code": "BOE-002",
    "flask_port": 5001
}
```

---

### Q: Bisa pakai Raspberry Pi untuk customer display?

**A:** Bisa! Setup:

1. **Kasir terminal:** PC Windows dengan POS Launcher
2. **Customer display:** Raspberry Pi dengan browser

```bash
# Di Raspberry Pi
chromium-browser --kiosk --app=http://<KASIR_IP>:5000/customer_display.html
```

Network requirements:
- Same LAN
- Flask API bind ke 0.0.0.0 (bukan 127.0.0.1)

```python
# local_api.py
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

---

### Q: Apakah data customer display tersimpan di database?

**A:** Tidak. Data di Flask API adalah **in-memory only** (temporary).

Keuntungan:
- ✅ Very fast (no DB query)
- ✅ No storage overhead
- ✅ Auto-cleanup on restart

Kekurangan:
- ❌ Data hilang saat Flask restart (but not a problem karena immediate sync from Django)

Database hanya di Django (persistent data).

---

### Q: Bagaimana cara ganti bahasa di customer display?

**A:** Edit `customer_display_config.json`:

```json
{
    "language": "id",  // "id" = Indonesian, "en" = English
    "currency": "IDR",
    "currency_symbol": "Rp"
}
```

Atau hardcode di HTML:
```html
<!-- customer_display.html -->
<script>
const translations = {
    id: {
        your_order: 'Pesanan Anda',
        total: 'Total',
        subtotal: 'Subtotal',
        tax: 'Pajak'
    },
    en: {
        your_order: 'Your Order',
        total: 'Total',
        subtotal: 'Subtotal',
        tax: 'Tax'
    }
};

const lang = config.language || 'id';
const t = translations[lang];

// Use: t.your_order, t.total, etc.
</script>
```

---

### Q: Bisa pakai touchscreen di customer display?

**A:** Bisa, tapi **tidak recommended** untuk mode read-only.

Customer display didesain **view-only**. Jika perlu interaksi customer:
- Gunakan QR Order system (separate module)
- Atau implementasikan "Customer Confirm" button

---

### Q: Kenapa pakai Flask? Kenapa tidak langsung Django?

**A:** Alasan teknis:

1. **Separation of Concerns**
   - Django = Business logic + Database
   - Flask = Real-time communication only

2. **Lightweight Real-time**
   - Flask lebih ringan untuk SSE
   - Django ASGI (Daphne) lebih berat

3. **Scalability**
   - Flask bisa dijalankan di server terpisah
   - Tidak membebani Django main server

4. **Development Speed**
   - Flask aturan lebih flexible
   - Cepat prototype fitur baru

---

### Q: Apakah sistem ini bisa offline?

**A:** Partial offline:

✅ **Bisa offline:**
- POS Launcher + Django (localhost)
- Customer display (local HTML)
- Flask API (localhost)
- Database (Docker local)

❌ **Tidak bisa offline:**
- Sync to Head Office (requires internet)
- Payment gateway (QRIS, card)
- Tailwind CDN (replace dengan local build)

---

### Q: Bagaimana cara backup data?

**A:**
```powershell
# Database backup
docker exec fnb_edge_postgres pg_dump -U fnb_user fnb_pos_edge > backup.sql

# Restore
docker exec -i fnb_edge_postgres psql -U fnb_user fnb_pos_edge < backup.sql

# Media files backup
docker cp fnb_edge_web:/app/media ./media_backup

# Configuration backup
Copy-Item pos_launcher_qt\config.json -Destination config_backup.json
```

---

### Q: Berapa lama development waktu ini?

**A:** Timeline:
- **Phase 1** (Dual Display Basic): 2 hari
- **Phase 2** (Payment Modal v2.1): 1 hari
- **Phase 3** (Cache fixes, blank screen): 1 hari
- **Phase 4** (Terminal persistence bug): 1 hari
- **Phase 5** (Documentation): 1 hari

**Total**: ~6 hari development

---

## 📞 Getting Help

### Log Files Location
```
Django logs:     docker logs fnb_edge_web
Flask logs:      Terminal output (pos_launcher_qt stdout)
Customer logs:   Browser F12 Console
Database logs:   docker logs fnb_edge_postgres
```

### Debug Mode
```python
# Enable debug mode (DEVELOPMENT ONLY!)

# Django - .env.edge
DEBUG=True

# Flask - local_api.py
app.run(debug=True, port=5000)

# PyQt - pos_launcher_qt.py
os.environ['QTWEBENGINE_REMOTE_DEBUGGING'] = '9222'
# Then access: http://localhost:9222
```

### Community Support
- GitHub Issues: https://github.com/dadinjaenudin/FOODLife-POS/issues
- Documentation: pos_launcher_qt/docs/

---

**Dibuat**: 2026-02-07  
**Versi**: 1.0  
**Status**: ✅ Production Ready
