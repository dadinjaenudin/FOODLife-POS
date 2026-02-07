# 🔗 Hubungan POS Launcher dengan bill_panel & payment_modal

## 📋 Daftar Isi

1. [Overview Relasi](#overview-relasi)
2. [bill_panel.html - Complete Analysis](#bill_panelhtml---complete-analysis)
3. [payment_modal.html - Complete Analysis](#payment_modalhtml---complete-analysis)
4. [Data Flow: Django → Flask → Customer Display](#data-flow-django--flask--customer-display)
5. [Synchronization Mechanism](#synchronization-mechanism)
6. [Code Walkthrough](#code-walkthrough)

---

## 🎯 Overview Relasi

### Diagram Relasi Lengkap

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DJANGO VIEW LAYER                            │
│                        apps/pos/views.py                             │
│                                                                       │
│  @login_required                                                     │
│  def pos_view(request):                                              │
│      """Main POS interface - Render main.html"""                    │
│      return render(request, 'pos/main.html')                         │
│                                                                       │
│  @login_required                                                     │
│  def bill_panel_view(request):                                       │
│      """Render bill_panel.html untuk sidebar"""                     │
│      bill = get_active_bill(request)                                 │
│      sync_bill_to_customer_display(bill)  ◄─── SYNC TRIGGER!       │
│      return render(request, 'bill_panel.html', {'bill': bill})      │
│                                                                       │
│  @login_required                                                     │
│  def payment_view(request):                                          │
│      """Process payment"""                                           │
│      # Validate payment                                              │
│      # Save to database                                              │
│      # Render success                                                │
│      return render(request, 'payment_success.html')                  │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
                        │ HTTP POST
                        │ sync_bill_to_customer_display()
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          FLASK API LAYER                             │
│                      pos_launcher_qt/local_api.py                    │
│                                                                       │
│  bills_data = {...}      ◄─── IN-MEMORY STORAGE                     │
│  modal_data = {...}                                                  │
│                                                                       │
│  @app.route('/api/customer-display/update-bill', POST)             │
│  def update_bill():                                                  │
│      bills_data.update(request.json)                                │
│      broadcast_event('bill-update', bills_data)  ◄─── SSE EMIT      │
│                                                                       │
│  @app.route('/api/customer-display/show-modal', POST)              │
│  def show_modal():                                                   │
│      modal_data.update(request.json)                                │
│      broadcast_event('modal-show', modal_data)   ◄─── SSE EMIT      │
│                                                                       │
│  @app.route('/api/customer-display/stream', GET)                    │
│  def stream():                                                       │
│      """SSE endpoint for customer display"""                        │
│      yield events continuously...                                    │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
                        │ SSE Push (Server → Client)
                        │
        ┌───────────────┴────────────────┐
        │                                │
        ▼                                ▼
┌────────────────────┐          ┌────────────────────┐
│  KASIR MONITOR     │          │ CUSTOMER DISPLAY   │
│  (Main POS)        │          │ (customer_display) │
├────────────────────┤          ├────────────────────┤
│                    │          │                    │
│  ┌──────────────┐ │          │  EventSource       │
│  │ bill_panel   │◄┼──────────┼─ onmessage ────▶   │
│  │ (HTMX auto)  │ │          │  updateBillDisplay()│
│  └──────────────┘ │          │                    │
│                    │          │  ┌──────────────┐ │
│  ┌──────────────┐ │          │  │ bill_panel   │ │
│  │payment_modal │◄┼──────────┼─▶│ (mirrored)   │ │
│  │(Alpine.js)   │ │          │  └──────────────┘ │
│  └──────────────┘ │          │                    │
│                    │          │  ┌──────────────┐ │
│  Full control      │          │  │payment_modal │ │
│  ✅ Edit           │          │  │(read-only)   │ │
│  ✅ Click          │          │  └──────────────┘ │
│  ✅ Input          │          │                    │
│                    │          │  Read-only view    │
│                    │          │  ❌ No edit        │
│                    │          │  ❌ No click       │
└────────────────────┘          └────────────────────┘
```

---

## 📄 bill_panel.html - Complete Analysis

### File Location & Purpose

**Path:** `templates/pos/partials/bill_panel.html`

**Purpose:**
- Menampilkan daftar item dalam bill aktif
- Show totals (subtotal, tax, discount, grand total)
- Provide actions (hold, pay, etc.)
- Auto-refresh via HTMX every 2 seconds

### HTML Structure

```html
<!-- ============================================ -->
<!-- CONTAINER: Main bill panel wrapper          -->
<!-- ============================================ -->
<div id="bill-panel-content" 
     class="flex flex-col h-full bg-white rounded-lg shadow-lg"
     x-data="billPanelData()">
     
    <!-- ============================================ -->
    <!-- HEADER: Bill number & status                -->
    <!-- ============================================ -->
    <div class="p-4 border-b border-gray-200">
        <div class="flex items-center justify-between">
            <h2 class="text-xl font-bold text-gray-800">Current Order</h2>
            
            {% if bill %}
            <span class="px-3 py-1 text-sm font-semibold rounded-full
                         {{ bill.status == 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100' }}">
                Bill #{{ bill.bill_number }}
            </span>
            {% endif %}
        </div>
    </div>
    
    <!-- ============================================ -->
    <!-- ITEMS LIST: Scrollable list of bill items  -->
    <!-- ============================================ -->
    <div class="flex-1 overflow-y-auto p-4 space-y-2">
        {% if bill and bill.items.exists %}
            {% for item in bill.items.all %}
            <div class="bill-item p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition"
                 data-item-id="{{ item.id }}">
                 
                <!-- Item Info: Name + Modifiers + Notes -->
                <div class="flex items-start justify-between mb-2">
                    <div class="flex-1">
                        <!-- Product Name -->
                        <div class="font-semibold text-gray-900">
                            {{ item.product.name }}
                        </div>
                        
                        <!-- Modifiers (if any) -->
                        {% if item.modifiers %}
                        <div class="flex flex-wrap gap-1 mt-1">
                            {% for modifier in item.modifiers %}
                            <span class="px-2 py-0.5 text-xs bg-blue-100 text-blue-800 rounded">
                                + {{ modifier.name }}
                                {% if modifier.price > 0 %}
                                    (+{{ modifier.price|currency }})
                                {% endif %}
                            </span>
                            {% endfor %}
                        </div>
                        {% endif %}
                        
                        <!-- Notes (if any) -->
                        {% if item.notes %}
                        <div class="mt-1 text-sm text-gray-600">
                            <span class="text-gray-400">📝</span> {{ item.notes }}
                        </div>
                        {% endif %}
                    </div>
                    
                    <!-- Item Actions -->
                    <div class="flex gap-1 ml-2">
                        <button @click="editItem('{{ item.id }}')"
                                class="p-1 text-blue-600 hover:bg-blue-50 rounded">
                            ✏️
                        </button>
                        <button @click="removeItem('{{ item.id }}')"
                                class="p-1 text-red-600 hover:bg-red-50 rounded">
                            🗑️
                        </button>
                    </div>
                </div>
                
                <!-- Quantity & Price -->
                <div class="flex items-center justify-between">
                    <!-- Quantity Controls -->
                    <div class="flex items-center gap-2">
                        <button @click="decreaseQty('{{ item.id }}')"
                                class="w-8 h-8 flex items-center justify-center
                                       bg-white border border-gray-300 rounded
                                       hover:bg-gray-50">
                            −
                        </button>
                        
                        <span class="w-12 text-center font-semibold">
                            × {{ item.quantity }}
                        </span>
                        
                        <button @click="increaseQty('{{ item.id }}')"
                                class="w-8 h-8 flex items-center justify-center
                                       bg-white border border-gray-300 rounded
                                       hover:bg-gray-50">
                            +
                        </button>
                    </div>
                    
                    <!-- Item Subtotal -->
                    <div class="text-lg font-bold text-gray-900">
                        {{ item.subtotal|currency }}
                    </div>
                </div>
            </div>
            {% endfor %}
        {% else %}
            <!-- Empty State -->
            <div class="flex flex-col items-center justify-center h-full text-gray-400">
                <svg class="w-16 h-16 mb-4" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M3 1a1 1 0 000 2h1.22l.305 1.222a.997.997 0 00.01.042l1.358 5.43-.893.892C3.74 11.846 4.632 14 6.414 14H15a1 1 0 000-2H6.414l1-1H14a1 1 0 00.894-.553l3-6A1 1 0 0017 3H6.28l-.31-1.243A1 1 0 005 1H3z"/>
                </svg>
                <p class="text-lg font-medium">No items in order</p>
                <p class="text-sm">Add products to start</p>
            </div>
        {% endif %}
    </div>
    
    <!-- ============================================ -->
    <!-- TOTALS SECTION: Subtotal, Tax, Discount     -->
    <!-- ============================================ -->
    {% if bill %}
    <div class="p-4 border-t border-gray-200 space-y-2">
        <!-- Subtotal -->
        <div class="flex justify-between text-gray-700">
            <span>Subtotal:</span>
            <span class="font-semibold">{{ bill.subtotal|currency }}</span>
        </div>
        
        <!-- Discount (if exists) -->
        {% if bill.discount > 0 %}
        <div class="flex justify-between text-red-600">
            <span>Discount:</span>
            <span class="font-semibold">- {{ bill.discount|currency }}</span>
        </div>
        {% endif %}
        
        <!-- Tax -->
        <div class="flex justify-between text-gray-700">
            <span>Tax (11%):</span>
            <span class="font-semibold">{{ bill.tax|currency }}</span>
        </div>
        
        <!-- Grand Total -->
        <div class="flex justify-between text-xl font-bold text-gray-900 pt-2 border-t">
            <span>TOTAL:</span>
            <span>{{ bill.total|currency }}</span>
        </div>
    </div>
    {% endif %}
    
    <!-- ============================================ -->
    <!-- ACTION BUTTONS: Hold, Void, Pay             -->
    <!-- ============================================ -->
    {% if bill %}
    <div class="p-4 border-t border-gray-200 grid grid-cols-2 gap-2">
        <!-- Hold Bill -->
        <button @click="holdBill()"
                class="px-4 py-3 bg-yellow-500 text-white font-semibold rounded-lg
                       hover:bg-yellow-600 transition">
            🕐 Hold
        </button>
        
        <!-- Pay Button (Primary Action) -->
        <button @click="openPaymentModal()"
                class="px-4 py-3 bg-green-500 text-white font-semibold rounded-lg
                       hover:bg-green-600 transition shadow-lg">
            💰 Pay
        </button>
    </div>
    {% endif %}
</div>

<!-- ============================================ -->
<!-- ALPINE.JS DATA LAYER                         -->
<!-- ============================================ -->
<script>
function billPanelData() {
    return {
        // ========================================
        // METHODS: Item Actions
        // ========================================
        
        editItem(itemId) {
            console.log('[Bill Panel] Edit item:', itemId);
            // Load edit modal
            htmx.ajax('GET', `/pos/item/${itemId}/edit/`, {
                target: '#modal-container',
                swap: 'innerHTML'
            });
        },
        
        removeItem(itemId) {
            if (!confirm('Remove this item?')) return;
            
            console.log('[Bill Panel] Remove item:', itemId);
            htmx.ajax('DELETE', `/pos/item/${itemId}/`, {
                target: '#bill-panel',
                swap: 'innerHTML'
            }).then(() => {
                // Item removed, bill will auto-refresh via HTMX
                // Customer display will auto-update via SSE
            });
        },
        
        increaseQty(itemId) {
            console.log('[Bill Panel] Increase qty:', itemId);
            this.updateQuantity(itemId, 1);
        },
        
        decreaseQty(itemId) {
            console.log('[Bill Panel] Decrease qty:', itemId);
            this.updateQuantity(itemId, -1);
        },
        
        updateQuantity(itemId, delta) {
            htmx.ajax('POST', `/pos/item/${itemId}/quantity/`, {
                values: { delta: delta },
                target: '#bill-panel',
                swap: 'innerHTML'
            }).then(() => {
                console.log('[Bill Panel] Quantity updated');
                // Bill auto-refresh
                // Customer display auto-update
            });
        },
        
        // ========================================
        // METHODS: Bill Actions
        // ========================================
        
        holdBill() {
            console.log('[Bill Panel] Hold bill');
            htmx.ajax('GET', '/pos/hold-bill-modal/', {
                target: '#modal-container',
                swap: 'innerHTML'
            });
        },
        
        openPaymentModal() {
            console.log('[Bill Panel] Open payment modal');
            
            // Load payment modal via HTMX
            htmx.ajax('GET', '/pos/payment-modal/', {
                target: '#modal-container',
                swap: 'innerHTML'
            }).then(() => {
                // Modal loaded
                // Alpine.js will auto-initialize
                // Auto-sync to customer display (via payment_modal.html logic)
            });
        }
    }
}
</script>
```

### HTMX Auto-Refresh Mechanism

**In main.html:**
```html
<div id="bill-panel"
     hx-get="/pos/bill-panel/"
     hx-trigger="every 2s"
     hx-swap="innerHTML"
     hx-indicator="#bill-loading">
    <!-- Initial content -->
    Loading bill panel...
</div>
```

**How it works:**
1. **Every 2 seconds**, HTMX sends GET request to `/pos/bill-panel/`
2. Django renders `bill_panel.html` with **latest data** from database
3. HTMX **replaces** innerHTML of `#bill-panel` with response
4. Alpine.js **re-initializes** (data & methods)
5. **Side effect:** Django also calls `sync_bill_to_customer_display()`

**Result:**
- Kasir monitor: Always shows latest bill
- Customer display: Always synced via SSE

### Sync to Customer Display

**In Django view (`apps/pos/views.py`):**
```python
def bill_panel_view(request):
    """Render bill panel for HTMX polling"""
    
    # Get active bill
    bill_id = request.session.get('active_bill_id')
    bill = Bill.objects.get(id=bill_id) if bill_id else None
    
    # Calculate totals
    if bill:
        bill.subtotal = sum(item.subtotal for item in bill.items.all())
        bill.tax = bill.subtotal * Decimal('0.11')
        bill.total = bill.subtotal + bill.tax - bill.discount
        bill.save()
        
        # ⚡ SYNC TO CUSTOMER DISPLAY
        sync_bill_to_customer_display(bill)
    
    return render(request, 'pos/partials/bill_panel.html', {'bill': bill})


def sync_bill_to_customer_display(bill):
    """Send bill data to Flask API"""
    
    # Prepare data
    data = {
        'bill_id': str(bill.id),
        'bill_number': bill.bill_number,
        'items': [
            {
                'id': str(item.id),
                'name': item.product.name,
                'quantity': item.quantity,
                'unit_price': float(item.unit_price),
                'subtotal': float(item.subtotal),
                'modifiers': item.modifiers,
                'notes': item.notes
            }
            for item in bill.items.all()
        ],
        'subtotal': float(bill.subtotal),
        'tax': float(bill.tax),
        'discount': float(bill.discount),
        'total': float(bill.total)
    }
    
    # POST to Flask API
    try:
        response = requests.post(
            'http://localhost:5000/api/customer-display/update-bill',
            json=data,
            timeout=1
        )
        
        if response.status_code == 200:
            logger.info(f"[Sync] Bill {bill.bill_number} synced to customer display")
        else:
            logger.warning(f"[Sync] Failed: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"[Sync] Error: {e}")
        # Don't fail main request if sync fails
```

---

## 💳 payment_modal.html - Complete Analysis

### File Location & Purpose

**Path:** `templates/pos/partials/payment_modal.html`

**Purpose:**
- Accept payment from customer (cash, QRIS, card, etc.)
- Calculate change for cash payments
- Support split payments
- **Auto-sync to customer display** (read-only mode)
- Validate payment before processing

### Modal Structure

```html
<!-- ============================================ -->
<!-- MODAL OVERLAY & CONTAINER                    -->
<!-- ============================================ -->
<div id="paymentModalOverlay"
     class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
     x-data="paymentModalData()"
     x-show="$store.modal.payment"
     x-transition
     @click.self="closeModal()"
     
     <!-- 🔥 CRITICAL: Sync attributes -->
     data-sync-to-customer="true"
     data-customer-readonly="true"
     data-modal-type="payment"
     data-bill-id="{{ bill.id }}"
     data-bill-total="{{ bill.total }}">
     
    <!-- ============================================ -->
    <!-- MODAL CONTENT BOX                            -->
    <!-- ============================================ -->
    <div class="bg-white rounded-lg shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden"
         @click.stop>
         
        <!-- ============================================ -->
        <!-- HEADER: Title & Close Button                -->
        <!-- ============================================ -->
        <div class="flex items-center justify-between p-6 border-b border-gray-200">
            <h2 class="text-2xl font-bold text-gray-900">
                💰 Payment - Bill #{{ bill.bill_number }}
            </h2>
            
            <button @click="closeModal()"
                    class="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
            </button>
        </div>
        
        <!-- ============================================ -->
        <!-- BILL SUMMARY: Subtotal, Tax, Discount        -->
        <!-- ============================================ -->
        <div class="p-6 bg-gray-50 border-b">
            <div class="space-y-2">
                <div class="flex justify-between text-gray-700">
                    <span>Subtotal:</span>
                    <span class="font-semibold">{{ bill.subtotal|currency }}</span>
                </div>
                
                {% if bill.discount > 0 %}
                <div class="flex justify-between text-red-600">
                    <span>Discount:</span>
                    <span class="font-semibold">- {{ bill.discount|currency }}</span>
                </div>
                {% endif %}
                
                <div class="flex justify-between text-gray-700">
                    <span>Tax (11%):</span>
                    <span class="font-semibold">{{ bill.tax|currency }}</span>
                </div>
                
                <div class="flex justify-between text-2xl font-bold text-gray-900 pt-2 border-t">
                    <span>TOTAL:</span>
                    <span>{{ bill.total|currency }}</span>
                </div>
            </div>
        </div>
        
        <!-- ============================================ -->
        <!-- PAYMENT METHOD TABS                          -->
        <!-- ============================================ -->
        <div class="p-6">
            <div class="grid grid-cols-3 gap-3 mb-6">
                <!-- Cash Tab -->
                <button @click="selectMethod('cash')"
                        :class="selectedMethod === 'cash' ? 
                                'bg-green-500 text-white' : 
                                'bg-gray-100 text-gray-700 hover:bg-gray-200'"
                        class="p-4 rounded-lg font-semibold transition">
                    💵 Cash
                </button>
                
                <!-- QRIS Tab -->
                <button @click="selectMethod('qris')"
                        :class="selectedMethod === 'qris' ? 
                                'bg-green-500 text-white' : 
                                'bg-gray-100 text-gray-700 hover:bg-gray-200'"
                        class="p-4 rounded-lg font-semibold transition">
                    📱 QRIS
                </button>
                
                <!-- Card Tab -->
                <button @click="selectMethod('card')"
                        :class="selectedMethod === 'card' ? 
                                'bg-green-500 text-white' : 
                                'bg-gray-100 text-gray-700 hover:bg-gray-200'"
                        class="p-4 rounded-lg font-semibold transition">
                    💳 Card
                </button>
            </div>
            
            <!-- ============================================ -->
            <!-- CASH PAYMENT FORM                            -->
            <!-- ============================================ -->
            <div x-show="selectedMethod === 'cash'" class="space-y-4">
                <!-- Amount Paid Input -->
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">
                        Amount Paid:
                    </label>
                    <input type="number"
                           x-model.number="cashPaid"
                           @input="calculateChange()"
                           :disabled="$store.isCustomerDisplay"
                           placeholder="Enter amount"
                           class="w-full px-4 py-3 text-2xl font-bold border border-gray-300 rounded-lg
                                  focus:ring-2 focus:ring-green-500 focus:border-transparent">
                </div>
                
                <!-- Quick Amount Buttons -->
                <div x-show="!$store.isCustomerDisplay" 
                     class="grid grid-cols-4 gap-2">
                    <button @click="cashPaid = {{ bill.total }}; calculateChange()"
                            class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
                        Exact
                    </button>
                    <button @click="cashPaid = 50000; calculateChange()"
                            class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
                        50K
                    </button>
                    <button @click="cashPaid = 100000; calculateChange()"
                            class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
                        100K
                    </button>
                    <button @click="cashPaid = roundUp({{ bill.total }}); calculateChange()"
                            class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
                        Round
                    </button>
                </div>
                
                <!-- Change Display -->
                <div x-show="change >= 0" 
                     class="p-4 bg-green-50 border border-green-200 rounded-lg">
                    <div class="flex justify-between items-center">
                        <span class="text-lg font-medium text-green-800">Change:</span>
                        <span class="text-3xl font-bold text-green-600"
                              x-text="formatCurrency(change)"></span>
                    </div>
                </div>
            </div>
            
            <!-- ============================================ -->
            <!-- QRIS PAYMENT FORM                            -->
            <!-- ============================================ -->
            <div x-show="selectedMethod === 'qris'" class="space-y-4">
                <div class="flex flex-col items-center">
                    <!-- QR Code -->
                    <div class="p-4 bg-white border-2 border-gray-300 rounded-lg">
                        <img :src="qrisUrl || '/static/images/qris-placeholder.png'"
                             alt="QRIS Code"
                             class="w-64 h-64">
                    </div>
                    
                    <!-- Instructions -->
                    <p class="mt-4 text-center text-gray-600">
                        Scan QR code with mobile banking app
                    </p>
                    
                    <!-- Status Indicator -->
                    <div x-show="qrisStatus === 'waiting'"
                         class="mt-4 flex items-center gap-3">
                        <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                        <span class="text-blue-600 font-medium">Waiting for payment...</span>
                    </div>
                    
                    <div x-show="qrisStatus === 'success'"
                         class="mt-4 flex items-center gap-3 text-green-600">
                        <svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"/>
                        </svg>
                        <span class="font-medium">Payment received!</span>
                    </div>
                </div>
            </div>
            
            <!-- ============================================ -->
            <!-- CARD PAYMENT FORM                            -->
            <!-- ============================================ -->
            <div x-show="selectedMethod === 'card'" class="space-y-4">
                <!-- Card Reference Input -->
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">
                        Card Approval Code:
                    </label>
                    <input type="text"
                           x-model="cardReference"
                           :disabled="$store.isCustomerDisplay"
                           placeholder="Enter approval code from EDC"
                           class="w-full px-4 py-3 text-lg border border-gray-300 rounded-lg
                                  focus:ring-2 focus:ring-green-500">
                </div>
                
                <!-- EDC Instructions -->
                <div class="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <h4 class="font-semibold text-blue-900 mb-2">EDC Instructions:</h4>
                    <ol class="list-decimal list-inside space-y-1 text-blue-800">
                        <li>Insert/tap card into EDC machine</li>
                        <li>Enter amount: <strong x-text="formatCurrency({{ bill.total }})"></strong></li>
                        <li>Wait for approval</li>
                        <li>Enter approval code above</li>
                    </ol>
                </div>
            </div>
        </div>
        
        <!-- ============================================ -->
        <!-- ACTION BUTTONS: Cancel & Confirm             -->
        <!-- ============================================ -->
        <div class="flex gap-3 p-6 border-t bg-gray-50">
            <!-- Cancel Button (only on kasir) -->
            <button @click="closeModal()"
                    x-show="!$store.isCustomerDisplay"
                    class="flex-1 px-6 py-3 bg-gray-200 text-gray-700 font-semibold rounded-lg
                           hover:bg-gray-300 transition">
                Cancel
            </button>
            
            <!-- Confirm Button (only on kasir) -->
            <button @click="processPayment()"
                    x-show="!$store.isCustomerDisplay"
                    :disabled="!canProcess()"
                    :class="canProcess() ? 
                            'bg-green-500 hover:bg-green-600' : 
                            'bg-gray-300 cursor-not-allowed'"
                    class="flex-1 px-6 py-3 text-white font-semibold rounded-lg transition">
                <span x-show="!processing">✅ Confirm Payment</span>
                <span x-show="processing">⏳ Processing...</span>
            </button>
            
            <!-- Customer Display Message -->
            <div x-show="$store.isCustomerDisplay"
                 class="w-full text-center py-3 text-gray-600 font-medium">
                ⏳ Please wait for cashier to confirm payment...
            </div>
        </div>
    </div>
</div>

<!-- ============================================ -->
<!-- ALPINE.JS DATA & LOGIC                       -->
<!-- ============================================ -->
<script>
function paymentModalData() {
    return {
        // ========================================
        // STATE
        // ========================================
        selectedMethod: 'cash',
        cashPaid: 0,
        change: -1,
        cardReference: '',
        qrisUrl: '',
        qrisStatus: 'pending',  // 'pending', 'waiting', 'success'
        processing: false,
        
        // ========================================
        // COMPUTED PROPERTIES
        // ========================================
        get billTotal() {
            return parseFloat(this.$el.dataset.billTotal);
        },
        
        // ========================================
        // METHODS: Payment Logic
        // ========================================
        
        selectMethod(method) {
            console.log('[Payment] Method selected:', method);
            this.selectedMethod = method;
            
            if (method === 'qris') {
                this.generateQRIS();
            }
        },
        
        calculateChange() {
            this.change = this.cashPaid - this.billTotal;
            console.log('[Payment] Change calculated:', this.change);
        },
        
        roundUp(amount) {
            return Math.ceil(amount / 1000) * 1000;
        },
        
        formatCurrency(amount) {
            return new Intl.NumberFormat('id-ID', {
                style: 'currency',
                currency: 'IDR',
                minimumFractionDigits: 0
            }).format(amount);
        },
        
        canProcess() {
            if (this.processing) return false;
            
            switch(this.selectedMethod) {
                case 'cash':
                    return this.cashPaid >= this.billTotal;
                case 'qris':
                    return this.qrisStatus === 'success';
                case 'card':
                    return this.cardReference.length > 0;
                default:
                    return false;
            }
        },
        
        async generateQRIS() {
            console.log('[Payment] Generating QRIS...');
            this.qrisStatus = 'waiting';
            
            try {
                const response = await fetch('/pos/generate-qris/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: JSON.stringify({
                        bill_id: this.$el.dataset.billId,
                        amount: this.billTotal
                    })
                });
                
                const data = await response.json();
                this.qrisUrl = data.qr_url;
                
                // Poll for payment status
                this.pollQRISStatus(data.transaction_id);
                
            } catch (error) {
                console.error('[Payment] QRIS error:', error);
                alert('Failed to generate QRIS. Please try again.');
            }
        },
        
        async pollQRISStatus(transactionId) {
            const pollInterval = setInterval(async () => {
                try {
                    const response = await fetch(`/pos/qris-status/${transactionId}/`);
                    const data = await response.json();
                    
                    if (data.status === 'paid') {
                        this.qrisStatus = 'success';
                        clearInterval(pollInterval);
                        
                        // Auto-process payment
                        setTimeout(() => this.processPayment(), 1000);
                    }
                    
                } catch (error) {
                    console.error('[Payment] Status poll error:', error);
                    clearInterval(pollInterval);
                }
            }, 3000);  // Poll every 3 seconds
        },
        
        async processPayment() {
            if (!this.canProcess() || this.processing) return;
            
            this.processing = true;
            console.log('[Payment] Processing payment...');
            
            const paymentData = {
                bill_id: this.$el.dataset.billId,
                payment_method: this.selectedMethod,
                amount: this.billTotal,
                cash_paid: this.cashPaid,
                change: this.change,
                card_reference: this.cardReference
            };
            
            try {
                const response = await fetch('/pos/payment/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: JSON.stringify(paymentData)
                });
                
                if (response.ok) {
                    console.log('[Payment] Success!');
                    
                    // Show success message
                    const result = await response.text();
                    document.getElementById('payment-result').innerHTML = result;
                    
                    // ⚡ Clear customer display
                    await fetch('http://localhost:5000/api/customer-display/clear', {
                        method: 'POST'
                    });
                    
                    // Close modal
                    this.closeModal();
                    
                } else {
                    const error = await response.json();
                    alert('Payment failed: ' + error.message);
                }
                
            } catch (error) {
                console.error('[Payment] Error:', error);
                alert('Connection error. Please try again.');
            } finally {
                this.processing = false;
            }
        },
        
        closeModal() {
            console.log('[Payment] Closing modal');
            this.$store.modal.payment = false;
            
            // ⚡ Hide modal on customer display
            fetch('http://localhost:5000/api/customer-display/hide-modal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ modal_type: 'payment' })
            });
        },
        
        // ========================================
        // INIT: Run on modal open
        // ========================================
        init() {
            console.log('[Payment] Modal initialized');
            console.log('[Payment] Bill total:', this.billTotal);
            console.log('[Payment] Is customer display:', this.$store.isCustomerDisplay);
            
            // ⚡ Auto-sync to customer display
            if (!this.$store.isCustomerDisplay && this.$el.dataset.syncToCustomer === 'true') {
                this.syncToCustomerDisplay();
            }
        },
        
        syncToCustomerDisplay() {
            console.log('[Payment] Syncing to customer display...');
            
            const modalClone = this.$el.cloneNode(true);
            
            const data = {
                modal_type: 'payment',
                html: modalClone.outerHTML,
                data: {
                    bill_id: this.$el.dataset.billId,
                    total: this.billTotal,
                    readonly: true
                }
            };
            
            fetch('http://localhost:5000/api/customer-display/show-modal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            }).then(response => {
                if (response.ok) {
                    console.log('[Payment] Sync success');
                } else {
                    console.error('[Payment] Sync failed');
                }
            }).catch(error => {
                console.error('[Payment] Sync error:', error);
            });
        }
    }
}

function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}
</script>
```

---

## 🔄 Data Flow: Django → Flask → Customer Display

### Complete Flow dengan Timing

```
TIME    EVENT                           LOCATION                ACTION
────────────────────────────────────────────────────────────────────────────

0ms     User clicks "Pay"               Kasir Monitor           Alpine.js openPaymentModal()

10ms    HTMX GET request                Browser → Django        GET /pos/payment-modal/

30ms    Django renders template         Django Server           Render payment_modal.html
                                                                Context: {bill: Bill object}

50ms    HTML response returned          Django → Browser        427 lines HTML + Alpine.js

60ms    Modal injected to DOM           Kasir Monitor           #modal-container innerHTML

70ms    Alpine.js initializes           Kasir Monitor           paymentModalData() init()

80ms    Auto-sync triggered             Kasir Monitor           syncToCustomerDisplay()

90ms    Clone modal HTML                Kasir Monitor (JS)      modalClone = el.cloneNode(true)

100ms   POST to Flask API               Browser → Flask         POST /api/customer-display/show-modal
                                                                Body: {modal_type, html, data}

110ms   Flask stores data               Flask Server            modal_data global updated

120ms   Flask broadcast SSE             Flask Server            broadcast_event('modal-show', ...)

130ms   SSE event emitted               Flask → Customer        event: modal-show
                                                                data: {...}

140ms   Customer receives event         Customer Display        EventSource.onmessage

150ms   Parse JSON                      Customer Display (JS)   JSON.parse(event.data)

160ms   Inject HTML to DOM              Customer Display        #modal-container innerHTML

170ms   Disable all inputs              Customer Display (JS)   querySelectorAll('input').disabled

180ms   Hide action buttons             Customer Display (JS)   querySelectorAll('button').hide

190ms   Show customer message           Customer Display        "Please wait for cashier..."

200ms   ✅ BOTH DISPLAYS SHOWING MODAL  Kasir + Customer        Sync complete!

────────────────────────────────────────────────────────────────────────────
TOTAL LATENCY: 200ms (from click to customer display showing modal)
```

### Data Transformation

**1. Django Context → HTML:**
```python
# Django view
bill = Bill.objects.get(...)
context = {
    'bill': bill,  # Bill object with all fields
    'PAYMENT_CONFIG': {...}  # Payment methods config
}
return render(request, 'payment_modal.html', context)
```

**2. HTML → JavaScript Object:**
```javascript
// Alpine.js data extraction
const modalElement = document.getElementById('paymentModal');
const data = {
    bill_id: modalElement.dataset.billId,
    total: parseFloat(modalElement.dataset.billTotal),
    //... other data attributes
};
```

**3. JavaScript → Flask JSON:**
```javascript
// POST to Flask
fetch('http://localhost:5000/api/customer-display/show-modal', {
    method: 'POST',
    body: JSON.stringify({
        modal_type: 'payment',
        html: modalClone.outerHTML,  // Full HTML string
        data: data
    })
});
```

**4. Flask → SSE Event:**
```python
# Flask broadcast
modal_data = {
    'visible': True,
    'modal_type': request.json['modal_type'],
    'html': request.json['html'],  # HTML string
    'data': request.json['data']   # Metadata
}

broadcast_event('modal-show', modal_data)

# SSE format
f"event: modal-show\ndata: {json.dumps(modal_data)}\n\n"
```

**5. SSE → Customer Display DOM:**
```javascript
// Customer display receive & render
eventSource.addEventListener('modal-show', (event) => {
    const data = JSON.parse(event.data);
    
    // Inject HTML
    document.getElementById('modal-container').innerHTML = data.html;
    
    // Apply read-only mode
    Alpine.store('isCustomerDisplay', true);
    
    // Disable interactions
    disableInputs();
    hideActionButtons();
});
```

---

## 🔧 Synchronization Mechanism

### Attribute-Driven Sync

**Key Attributes:**
```html
data-sync-to-customer="true"      ← Enable auto-sync
data-customer-readonly="true"     ← Force read-only on customer
data-modal-type="payment"         ← Identify modal type
data-bill-id="{{ bill.id }}"      ← Pass bill ID
data-bill-total="{{ bill.total }}" ← Pass total for calculations
```

**How Alpine.js Detects:**
```javascript
// In Alpine.js init()
init() {
    // Check if should sync
    if (!this.$store.isCustomerDisplay && 
        this.$el.dataset.syncToCustomer === 'true') {
        
        // Trigger sync
        this.syncToCustomerDisplay();
    }
}
```

### Read-Only Transformation

**On Customer Display:**
```javascript
// After HTML injection
function makeReadOnly() {
    const container = document.getElementById('modal-container');
    
    // 1. Set global flag
    Alpine.store('isCustomerDisplay', true);
    
    // 2. Disable all inputs
    container.querySelectorAll('input, select, textarea').forEach(el => {
        el.disabled = true;
        el.readOnly = true;
    });
    
    // 3. Hide action buttons (keep close button)
    container.querySelectorAll('button').forEach(el => {
        if (!el.classList.contains('modal-close')) {
            el.style.display = 'none';
        }
    });
    
    // 4. Add visual indicator
    container.classList.add('customer-display-mode');
}
```

**CSS for Customer Display:**
```css
/* Make it clear this is read-only */
.customer-display-mode input,
.customer-display-mode select,
.customer-display-mode textarea {
    background-color: #f3f4f6 !important;
    cursor: not-allowed !important;
    opacity: 0.7 !important;
}

.customer-display-mode button[hidden] {
    display: none !important;
}
```

---

## 📝 Summary

### Hubungan bill_panel & payment_modal dengan POS Launcher

| Aspek | bill_panel.html | payment_modal.html |
|-------|-----------------|-------------------|
| **Tipe** | Partial template (sidebar) | Partial template (modal overlay) |
| **Update Frequency** | Every 2 seconds (HTMX poll) | On-demand (user click "Pay") |
| **Sync Trigger** | Django view (automatic) | Alpine.js (on modal open) |
| **Sync Method** | HTTP POST to Flask (via Django) | HTTP POST to Flask (via JavaScript) |
| **Customer Display** | Always visible when bill exists | Only visible during payment |
| **Data Source** | Django ORM (Bill model) | Django ORM (Bill model) |
| **Interactivity (Kasir)** | Full control (edit, delete, qty) | Full control (method, amount, confirm) |
| **Interactivity (Customer)** | Read-only display | Read-only display |
| **Lines of Code** | ~200 lines | ~427 lines |
| **Complexity** | Simple (list + totals) | Complex (multi-method, validation, calculation) |

### Key Takeaways

1. **bill_panel.html** = Real-time order display
   - Updates constantly (every 2s)
   - Synced automatically by Django
   - Simple view-only on customer display

2. **payment_modal.html** = Interactive payment processor
   - Opens on-demand
   - Synced when opened (one-time)
   - Complex read-only transformation on customer

3. **Both components use SSE** for real-time customer display updates
   - Flask API acts as message broker
   - EventSource provides auto-reconnect
   - In-memory state for fast sync

4. **Separation of Concerns**
   - Django = Business logic + Database
   - Flask = Real-time bridge
   - Customer Display = Pure presentation

---

**Dibuat**: 2026-02-07  
**Versi**: 1.0  
**Untuk:** Deep understanding bill_panel & payment_modal
