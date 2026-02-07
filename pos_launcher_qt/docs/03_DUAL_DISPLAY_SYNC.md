# 🔄 Dual Display Synchronization - Deep Dive

## 📋 Daftar Isi

1. [Konsep Sinkronisasi](#konsep-sinkronisasi)
2. [Server-Sent Events (SSE) Explained](#server-sent-events-explained)
3. [Bill Panel Sync Flow](#bill-panel-sync-flow)
4. [Payment Modal Sync Flow](#payment-modal-sync-flow)
5. [Error Handling & Recovery](#error-handling--recovery)
6. [Performance Optimization](#performance-optimization)
7. [Testing & Debugging](#testing--debugging)

---

## 🎯 Konsep Sinkronisasi

### Apa yang Disinkronkan?

```
Monitor Kasir                    Monitor Pelanggan
┌─────────────────────┐         ┌─────────────────────┐
│                     │         │                     │
│  ✅ Bill Panel      │────────▶│  ✅ Bill Panel      │
│  ✅ Payment Modal   │────────▶│  ✅ Payment Modal   │
│  ✅ Success Message │────────▶│  ✅ Success Message │
│                     │         │                     │
│  ❌ Settings        │  ╳╳╳╳╳▶│                     │
│  ❌ Admin Menu      │  ╳╳╳╳╳▶│                     │
│  ❌ Error Dialogs   │  ╳╳╳╳╳▶│                     │
└─────────────────────┘         └─────────────────────┘
```

### Tipe Sinkronisasi

| Konten | Metode | Frequency | Latency |
|--------|--------|-----------|---------|
| **Bill Items** | SSE Push | Real-time on change | <100ms |
| **Totals** | SSE Push | Real-time on change | <100ms |
| **Payment Modal** | SSE Push | On modal open | <50ms |
| **Success Screen** | SSE Push | On payment complete | <50ms |
| **Clear Display** | SSE Push | On new bill/logout | <50ms |
| **Slideshow** | Local Timer | Every 5 seconds | N/A |

---

## 📡 Server-Sent Events (SSE) Explained

### Apa itu SSE?

**Server-Sent Events** adalah teknologi HTML5 untuk **server push data ke client** melalui HTTP.

### Perbandingan dengan Alternatif

| Teknologi | Direction | Protocol | Complexity | Use Case |
|-----------|-----------|----------|------------|----------|
| **Polling** | Client → Server | HTTP | 😊 Simple | Low frequency updates |
| **Long Polling** | Client ⇄ Server | HTTP | 😐 Medium | Medium frequency |
| **SSE** ✅ | Server → Client | HTTP | 😊 Simple | **Real-time push** |
| **WebSocket** | Client ⇄ Server | WS:// | 😰 Complex | Bidirectional chat |

**Kenapa pilih SSE?**
- ✅ Built-in browser API (EventSource)
- ✅ Auto-reconnect otomatis
- ✅ Lightweight (hanya HTTP)
- ✅ Cocok untuk one-way push (server → client)
- ✅ No special server requirements
- ❌ Tidak cocok untuk client → server (tapi kita tidak perlu ini!)

### SSE Protocol Format

```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

event: bill-update
data: {"bill_id": "uuid", "items": [...], "total": 27750}

event: modal-show
data: {"modal_type": "payment", "html": "<div>...</div>"}

event: ping
data: {"timestamp": 1707312000}

```

**Format anatomy:**
- `event:` → Event type (untuk filtering di client)
- `data:` → JSON payload
- Blank line → Separator antar event

---

## 🔧 Implementation - Flask API (Server Side)

### File: `pos_launcher_qt/local_api.py`

#### Global State
```python
from flask import Flask, Response, request, jsonify
from flask_cors import CORS
import json
import time
from threading import Lock
from queue import Queue

app = Flask(__name__)
CORS(app)

# ========================================
# GLOBAL STATE (In-Memory)
# ========================================

# Current bill data
bills_data = {
    'bill_id': None,
    'bill_number': None,
    'items': [],
    'subtotal': 0,
    'tax': 0,
    'discount': 0,
    'total': 0,
    'updated_at': None
}

# Active modal
modal_data = {
    'visible': False,
    'modal_type': None,
    'html': None,
    'data': {}
}

# SSE clients registry
sse_clients = []
sse_lock = Lock()

# Event queue for broadcasting
event_queue = Queue()
```

#### SSE Stream Endpoint
```python
@app.route('/api/customer-display/stream')
def stream():
    """
    SSE endpoint for pushing real-time updates to customer display
    
    Flow:
    1. Client connects (EventSource in JavaScript)
    2. Add client to registry
    3. Keep connection alive
    4. Push events when data changes
    5. Remove client on disconnect
    """
    
    def generate():
        # Client connected
        client_id = id(request.environ)
        
        with sse_lock:
            sse_clients.append(request.environ)
        
        print(f"[SSE] Client connected: {client_id}")
        
        try:
            # Send initial data
            yield f"event: connected\ndata: {json.dumps({'status': 'ok'})}\n\n"
            
            # Send current bill data if exists
            if bills_data['bill_id']:
                yield f"event: bill-update\ndata: {json.dumps(bills_data)}\n\n"
            
            # Send current modal if visible
            if modal_data['visible']:
                yield f"event: modal-show\ndata: {json.dumps(modal_data)}\n\n"
            
            # Keep-alive loop
            last_ping = time.time()
            while True:
                # Check for new events in queue
                if not event_queue.empty():
                    event = event_queue.get()
                    yield f"event: {event['type']}\ndata: {json.dumps(event['data'])}\n\n"
                
                # Send periodic ping (every 30 seconds)
                now = time.time()
                if now - last_ping > 30:
                    yield f"event: ping\ndata: {json.dumps({'timestamp': now})}\n\n"
                    last_ping = now
                
                time.sleep(0.5)  # Small sleep to prevent CPU spike
                
        except GeneratorExit:
            # Client disconnected
            print(f"[SSE] Client disconnected: {client_id}")
            with sse_lock:
                if request.environ in sse_clients:
                    sse_clients.remove(request.environ)
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'  # Disable nginx buffering
        }
    )
```

#### Update Bill Data
```python
@app.route('/api/customer-display/update-bill', methods=['POST'])
def update_bill():
    """
    Called by Django when bill changes
    
    Request payload:
    {
        "bill_id": "uuid",
        "bill_number": "INV-2026-0001",
        "items": [
            {
                "id": "uuid",
                "name": "Nasi Goreng",
                "quantity": 1,
                "unit_price": 25000,
                "subtotal": 25000
            }
        ],
        "subtotal": 25000,
        "tax": 2750,
        "discount": 0,
        "total": 27750
    }
    """
    global bills_data
    
    data = request.json
    
    # Update global state
    bills_data = {
        'bill_id': data.get('bill_id'),
        'bill_number': data.get('bill_number'),
        'items': data.get('items', []),
        'subtotal': data.get('subtotal', 0),
        'tax': data.get('tax', 0),
        'discount': data.get('discount', 0),
        'total': data.get('total', 0),
        'updated_at': time.time()
    }
    
    # Broadcast to all SSE clients
    broadcast_event('bill-update', bills_data)
    
    print(f"[Bill Update] {data.get('bill_number')} - Total: {data.get('total')}")
    
    return jsonify({
        'status': 'success',
        'message': 'Bill updated',
        'clients': len(sse_clients)
    })


def broadcast_event(event_type, data):
    """Push event to all connected SSE clients"""
    event = {
        'type': event_type,
        'data': data
    }
    event_queue.put(event)
```

#### Show Modal
```python
@app.route('/api/customer-display/show-modal', methods=['POST'])
def show_modal():
    """
    Display modal on customer screen
    
    Request payload:
    {
        "modal_type": "payment",
        "html": "<div>...</div>",
        "data": {
            "total": 27750,
            "payment_method": "cash"
        }
    }
    """
    global modal_data
    
    data = request.json
    
    modal_data = {
        'visible': True,
        'modal_type': data.get('modal_type'),
        'html': data.get('html'),
        'data': data.get('data', {})
    }
    
    # Broadcast to SSE clients
    broadcast_event('modal-show', modal_data)
    
    print(f"[Modal Show] Type: {data.get('modal_type')}")
    
    return jsonify({'status': 'success'})


@app.route('/api/customer-display/hide-modal', methods=['POST'])
def hide_modal():
    """Hide modal on customer screen"""
    global modal_data
    
    modal_type = request.json.get('modal_type')
    
    modal_data = {
        'visible': False,
        'modal_type': None,
        'html': None,
        'data': {}
    }
    
    # Broadcast to SSE clients
    broadcast_event('modal-hide', {'modal_type': modal_type})
    
    print(f"[Modal Hide] Type: {modal_type}")
    
    return jsonify({'status': 'success'})
```

#### Clear Display
```python
@app.route('/api/customer-display/clear', methods=['POST'])
def clear_display():
    """
    Clear customer display (back to blank/slideshow)
    
    Called after:
    - Payment success
    - Bill void
    - User logout
    """
    global bills_data, modal_data
    
    # Reset state
    bills_data = {
        'bill_id': None,
        'bill_number': None,
        'items': [],
        'subtotal': 0,
        'tax': 0,
        'discount': 0,
        'total': 0,
        'updated_at': None
    }
    
    modal_data = {
        'visible': False,
        'modal_type': None,
        'html': None,
        'data': {}
    }
    
    # Broadcast to SSE clients
    broadcast_event('clear', {'reason': 'payment_success'})
    
    print("[Display Cleared]")
    
    return jsonify({'status': 'success'})
```

---

## 💻 Implementation - Customer Display (Client Side)

### File: `pos_launcher_qt/customer_display.html`

#### SSE Connection Setup
```html
<script>
const API_BASE = 'http://localhost:5000';
let eventSource = null;
let reconnectTimer = null;

function connectSSE() {
    // Close existing connection
    if (eventSource) {
        eventSource.close();
    }
    
    console.log('[SSE] Connecting to server...');
    
    // Create EventSource
    eventSource = new EventSource(`${API_BASE}/api/customer-display/stream`);
    
    // ========================================
    // EVENT HANDLERS
    // ========================================
    
    // Connection established
    eventSource.addEventListener('connected', (event) => {
        const data = JSON.parse(event.data);
        console.log('[SSE] Connected successfully', data);
        
        // Clear reconnect timer
        if (reconnectTimer) {
            clearTimeout(reconnectTimer);
            reconnectTimer = null;
        }
    });
    
    // Bill update
    eventSource.addEventListener('bill-update', (event) => {
        const data = JSON.parse(event.data);
        console.log('[SSE] Bill update received', data);
        
        updateBillDisplay(data);
    });
    
    // Modal show
    eventSource.addEventListener('modal-show', (event) => {
        const data = JSON.parse(event.data);
        console.log('[SSE] Modal show received', data);
        
        showModal(data);
    });
    
    // Modal hide
    eventSource.addEventListener('modal-hide', (event) => {
        const data = JSON.parse(event.data);
        console.log('[SSE] Modal hide received', data);
        
        hideModal(data.modal_type);
    });
    
    // Clear display
    eventSource.addEventListener('clear', (event) => {
        const data = JSON.parse(event.data);
        console.log('[SSE] Clear received', data);
        
        clearDisplay();
    });
    
    // Keep-alive ping
    eventSource.addEventListener('ping', (event) => {
        const data = JSON.parse(event.data);
        console.log('[SSE] Ping received', data.timestamp);
    });
    
    // ========================================
    // ERROR HANDLING
    // ========================================
    
    eventSource.onerror = (error) => {
        console.error('[SSE] Connection error', error);
        eventSource.close();
        
        // Auto-reconnect after 3 seconds
        console.log('[SSE] Reconnecting in 3 seconds...');
        reconnectTimer = setTimeout(connectSSE, 3000);
    };
}

// Auto-connect on page load
document.addEventListener('DOMContentLoaded', () => {
    connectSSE();
});
</script>
```

#### Bill Display Update
```html
<script>
function updateBillDisplay(data) {
    const billPanel = document.getElementById('bill-panel');
    const blankScreen = document.getElementById('blank-screen');
    
    if (!data.bill_id || data.items.length === 0) {
        // No bill - show blank screen
        billPanel.style.display = 'none';
        blankScreen.style.display = 'flex';
        return;
    }
    
    // Show bill panel
    billPanel.style.display = 'block';
    blankScreen.style.display = 'none';
    
    // Update bill number
    document.getElementById('bill-number').textContent = data.bill_number || '--';
    
    // Update items list
    const itemsList = document.getElementById('items-list');
    itemsList.innerHTML = '';
    
    data.items.forEach(item => {
        const itemRow = document.createElement('div');
        itemRow.className = 'bill-item';
        itemRow.innerHTML = `
            <div class="item-info">
                <div class="item-name">${item.name}</div>
                ${item.notes ? `<div class="item-notes">${item.notes}</div>` : ''}
            </div>
            <div class="item-quantity">×${item.quantity}</div>
            <div class="item-price">${formatCurrency(item.subtotal)}</div>
        `;
        itemsList.appendChild(itemRow);
    });
    
    // Update totals
    document.getElementById('subtotal').textContent = formatCurrency(data.subtotal);
    document.getElementById('tax').textContent = formatCurrency(data.tax);
    
    if (data.discount > 0) {
        document.getElementById('discount-row').style.display = 'flex';
        document.getElementById('discount').textContent = formatCurrency(data.discount);
    } else {
        document.getElementById('discount-row').style.display = 'none';
    }
    
    document.getElementById('total').textContent = formatCurrency(data.total);
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('id-ID', {
        style: 'currency',
        currency: 'IDR',
        minimumFractionDigits: 0
    }).format(amount);
}
</script>
```

#### Modal Display
```html
<script>
function showModal(data) {
    const modalContainer = document.getElementById('modal-container');
    
    // Inject HTML
    modalContainer.innerHTML = data.html;
    
    // Apply customer display mode
    Alpine.store('isCustomerDisplay', true);
    
    // Disable all inputs and buttons
    modalContainer.querySelectorAll('input, select, textarea').forEach(el => {
        el.disabled = true;
        el.readOnly = true;
    });
    
    modalContainer.querySelectorAll('button').forEach(el => {
        // Hide action buttons, keep close button visible
        if (!el.classList.contains('modal-close')) {
            el.style.display = 'none';
        }
    });
    
    // Show modal
    modalContainer.style.display = 'block';
    
    // Add customer-display class for styling
    modalContainer.classList.add('customer-display-mode');
}

function hideModal(modalType) {
    const modalContainer = document.getElementById('modal-container');
    
    // Fade out animation
    modalContainer.style.opacity = '0';
    
    setTimeout(() => {
        modalContainer.innerHTML = '';
        modalContainer.style.display = 'none';
        modalContainer.style.opacity = '1';
    }, 300);
}

function clearDisplay() {
    const billPanel = document.getElementById('bill-panel');
    const blankScreen = document.getElementById('blank-screen');
    const modalContainer = document.getElementById('modal-container');
    
    // Hide bill and modal
    billPanel.style.display = 'none';
    modalContainer.style.display = 'none';
    modalContainer.innerHTML = '';
    
    // Show blank screen / slideshow
    blankScreen.style.display = 'flex';
    
    // Start slideshow if configured
    if (config.slideshow_enabled) {
        startSlideshow();
    }
}
</script>
```

---

## 🔄 Bill Panel Sync Flow

### Complete Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                           KASIR ACTION                                │
│                    (Click "Add Nasi Goreng")                         │
└────────────────────────────┬──────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      DJANGO VIEW PROCESSING                           │
│                                                                       │
│  1. Validate product exists                                          │
│  2. Get/Create active bill                                           │
│  3. Add BillItem:                                                    │
│     - product = Nasi Goreng                                          │
│     - quantity = 1                                                   │
│     - unit_price = 25000                                             │
│     - subtotal = 25000                                               │
│  4. Save to database ✅                                              │
│  5. Calculate totals:                                                │
│     - subtotal = Σ(items.subtotal)                                   │
│     - tax = subtotal * 0.11                                          │
│     - total = subtotal + tax - discount                              │
│  6. Update Bill model ✅                                             │
│  7. Render bill_panel.html (for HTMX)                                │
│  8. Call sync_bill_to_customer_display(bill) ⚡                      │
└────────────────────┬────────────────────────┬─────────────────────────┘
                     │                        │
                     │ HTMX swap              │ HTTP POST
                     │                        │
         ┌───────────▼──────────┐  ┌─────────▼─────────────────────────┐
         │  Monitor Kasir       │  │  Flask API                         │
         │  #bill-panel updated │  │  /api/customer-display/update-bill│
         │                      │  │                                    │
         │  ┌────────────────┐ │  │  1. Receive bill data JSON        │
         │  │ Nasi Goreng    │ │  │  2. Update bills_data (global)    │
         │  │ × 1     25.000 │ │  │  3. broadcast_event('bill-update')│
         │  ├────────────────┤ │  │  4. Put event in queue            │
         │  │ Total:  27.750 │ │  └─────────────┬──────────────────────┘
         │  └────────────────┘ │                │
         └─────────────────────┘                │ SSE emit
                                                 │
                                      ┌──────────▼──────────────────┐
                                      │  Customer Display           │
                                      │  EventSource.onmessage      │
                                      │                             │
                                      │  1. Parse event data        │
                                      │  2. updateBillDisplay()     │
                                      │  3. Render HTML:            │
                                      │                             │
                                      │  ┌──────────────────────┐  │
                                      │  │ 🛒 Pesanan Anda     │  │
                                      │  ├──────────────────────┤  │
                                      │  │ Nasi Goreng   25.000│  │
                                      │  │ ─────────────────────│  │
                                      │  │ Total:        27.750│  │
                                      │  └──────────────────────┘  │
                                      └──────────────────────────────┘
```

### Timing Sequence

```
Time    Kasir Monitor          Django Server         Flask API          Customer Display
─────   ─────────────          ─────────────         ─────────         ────────────────
0ms     [Click Add Item]
        │
20ms    │ POST /pos/add-item/  ─▶
        │                      │
30ms    │                      [Process]
        │                      │ DB write
50ms    │                      │ Render HTML
        │                      │ POST Flask ───────▶
60ms    │                      │                   [Store data]
        │                      │                   [Queue event]
70ms    │ ◀─ HTMX response     │                   │
        │ [DOM updated]        │                   │ SSE emit ───────▶
80ms    │                      │                   │                   [Receive event]
        │                      │                   │                   [Parse JSON]
90ms    │                      │                   │                   [Render UI]
        │                      │                   │                   ✅ UPDATED
        
Total latency: ~90ms (from click to customer display update)
```

---

## 💳 Payment Modal Sync Flow

### Complete Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                           KASIR ACTION                                │
│                         (Click "Bayar")                              │
└────────────────────────────┬──────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      DJANGO TEMPLATE RENDER                           │
│                                                                       │
│  1. Load payment_modal.html                                          │
│  2. Pass context:                                                    │
│     - bill (with totals)                                             │
│     - PAYMENT_CONFIG                                                 │
│  3. Render HTML with data-sync-to-customer="true"                   │
│  4. Alpine.js initialize modal                                       │
└────────────────────┬──────────────────────┬─────────────────────────┘
                     │                      │
                     │ Show modal           │
                     │                      │
         ┌───────────▼──────────┐          │
         │  Monitor Kasir       │          │
         │  Modal visible       │          │
         │                      │          │
         │  JavaScript detects: │          │
         │  - data-sync="true"  │          │
         │  ↓                   │          │
         │  Extract:            │          │
         │  - modal HTML        │          │
         │  - modal data        │          │
         │  ↓                   │          │
         │  POST to Flask ──────┼──────────┼─────────────────────▶
         └──────────────────────┘          │                      │
                                            │               ┌──────▼──────────┐
                                            │               │  Flask API      │
                                            │               │  /show-modal    │
                                            │               │                 │
                                            │               │  1. Store HTML  │
                                            │               │  2. Queue event │
                                            │               │  3. SSE emit ─┐ │
                                            │               └────────────────┼─┘
                                            │                                │
                                            │                     ┌──────────▼─────────┐
                                            │                     │  Customer Display  │
                                            │                     │  EventSource       │
                                            │                     │                    │
                                            │                     │  1. Receive event  │
                                            │                     │  2. showModal()    │
                                            │                     │  3. Inject HTML    │
                                            │                     │  4. Disable inputs │
                                            │                     │  5. Hide buttons   │
                                            │                     │                    │
                                            │                     │  [Modal rendered]  │
                                            │                     │  Customer can see  │
                                            │                     │  ✅ Read-only mode │
                                            │                     └────────────────────┘
                                            │
                                            │ (Kasir selects payment method,
                                            │  inputs amount, sees change calculation)
                                            │
                                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      KASIR CONFIRM PAYMENT                            │
│                   (Click "Confirm Payment")                          │
└────────────────────────────┬──────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      DJANGO PAYMENT PROCESSING                        │
│                                                                       │
│  1. Validate payment data                                            │
│  2. Create Payment record                                            │
│  3. Update Bill status = 'paid'                                      │
│  4. Generate receipt                                                 │
│  5. Render payment_success.html                                      │
│  6. Call Flask /hide-modal ──────────────────────────────────┐       │
│  7. Call Flask /clear ───────────────────────────────────────┼─┐     │
└──────────────────────────────────────────────────────────────┼─┼─────┘
                                                               │ │
                                                               │ │
                                          ┌────────────────────▼─▼────┐
                                          │  Flask API                │
                                          │  1. /hide-modal           │
                                          │     → emit modal-hide─┐   │
                                          │  2. /clear                │
                                          │     → emit clear ───────┼─┐
                                          └─────────────────────────┼─┼┘
                                                                    │ │
                                       ┌────────────────────────────▼─▼──┐
                                       │  Customer Display                │
                                       │  1. Hide modal (fade out)        │
                                       │  2. Clear bill panel            │
                                       │  3. Show blank screen/slideshow │
                                       │  ✅ Ready for next customer     │
                                       └──────────────────────────────────┘
```

### Modal Clone Implementation

**Di payment_modal.html:**
```html
<!-- data-sync attribute tells JS to clone this -->
<div id="paymentModal"
     x-data="paymentModalData()"
     x-show="$store.modal.payment"
     data-sync-to-customer="true"
     data-customer-readonly="true"
     data-modal-type="payment"
     data-bill-id="{{ bill.id }}"
     data-bill-total="{{ bill.total }}">
     
    <!-- Modal content -->
</div>

<script>
// Auto-sync on modal show
Alpine.directive('show', (el, { expression }, { effect, evaluateLater }) => {
    let evaluate = evaluateLater(expression);
    
    effect(() => {
        evaluate(value => {
            if (value && el.dataset.syncToCustomer === 'true') {
                // Modal just became visible, sync it!
                syncModalToCustomerDisplay(el);
            }
        });
    });
});

function syncModalToCustomerDisplay(modalElement) {
    // Clone the element
    const clone = modalElement.cloneNode(true);
    
    // Extract data
    const data = {
        modal_type: modalElement.dataset.modalType,
        html: clone.outerHTML,
        data: {
            bill_id: modalElement.dataset.billId,
            total: parseFloat(modalElement.dataset.billTotal),
            readonly: modalElement.dataset.customerReadonly === 'true'
        }
    };
    
    // Send to Flask
    fetch('http://localhost:5000/api/customer-display/show-modal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    }).then(response => {
        if (response.ok) {
            console.log('[Modal Sync] Success');
        } else {
            console.error('[Modal Sync] Failed');
        }
    }).catch(error => {
        console.error('[Modal Sync] Error:', error);
    });
}
</script>
```

---

## 🛡️ Error Handling & Recovery

### Connection Loss Scenarios

#### 1. Flask API Down

```javascript
// customer_display.html
eventSource.onerror = (error) => {
    console.error('[SSE] Connection failed');
    
    // Show connection lost indicator
    showConnectionError();
    
    // Auto-reconnect
    setTimeout(connectSSE, 3000);
};

function showConnectionError() {
    const errorBanner = document.createElement('div');
    errorBanner.id = 'connection-error';
    errorBanner.className = 'error-banner';
    errorBanner.innerHTML = `
        <span>⚠️ Connection lost. Reconnecting...</span>
    `;
    document.body.appendChild(errorBanner);
}

// Remove error when reconnected
eventSource.addEventListener('connected', () => {
    const errorBanner = document.getElementById('connection-error');
    if (errorBanner) {
        errorBanner.remove();
    }
});
```

#### 2. Network Timeout

```python
# Django views.py
def sync_bill_to_customer_display(bill):
    """Send bill to Flask with timeout"""
    try:
        response = requests.post(
            'http://localhost:5000/api/customer-display/update-bill',
            json=bill_data,
            timeout=1  # Max 1 second wait
        )
        
        if response.status_code != 200:
            logger.warning(f"Flask API returned {response.status_code}")
        
    except requests.exceptions.Timeout:
        logger.warning("Flask API timeout - customer display may not update")
        # Don't fail the main transaction!
        
    except requests.exceptions.ConnectionError:
        logger.error("Flask API not available")
        # Continue without customer display
```

#### 3. Data Corruption

```javascript
// customer_display.html
eventSource.addEventListener('bill-update', (event) => {
    try {
        const data = JSON.parse(event.data);
        
        // Validate data structure
        if (!data.bill_id || !Array.isArray(data.items)) {
            throw new Error('Invalid bill data structure');
        }
        
        // Validate numbers
        if (isNaN(data.total) || data.total < 0) {
            throw new Error('Invalid total amount');
        }
        
        // All good, update display
        updateBillDisplay(data);
        
    } catch (error) {
        console.error('[Bill Update] Error:', error);
        showErrorMessage('Data error. Please refresh.');
    }
});
```

---

## ⚡ Performance Optimization

### 1. Debouncing Updates

```python
# Django - Prevent too frequent updates
from django.utils import timezone
from datetime import timedelta

last_sync_time = {}

def sync_bill_to_customer_display(bill):
    """Debounced sync - max once per second per bill"""
    
    bill_id = str(bill.id)
    now = timezone.now()
    
    if bill_id in last_sync_time:
        elapsed = (now - last_sync_time[bill_id]).total_seconds()
        if elapsed < 1.0:  # Less than 1 second
            # Skip this sync
            return
    
    # Update last sync time
    last_sync_time[bill_id] = now
    
    # Proceed with sync
    # ... (Flask POST request)
```

### 2. Batch Updates

```python
# Flask - Batch multiple events
import threading

pending_events = []
batch_lock = threading.Lock()

def broadcast_event(event_type, data):
    """Add event to batch"""
    with batch_lock:
        pending_events.append({
            'type': event_type,
            'data': data,
            'timestamp': time.time()
        })

def flush_events():
    """Send batched events (called by timer)"""
    with batch_lock:
        if not pending_events:
            return
        
        # Group by type, take latest
        latest_events = {}
        for event in pending_events:
            latest_events[event['type']] = event
        
        # Send to queue
        for event in latest_events.values():
            event_queue.put(event)
        
        # Clear batch
        pending_events.clear()

# Run flush every 100ms
def start_batch_timer():
    threading.Timer(0.1, lambda: (flush_events(), start_batch_timer())).start()
```

### 3. Lazy Loading Images

```html
<!-- customer_display.html -->
<img src="placeholder.jpg"
     data-src="actual-image.jpg"
     loading="lazy"
     onload="this.style.opacity=1">

<style>
img {
    opacity: 0;
    transition: opacity 0.3s;
}
</style>
```

---

## 🔍 Testing & Debugging

### Debug Checklist

```markdown
## Is Flask running?
□ Check: `curl http://localhost:5000/`
□ Response: `{"status": "ok", ...}`

## Is SSE connected?
□ Open customer display in browser
□ F12 → Network tab → Filter: "stream"
□ Should see persistent connection (pending...)
□ Check console for "[SSE] Connected successfully"

## Is data flowing?
□ Add item in kasir monitor
□ Check Flask logs: "[Bill Update] ..."
□ Check browser console: "[SSE] Bill update received"
□ Verify customer display updates

## Is modal syncing?
□ Click "Bayar" in kasir
□ Check Flask logs: "[Modal Show] Type: payment"
□ Check customer display: modal appears
□ Verify inputs are disabled

## Connection recovery?
□ Stop Flask (Ctrl+C)
□ Check customer display: error banner appears
□ Start Flask again
□ Check customer display: reconnects automatically
```

### Debug Tools

#### 1. SSE Monitor Script
```html
<!-- Add to customer_display.html for debugging -->
<div id="debug-panel" style="position: fixed; bottom: 0; right: 0; background: black; color: lime; padding: 10px; font-family: monospace; font-size: 12px; max-height: 300px; overflow-y: auto;">
    <div id="debug-log"></div>
</div>

<script>
function debugLog(message, data = null) {
    const log = document.getElementById('debug-log');
    const entry = document.createElement('div');
    const timestamp = new Date().toLocaleTimeString();
    entry.textContent = `[${timestamp}] ${message}`;
    if (data) {
        entry.textContent += ': ' + JSON.stringify(data);
    }
    log.prepend(entry);
    
    // Keep only last 50 entries
    while (log.children.length > 50) {
        log.lastChild.remove();
    }
}

// Override console.log
const originalLog = console.log;
console.log = function(...args) {
    originalLog.apply(console, args);
    debugLog(args.join(' '));
};
</script>
```

#### 2. Flask Request Logger
```python
# local_api.py
@app.before_request
def log_request():
    print(f"[{request.method}] {request.path} - {request.remote_addr}")

@app.after_request
def log_response(response):
    print(f"  → {response.status_code} {response.content_length} bytes")
    return response
```

#### 3. Network Inspector
```bash
# Monitor Flask traffic
# In PowerShell:
while ($true) {
    $response = Invoke-WebRequest -Uri "http://localhost:5000/" -ErrorAction SilentlyContinue
    if ($response) {
        Write-Host "[OK] Flask is responding" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Flask is down!" -ForegroundColor Red
    }
    Start-Sleep -Seconds 5
}
```

---

## 📝 Summary

### Key Takeaways

1. **SSE = Simple Real-time**
   - One-way push perfect for display updates
   - Auto-reconnect built-in
   - No special server needed (just HTTP)

2. **Flask as Bridge**
   - Decouples Django from customer display
   - In-memory state for speed
   - Easy to scale (could run on separate machine)

3. **Error Tolerance**
   - Customer display failure doesn't break POS
   - Auto-reconnect ensures reliability
   - Graceful degradation on network issues

4. **Performance**
   - <100ms latency for most updates
   - Batch and debounce to prevent spam
   - Lazy loading for large assets

### Next Steps

- [04_TROUBLESHOOTING.md](./04_TROUBLESHOOTING.md) - Common issues & solutions
- [INTEGRATION_GUIDE.md](../INTEGRATION_GUIDE.md) - Production deployment
- [CUSTOMER_DISPLAY_GUIDE.md](../CUSTOMER_DISPLAY_GUIDE.md) - Configuration options

---

**Dibuat**: 2026-02-07  
**Versi**: 1.0  
**Kompleksitas**: Advanced
