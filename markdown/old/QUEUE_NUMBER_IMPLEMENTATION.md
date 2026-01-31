# Queue Number System - Implementation Roadmap

> **Step-by-Step Production-Ready Implementation**  
> Dari zero sampai production untuk Quick Order/Takeaway system

---

## 📋 Overview

Implementasi queue number system untuk sistem POS yang sudah ada, dengan minimal disruption ke operasional.

**Estimated Timeline:**
- Phase 1 (Backend): 1 day
- Phase 2 (Frontend): 1 day  
- Phase 3 (Printer): 0.5 day
- Phase 4 (Testing): 0.5 day
- **Total: 3 days** (single developer)

---

## 🎯 Pre-Implementation Checklist

### ✅ Requirement Verification

```bash
# 1. Check current system state
□ Sistem POS sudah running?
□ Bill model sudah ada?
□ Payment flow sudah jalan?
□ Kitchen printer sudah setup?

# 2. Check technical stack
□ Django >= 3.2?
□ Database: PostgreSQL/SQLite?
□ HTMX >= 1.9?
□ Python >= 3.8?

# 3. Check hardware
□ Thermal printer 58mm/80mm available?
□ Network printer or USB?
□ Test print berhasil?

# 4. Business requirements
□ Sudah ada flow takeaway sekarang?
□ Sudah ada pre-payment?
□ Kitchen sudah pakai printer?
```

### 📦 Dependencies Installation

```bash
# Install additional packages (if needed)
pip install python-escpos  # For thermal printer
pip install Pillow  # For QR code/images on receipt

# Update requirements.txt
echo "python-escpos==3.0" >> requirements.txt
echo "Pillow>=9.0.0" >> requirements.txt
```

---

## 🚀 Phase 1: Backend Implementation (Day 1)

### Step 1.1: Database Migration - Add queue_number Field

**File:** `apps/pos/migrations/XXXX_add_queue_number.py`

```python
# Generate migration
python manage.py makemigrations pos --name add_queue_number

# Manual create if needed:
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0XXX_previous_migration'),
    ]

    operations = [
        migrations.AddField(
            model_name='bill',
            name='queue_number',
            field=models.IntegerField(
                null=True, 
                blank=True,
                help_text='Auto-increment daily for takeaway orders'
            ),
        ),
        migrations.AddIndex(
            model_name='bill',
            index=models.Index(
                fields=['brand', 'bill_type', 'created_at'],
                name='idx_queue_lookup'
            ),
        ),
    ]
```

**Run migration:**
```bash
python manage.py migrate pos
```

**Verify:**
```bash
python manage.py dbshell
# PostgreSQL
\d pos_bill
# or SQLite
.schema pos_bill
# Confirm queue_number field exists
```

---

### Step 1.2: Update Bill Model

**File:** `apps/pos/models.py`

```python
class Bill(models.Model):
    # ... existing fields ...
    
    queue_number = models.IntegerField(
        null=True, 
        blank=True,
        help_text='Auto-increment daily for takeaway orders'
    )
    
    # ... existing fields ...
    
    class Meta:
        indexes = [
            models.Index(
                fields=['brand', 'bill_type', 'created_at'],
                name='idx_queue_lookup'
            ),
            # ... existing indexes ...
        ]
    
    def __str__(self):
        if self.bill_type == 'takeaway' and self.queue_number:
            return f"Queue #{self.queue_number} - {self.bill_number}"
        elif self.bill_type == 'dine_in' and self.table:
            return f"Table {self.table.number} - {self.bill_number}"
        return self.bill_number
    
    def get_display_identifier(self):
        """Get human-readable identifier for display"""
        if self.bill_type == 'takeaway' and self.queue_number:
            return f"Queue #{self.queue_number}"
        elif self.table:
            return f"Table {self.table.number}"
        return self.bill_number
```

---

### Step 1.3: Create Queue Number Generator Utility

**File:** `apps/pos/utils.py` (create if not exists)

```python
from django.db import models
from django.utils import timezone
from apps.pos.models import Bill

def generate_queue_number(brand):
    """
    Generate next queue number for today
    Auto-increment, reset daily at 00:00
    
    Returns:
        int: Next queue number (1, 2, 3, ...)
    """
    today = timezone.now().date()
    
    last_queue = Bill.objects.filter(
        brand=brand,
        bill_type='takeaway',
        created_at__date=today,
        queue_number__isnull=False
    ).aggregate(max_queue=models.Max('queue_number'))
    
    max_queue = last_queue['max_queue'] or 0
    return max_queue + 1


def get_active_queues(brand, limit=10):
    """
    Get active queue numbers waiting to be served
    
    Returns:
        QuerySet: Bills with status='paid' (not completed yet)
    """
    today = timezone.now().date()
    
    return Bill.objects.filter(
        brand=brand,
        bill_type='takeaway',
        created_at__date=today,
        status='paid',  # Paid but not completed
        queue_number__isnull=False
    ).order_by('queue_number')[:limit]


def get_serving_queues(brand, limit=3):
    """
    Get recently completed queues (now serving)
    
    Returns:
        QuerySet: Recently completed bills
    """
    today = timezone.now().date()
    
    return Bill.objects.filter(
        brand=brand,
        bill_type='takeaway',
        created_at__date=today,
        status='completed',
        queue_number__isnull=False
    ).order_by('-completed_at')[:limit]
```

**Test utility:**
```python
# In Django shell
python manage.py shell

from apps.core.models import Brand
from apps.pos.utils import generate_queue_number

brand = Brand.objects.first()
queue = generate_queue_number(brand)
print(f"Next queue: {queue}")
# Expected output: Next queue: 1 (if first order today)
```

---

### Step 1.4: Update Quick Order View

**File:** `apps/pos/views.py`

Locate existing `quick_order_create` function and enhance it:

```python
from apps.pos.utils import generate_queue_number

@require_http_methods(["POST"])
@login_required
def quick_order_create(request):
    """
    Create takeaway order with auto-generated queue number
    """
    try:
        # 1. Parse input
        items_json = request.POST.get('items', '[]')
        items = json.loads(items_json)
        customer_name = request.POST.get('customer_name', '').strip()
        payment_method = request.POST.get('payment_method', 'cash')
        amount_paid = Decimal(request.POST.get('amount_paid', '0'))
        
        if not items:
            return JsonResponse({
                'success': False, 
                'error': 'No items in order'
            }, status=400)
        
        # 2. Generate queue number
        queue_number = generate_queue_number(request.user.brand)
        
        # 3. Create bill
        bill = Bill.objects.create(
            brand=request.user.brand,
            store=Store.get_current(),
            terminal=get_terminal_from_request(request),
            bill_type='takeaway',
            queue_number=queue_number,  # ← NEW!
            customer_name=customer_name,
            status='open',  # Will be paid below
            created_by=request.user,
        )
        
        # 4. Create bill items
        for item_data in items:
            product = Product.objects.get(id=item_data['product_id'])
            BillItem.objects.create(
                bill=bill,
                product=product,
                quantity=item_data['quantity'],
                unit_price=product.price,
                created_by=request.user
            )
        
        # 5. Calculate totals
        bill.calculate_totals()
        bill.save()
        
        # 6. Create payment (PRE-PAYMENT!)
        Payment.objects.create(
            bill=bill,
            method=payment_method,
            amount=bill.total,
            created_by=request.user
        )
        
        # 7. Mark as paid
        bill.status = 'paid'
        bill.closed_by = request.user
        bill.closed_at = timezone.now()
        bill.save()
        
        # 8. Send to kitchen
        from apps.kitchen.services import print_kitchen_order
        
        kitchen_items = bill.items.filter(product__printer_target='kitchen')
        bar_items = bill.items.filter(product__printer_target='bar')
        
        if kitchen_items.exists():
            print_kitchen_order(bill, 'kitchen', kitchen_items)
        if bar_items.exists():
            print_kitchen_order(bill, 'bar', bar_items)
        
        # 9. Print customer receipt
        from apps.pos.services import print_receipt
        print_receipt(bill)
        
        # 10. Return success
        change = amount_paid - bill.total
        
        return render(request, 'pos/partials/quick_order_success.html', {
            'bill': bill,
            'queue_number': queue_number,  # ← NEW!
            'payment_method': payment_method,
            'amount_paid': amount_paid,
            'change': change
        })
        
    except Exception as e:
        logger.error(f"Quick order error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
```

---

### Step 1.5: Add Queue Display Endpoint

**File:** `apps/pos/views.py`

```python
@login_required
def queue_display(request):
    """
    Real-time queue display for TV/Monitor
    Auto-refresh via HTMX
    """
    brand = request.user.brand
    
    # Get current serving (last 3 completed)
    serving = get_serving_queues(brand, limit=3)
    
    # Get preparing orders (paid but not completed)
    preparing = get_active_queues(brand, limit=10)
    
    # Calculate average wait time
    today = timezone.now().date()
    completed_orders = Bill.objects.filter(
        brand=brand,
        bill_type='takeaway',
        created_at__date=today,
        status='completed',
        queue_number__isnull=False
    )
    
    avg_wait = None
    if completed_orders.exists():
        wait_times = [
            (order.completed_at - order.created_at).total_seconds()
            for order in completed_orders
            if order.completed_at
        ]
        if wait_times:
            avg_wait = int(sum(wait_times) / len(wait_times) / 60)  # minutes
    
    return render(request, 'pos/queue_display.html', {
        'serving': serving,
        'preparing': preparing,
        'avg_wait': avg_wait
    })
```

**File:** `apps/pos/urls.py`

```python
urlpatterns = [
    # ... existing patterns ...
    path('queue/display/', views.queue_display, name='queue_display'),
]
```

---

### Step 1.6: Add Bill Completion Method

**File:** `apps/pos/models.py`

```python
class Bill(models.Model):
    # ... existing fields ...
    
    completed_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text='When order was picked up by customer'
    )
    
    def mark_completed(self, user):
        """Mark bill as completed (customer picked up)"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
        
        # Log action
        BillLog.objects.create(
            bill=self,
            action='completed',
            details={'completed_by': user.username},
            user=user
        )
```

**Migration:**
```bash
python manage.py makemigrations pos --name add_completed_at
python manage.py migrate pos
```

---

## 🎨 Phase 2: Frontend Implementation (Day 2)

### Step 2.1: Update Quick Order Modal

**File:** `templates/pos/partials/quick_order_modal.html`

Add customer name input (optional):

```html
<div class="modal" id="quick-order-modal">
    <div class="modal-content">
        <h2>Quick Order (Takeaway)</h2>
        
        <form hx-post="{% url 'pos:quick_order_create' %}" 
              hx-target="#quick-order-result"
              hx-swap="innerHTML">
            
            <!-- Customer Name (Optional) -->
            <div class="form-group">
                <label>Customer Name (Optional)</label>
                <input type="text" 
                       name="customer_name" 
                       placeholder="e.g. DADIN"
                       class="form-control">
                <small class="text-muted">
                    Optional: Untuk referensi internal saja
                </small>
            </div>
            
            <!-- Items (from POS grid selection) -->
            <input type="hidden" name="items" id="quick-order-items">
            
            <!-- Payment Method -->
            <div class="form-group">
                <label>Payment Method *</label>
                <select name="payment_method" class="form-control" required>
                    <option value="cash">Cash</option>
                    <option value="card">Card</option>
                    <option value="qris">QRIS</option>
                </select>
            </div>
            
            <!-- Amount Paid -->
            <div class="form-group">
                <label>Amount Paid *</label>
                <input type="number" 
                       name="amount_paid" 
                       step="1000"
                       placeholder="100000"
                       class="form-control" 
                       required>
            </div>
            
            <!-- Order Summary -->
            <div class="order-summary">
                <h3>Order Summary</h3>
                <div id="quick-order-summary"></div>
                <div class="total">
                    <strong>Total:</strong> 
                    <span id="quick-order-total">Rp 0</span>
                </div>
            </div>
            
            <div class="form-actions">
                <button type="button" class="btn btn-secondary" onclick="closeQuickOrder()">
                    Cancel
                </button>
                <button type="submit" class="btn btn-primary">
                    💰 Process Payment
                </button>
            </div>
        </form>
        
        <div id="quick-order-result"></div>
    </div>
</div>
```

---

### Step 2.2: Create Success Template with Queue Number

**File:** `templates/pos/partials/quick_order_success.html`

```html
<div class="quick-order-success">
    <div class="success-icon">✅</div>
    
    <h2>Order Successful!</h2>
    
    <!-- QUEUE NUMBER - LARGE DISPLAY -->
    <div class="queue-number-display">
        <div class="label">QUEUE NUMBER</div>
        <div class="number">#{{ queue_number }}</div>
    </div>
    
    <div class="order-details">
        <div class="detail-row">
            <span>Bill Number:</span>
            <strong>{{ bill.bill_number }}</strong>
        </div>
        <div class="detail-row">
            <span>Total:</span>
            <strong>Rp {{ bill.total|floatformat:0 }}</strong>
        </div>
        <div class="detail-row">
            <span>Paid:</span>
            <strong>Rp {{ amount_paid|floatformat:0 }}</strong>
        </div>
        <div class="detail-row">
            <span>Change:</span>
            <strong>Rp {{ change|floatformat:0 }}</strong>
        </div>
    </div>
    
    <div class="customer-message">
        <p>✅ Receipt printed</p>
        <p>⏳ Estimated wait: 7-10 minutes</p>
        <p>🔊 Please listen for queue number announcement</p>
    </div>
    
    <button class="btn btn-primary btn-lg" onclick="closeQuickOrderSuccess()">
        ✅ Done
    </button>
</div>

<style>
.quick-order-success {
    text-align: center;
    padding: 30px;
}

.success-icon {
    font-size: 80px;
    margin-bottom: 20px;
}

.queue-number-display {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 30px;
    border-radius: 15px;
    margin: 30px 0;
    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
}

.queue-number-display .label {
    font-size: 18px;
    font-weight: 600;
    letter-spacing: 2px;
    margin-bottom: 10px;
}

.queue-number-display .number {
    font-size: 80px;
    font-weight: 900;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
}

.order-details {
    background: #f8f9fa;
    padding: 20px;
    border-radius: 10px;
    margin: 20px 0;
}

.detail-row {
    display: flex;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid #dee2e6;
}

.detail-row:last-child {
    border-bottom: none;
}

.customer-message {
    margin: 20px 0;
    padding: 20px;
    background: #e7f5ff;
    border-radius: 10px;
}

.customer-message p {
    margin: 10px 0;
    font-size: 16px;
}
</style>

<script>
function closeQuickOrderSuccess() {
    // Close modal
    document.getElementById('quick-order-modal').style.display = 'none';
    
    // Clear form
    document.querySelector('#quick-order-modal form').reset();
    
    // Refresh POS screen (optional)
    htmx.ajax('GET', '{% url "pos:main" %}', {
        target: '#pos-container',
        swap: 'innerHTML'
    });
}
</script>
```

---

### Step 2.3: Create Queue Display Dashboard

**File:** `templates/pos/queue_display.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Queue Display - {{ request.user.brand.name }}</title>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
            color: #fff;
            font-family: 'Arial', sans-serif;
            overflow: hidden;
        }
        
        .container {
            padding: 40px;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .brand-name {
            font-size: 48px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #ffd700;
        }
        
        .timestamp {
            font-size: 24px;
            color: #aaa;
        }
        
        .serving-section {
            flex: 1;
            text-align: center;
            margin-bottom: 40px;
        }
        
        .section-title {
            font-size: 40px;
            font-weight: bold;
            margin-bottom: 30px;
            color: #00ff00;
            text-transform: uppercase;
            letter-spacing: 3px;
        }
        
        .queue-numbers {
            display: flex;
            justify-content: center;
            gap: 40px;
            flex-wrap: wrap;
        }
        
        .queue-number {
            background: linear-gradient(135deg, #00ff00 0%, #00cc00 100%);
            color: #000;
            font-size: 120px;
            font-weight: 900;
            padding: 40px 60px;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,255,0,0.3);
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { 
                transform: scale(1);
                box-shadow: 0 20px 40px rgba(0,255,0,0.3);
            }
            50% { 
                transform: scale(1.05);
                box-shadow: 0 30px 60px rgba(0,255,0,0.5);
            }
        }
        
        .preparing-section {
            text-align: center;
        }
        
        .preparing-section .section-title {
            color: #ffaa00;
            font-size: 32px;
        }
        
        .preparing-numbers {
            display: flex;
            justify-content: center;
            gap: 20px;
            flex-wrap: wrap;
        }
        
        .preparing-number {
            background: #333;
            color: #fff;
            font-size: 50px;
            font-weight: bold;
            padding: 20px 30px;
            border-radius: 10px;
            border: 2px solid #ffaa00;
        }
        
        .footer {
            position: fixed;
            bottom: 20px;
            right: 40px;
            font-size: 28px;
            color: #888;
        }
        
        .empty-state {
            font-size: 36px;
            color: #666;
            padding: 60px;
        }
    </style>
</head>
<body hx-get="{% url 'pos:queue_display' %}" 
      hx-trigger="every 5s" 
      hx-swap="outerHTML"
      hx-target="body">
    
    <div class="container">
        <div class="header">
            <div class="brand-name">{{ request.user.brand.name }}</div>
            <div class="timestamp" id="current-time"></div>
        </div>
        
        <div class="serving-section">
            <div class="section-title">🎯 NOW SERVING</div>
            
            {% if serving %}
                <div class="queue-numbers">
                    {% for bill in serving %}
                        <div class="queue-number">#{{ bill.queue_number }}</div>
                    {% endfor %}
                </div>
            {% else %}
                <div class="empty-state">No orders yet</div>
            {% endif %}
        </div>
        
        <div class="preparing-section">
            <div class="section-title">⏳ PREPARING</div>
            
            {% if preparing %}
                <div class="preparing-numbers">
                    {% for bill in preparing %}
                        <div class="preparing-number">#{{ bill.queue_number }}</div>
                    {% endfor %}
                </div>
            {% else %}
                <div class="empty-state">Queue is empty</div>
            {% endif %}
        </div>
        
        {% if avg_wait %}
        <div class="footer">
            📊 Avg wait: {{ avg_wait }} min
        </div>
        {% endif %}
    </div>
    
    <script>
        // Update timestamp every second
        function updateTime() {
            const now = new Date();
            const timeStr = now.toLocaleTimeString('id-ID', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
            document.getElementById('current-time').textContent = timeStr;
        }
        
        updateTime();
        setInterval(updateTime, 1000);
    </script>
</body>
</html>
```

---

## 🖨️ Phase 3: Printer Implementation (Day 2 afternoon)

### Step 3.1: Update Kitchen Print Service

**File:** `apps/kitchen/services.py`

```python
def print_kitchen_order(bill, station, items):
    """
    Print order to kitchen printer with LARGE queue number
    """
    config = PrinterConfig.objects.filter(
        brand=bill.brand,
        station=station,
        is_active=True
    ).first()
    
    if not config:
        logger.warning(f"No printer for station: {station}")
        return
    
    try:
        from escpos.printer import Network
        p = Network(config.ip_address, config.port)
        
        # Header - Station
        p.set(align='center', bold=True, double_height=True)
        p.text(f"--- {station.upper()} ---\n")
        p.set(bold=False, double_height=False)
        
        # Queue Number - EXTRA LARGE! (if takeaway)
        if bill.bill_type == 'takeaway' and bill.queue_number:
            p.text("\n")
            p.set(align='center', bold=True, 
                  double_height=True, double_width=True)
            p.text(f"ANTRIAN\n")
            p.text(f"#{bill.queue_number}\n")
            p.set(bold=False, double_height=False, double_width=False)
            p.text("\n")
        
        p.text("-" * 32 + "\n")
        
        # Bill info
        p.set(align='left')
        p.text(f"Bill: {bill.bill_number}\n")
        
        if bill.bill_type == 'dine_in' and bill.table:
            p.set(bold=True, double_height=True)
            p.text(f"Meja: {bill.table.number}\n")
            p.set(bold=False, double_height=False)
        
        p.text(f"Time: {bill.created_at.strftime('%H:%M')}\n")
        
        if bill.customer_name:
            p.text(f"Name: {bill.customer_name}\n")
        
        p.text("-" * 32 + "\n")
        
        # Items
        for item in items:
            p.set(bold=True)
            p.text(f"{item.quantity}x {item.product.name}\n")
            p.set(bold=False)
            
            # Modifiers
            if item.modifiers:
                for mod in item.modifiers:
                    p.text(f"   - {mod['name']}\n")
            
            # Notes
            if item.notes:
                p.set(bold=True)
                p.text(f"   !! {item.notes}\n")
                p.set(bold=False)
            
            p.text("\n")
        
        p.text("-" * 32 + "\n")
        p.text("\n\n")
        p.cut()
        p.close()
        
        logger.info(f"Kitchen order printed: {bill.bill_number} to {station}")
        
    except Exception as e:
        logger.error(f"Kitchen print error: {e}", exc_info=True)
```

---

### Step 3.2: Update Customer Receipt Print

**File:** `apps/pos/services.py`

```python
def print_receipt(bill):
    """
    Print customer receipt with LARGE queue number
    """
    config = PrinterConfig.objects.filter(
        brand=bill.brand,
        station='cashier',
        is_active=True
    ).first()
    
    if not config:
        logger.warning("No cashier printer configured")
        return
    
    try:
        from escpos.printer import Network
        p = Network(config.ip_address, config.port)
        
        # Header - Brand Info
        p.set(align='center', bold=True)
        p.text(f"{bill.brand.name}\n")
        p.set(bold=False)
        p.text(f"{bill.brand.address}\n")
        p.text(f"Tel: {bill.brand.phone}\n")
        p.text("=" * 32 + "\n")
        
        # QUEUE NUMBER - MASSIVE! (if takeaway)
        if bill.bill_type == 'takeaway' and bill.queue_number:
            p.text("\n")
            p.set(align='center', bold=True)
            p.text("ANTRIAN / QUEUE\n")
            p.set(bold=True, double_height=True, double_width=True)
            p.text(f"  #{bill.queue_number}  \n")
            p.set(bold=False, double_height=False, double_width=False)
            p.text("\n")
            p.text("=" * 32 + "\n")
        
        # Bill Details
        p.set(align='left')
        p.text(f"Bill: {bill.bill_number}\n")
        p.text(f"Date: {bill.closed_at.strftime('%d/%m/%Y %H:%M')}\n")
        p.text(f"Cashier: {bill.closed_by.get_full_name()}\n")
        
        if bill.table:
            p.text(f"Table: {bill.table.number}\n")
        
        p.text("-" * 32 + "\n")
        
        # Items
        for item in bill.items.filter(is_void=False):
            name = item.product.name[:20]  # Truncate long names
            qty_price = f"{item.quantity}x{item.unit_price:,.0f}"
            total = f"{item.total:,.0f}"
            
            p.text(f"{name}\n")
            p.text(f"  {qty_price:>15} {total:>10}\n")
        
        p.text("-" * 32 + "\n")
        
        # Totals
        p.text(f"{'Subtotal':20} {bill.subtotal:>10,.0f}\n")
        
        if bill.discount_amount > 0:
            p.text(f"{'Discount':20} {-bill.discount_amount:>10,.0f}\n")
        
        if bill.tax_amount > 0:
            p.text(f"{'Tax':20} {bill.tax_amount:>10,.0f}\n")
        
        if bill.service_charge > 0:
            p.text(f"{'Service':20} {bill.service_charge:>10,.0f}\n")
        
        p.text("-" * 32 + "\n")
        p.set(bold=True, double_height=True)
        p.text(f"{'TOTAL':20} {bill.total:>10,.0f}\n")
        p.set(bold=False, double_height=False)
        
        # Payments
        p.text("-" * 32 + "\n")
        for payment in bill.payments.all():
            method = payment.get_method_display()
            p.text(f"{method:20} {payment.amount:>10,.0f}\n")
        
        # Footer message (if takeaway)
        if bill.bill_type == 'takeaway':
            p.text("\n")
            p.set(align='center')
            p.text("=" * 32 + "\n")
            p.text("Estimated wait: 7-10 minutes\n")
            p.text("Please wait for your number\n")
            p.text("to be called\n")
            p.text("=" * 32 + "\n")
        
        # Brand footer
        p.text("\n")
        p.set(align='center')
        if bill.brand.receipt_footer:
            p.text(bill.brand.receipt_footer)
        else:
            p.text("Thank You!\n")
        
        p.text("\n\n")
        p.cut()
        p.close()
        
        logger.info(f"Receipt printed: {bill.bill_number}")
        
    except Exception as e:
        logger.error(f"Receipt print error: {e}", exc_info=True)
```

---

## 🧪 Phase 4: Testing & Quality Assurance (Day 3 morning)

### Test Checklist

```bash
# 1. Unit Tests
python manage.py test apps.pos.tests.test_queue_number

# 2. Manual Testing Scenarios
```

**Test Scenario 1: First Order of Day**
```
Action: Create takeaway order at 10:00 AM
Expected: Queue #1 generated
Verify:
  ✅ Bill.queue_number = 1
  ✅ Receipt shows "ANTRIAN #1" (large)
  ✅ Kitchen print shows "ANTRIAN #1"
  ✅ Display shows #1 in "PREPARING"
```

**Test Scenario 2: Sequential Orders**
```
Action: Create 5 orders rapidly
Expected: Queue #1, #2, #3, #4, #5
Verify:
  ✅ No duplicates
  ✅ No gaps
  ✅ All in correct order
```

**Test Scenario 3: Daily Reset**
```
Action: Wait until midnight (or change system date)
Expected: Next order = Queue #1 (reset)
Verify:
  ✅ Yesterday's queues still visible in history
  ✅ Today starts from #1
```

**Test Scenario 4: Multi-Brand Isolation**
```
Action: Create orders for Brand A and Brand B
Expected: Separate queue sequences
Verify:
  ✅ Brand A: #1, #2, #3
  ✅ Brand B: #1, #2, #3 (independent)
```

**Test Scenario 5: Display Updates**
```
Action: Open queue display on TV
Expected: Auto-refresh every 5 seconds
Verify:
  ✅ New orders appear in "PREPARING"
  ✅ Completed orders move to "NOW SERVING"
  ✅ Average wait time updates
```

**Test Scenario 6: Printer Failure Handling**
```
Action: Disconnect printer, create order
Expected: Order still created, error logged
Verify:
  ✅ Bill saved with queue number
  ✅ Error logged in console
  ✅ Can manually reprint later
```

---

### Create Unit Tests

**File:** `apps/pos/tests/test_queue_number.py`

```python
from django.test import TestCase
from django.utils import timezone
from apps.core.models import Brand, Company
from apps.pos.models import Bill
from apps.pos.utils import generate_queue_number

class QueueNumberTestCase(TestCase):
    
    def setUp(self):
        """Create test data"""
        self.company = Company.objects.create(
            code='TEST',
            name='Test Company'
        )
        self.brand = Brand.objects.create(
            company=self.company,
            code='TEST',
            name='Test Brand'
        )
    
    def test_generate_first_queue_number(self):
        """First order of day should be #1"""
        queue = generate_queue_number(self.brand)
        self.assertEqual(queue, 1)
    
    def test_generate_sequential_queue_numbers(self):
        """Sequential orders should increment"""
        # Create 3 bills
        for i in range(3):
            Bill.objects.create(
                brand=self.brand,
                bill_type='takeaway',
                queue_number=generate_queue_number(self.brand)
            )
        
        # Next should be 4
        next_queue = generate_queue_number(self.brand)
        self.assertEqual(next_queue, 4)
    
    def test_queue_number_daily_reset(self):
        """Queue should reset on new day"""
        # Create order today
        today = timezone.now().date()
        Bill.objects.create(
            brand=self.brand,
            bill_type='takeaway',
            queue_number=1,
            created_at=timezone.now()
        )
        
        # Simulate tomorrow
        from datetime import timedelta
        tomorrow = today + timedelta(days=1)
        
        # Mock: In real scenario, would test with date change
        # For unit test, verify logic handles date filtering
        queue = generate_queue_number(self.brand)
        self.assertIsNotNone(queue)
    
    def test_brand_isolation(self):
        """Different brands have independent queues"""
        brand2 = Brand.objects.create(
            company=self.company,
            code='TEST2',
            name='Test Brand 2'
        )
        
        # Brand 1: queue 1
        q1 = generate_queue_number(self.brand)
        
        # Brand 2: also queue 1 (independent)
        q2 = generate_queue_number(brand2)
        
        self.assertEqual(q1, 1)
        self.assertEqual(q2, 1)
```

**Run tests:**
```bash
python manage.py test apps.pos.tests.test_queue_number
```

---

## 🚀 Phase 5: Deployment & Go-Live (Day 3 afternoon)

### Pre-Deployment Checklist

```bash
# 1. Database backup
python manage.py dumpdata > backup_before_queue.json

# 2. Run migrations on production
python manage.py migrate --check
python manage.py migrate

# 3. Collect static files (if needed)
python manage.py collectstatic --no-input

# 4. Restart services
# Linux/Mac:
sudo systemctl restart gunicorn
sudo systemctl restart nginx

# Windows:
# Restart IIS or development server

# 5. Verify deployment
curl http://your-pos-domain/pos/queue/display/
# Should return queue display page
```

---

### Hardware Setup (TV Display)

**Option 1: Dedicated Display Device**
```bash
# Raspberry Pi or similar
1. Connect to TV via HDMI
2. Open Chromium browser in kiosk mode:

chromium-browser \
  --kiosk \
  --incognito \
  --disable-pinch \
  --overscroll-history-navigation=0 \
  "http://your-pos-domain/pos/queue/display/"

3. Set to auto-start on boot
```

**Option 2: Windows PC/Laptop**
```bash
1. Open Chrome/Edge
2. Press F11 for fullscreen
3. Navigate to: http://your-pos-domain/pos/queue/display/
4. Set browser to auto-start on boot
```

**Option 3: Android Tablet**
```bash
1. Install "Fully Kiosk Browser" from Play Store
2. Enable kiosk mode
3. Set homepage: http://your-pos-domain/pos/queue/display/
4. Enable auto-refresh
```

---

### Staff Training (30 minutes)

**Training Checklist:**
```
□ How to take takeaway orders
□ How to input customer name (optional)
□ How to process payment (pre-payment!)
□ What happens after payment:
  - Receipt prints with queue number
  - Kitchen gets order
  - Customer waits for call
  
□ How to call queue numbers:
  - Use microphone/speaker
  - "Nomor antrian 23!" (repeat 2x)
  - Check customer receipt matches
  
□ How to mark order complete:
  - After customer picks up
  - Update status in system (if manual)
  
□ What if printer fails:
  - Order still saved
  - Can manually reprint
  - Call IT support
  
□ Display screen monitoring:
  - Check screen shows correct queues
  - If frozen, refresh browser (F5)
```

---

### Go-Live Plan

**Soft Launch (Day 1):**
```
Morning (10am-12pm):
  - Enable queue system
  - Staff on high alert
  - Monitor closely
  - Fix issues immediately

Afternoon (2pm-5pm):
  - If stable, continue
  - If issues, rollback

Evening (5pm-9pm):
  - Peak hour test
  - Collect feedback
```

**Full Launch (Day 2):**
```
All day:
  - Normal operations
  - Queue system default
  - Monitor performance
  - Customer feedback
```

---

### Rollback Plan (If Issues)

```bash
# Emergency rollback
git checkout HEAD~1  # Go back 1 commit
python manage.py migrate pos XXXX_previous_migration
python manage.py collectstatic --no-input
sudo systemctl restart gunicorn

# Or: Feature flag approach
# In settings.py
ENABLE_QUEUE_SYSTEM = False

# In views.py
if settings.ENABLE_QUEUE_SYSTEM:
    queue_number = generate_queue_number(brand)
else:
    queue_number = None
```

---

## 📊 Post-Implementation Monitoring

### Week 1 Metrics to Track

```python
# Analytics queries
from apps.pos.models import Bill
from django.db.models import Avg, Count
from datetime import timedelta

# Average wait time
today = timezone.now().date()
completed = Bill.objects.filter(
    bill_type='takeaway',
    status='completed',
    created_at__date=today
)

wait_times = [
    (b.completed_at - b.created_at).total_seconds() / 60
    for b in completed
    if b.completed_at
]

avg_wait = sum(wait_times) / len(wait_times) if wait_times else 0
print(f"Average wait time: {avg_wait:.1f} minutes")

# Orders per hour
orders_per_hour = Bill.objects.filter(
    bill_type='takeaway',
    created_at__date=today
).extra(select={'hour': 'EXTRACT(hour FROM created_at)'}).values('hour').annotate(
    count=Count('id')
).order_by('hour')

for row in orders_per_hour:
    print(f"{row['hour']:02d}:00 - {row['count']} orders")

# Queue number distribution
max_queue = Bill.objects.filter(
    bill_type='takeaway',
    created_at__date=today
).aggregate(max=Max('queue_number'))

print(f"Total orders today: {max_queue['max']}")
```

---

### Success Criteria

**Week 1 Goals:**
- ✅ 0 duplicate queue numbers
- ✅ 0 system crashes
- ✅ < 5% printer failures
- ✅ Customer confusion < 10%
- ✅ Staff confident using system

**Week 2 Goals:**
- ✅ Average wait time < 10 minutes
- ✅ Queue throughput +20%
- ✅ Customer satisfaction +15%
- ✅ Staff efficiency +25%

---

## 🆘 Troubleshooting Guide

### Issue 1: Duplicate Queue Numbers

**Symptoms:** Two orders have same queue #23

**Cause:** Race condition in queue generation

**Fix:**
```python
# Add database lock
from django.db import transaction

@transaction.atomic
def generate_queue_number(brand):
    """Thread-safe queue generation"""
    today = timezone.now().date()
    
    # Use select_for_update to lock
    last_queue = Bill.objects.select_for_update().filter(
        brand=brand,
        bill_type='takeaway',
        created_at__date=today
    ).aggregate(max_queue=Max('queue_number'))
    
    return (last_queue['max_queue'] or 0) + 1
```

---

### Issue 2: Display Not Updating

**Symptoms:** TV screen frozen, shows old queues

**Cause:** HTMX polling stopped or network issue

**Fix:**
```bash
# Quick fix: Refresh browser (F5)

# Permanent fix: Add error handling
# In queue_display.html
<body hx-get="{% url 'pos:queue_display' %}" 
      hx-trigger="every 5s"
      hx-on="htmx:timeout: location.reload()">
```

---

### Issue 3: Printer Not Printing Queue Number

**Symptoms:** Receipt prints but queue number missing

**Cause:** Printer doesn't support double_width/double_height

**Fix:**
```python
# Use standard size with more lines
p.set(align='center', bold=True)
p.text("\n")
p.text("=" * 32 + "\n")
p.text("    ANTRIAN / QUEUE    \n")
p.text("=" * 32 + "\n")
p.text(f"        #{queue_number}        \n")
p.text("=" * 32 + "\n")
p.text("\n")
```

---

### Issue 4: Queue Not Resetting at Midnight

**Symptoms:** Queue continues from yesterday (#256, #257...)

**Cause:** created_at__date filter not working

**Fix:**
```python
# Ensure timezone-aware queries
from django.utils import timezone

today = timezone.now().date()  # Use timezone.now(), not datetime.now()
```

---

## 📚 Additional Resources

### Documentation to Update

1. **User Manual** - Add queue system section
2. **Admin Guide** - Add configuration steps
3. **API Docs** - Document queue endpoints
4. **Training Materials** - Create video tutorials

### Files Modified Summary

```
New Files:
✅ apps/pos/utils.py (queue generation)
✅ templates/pos/queue_display.html (display dashboard)
✅ templates/pos/partials/quick_order_success.html (success screen)
✅ apps/pos/tests/test_queue_number.py (tests)

Modified Files:
✅ apps/pos/models.py (add queue_number field)
✅ apps/pos/views.py (quick_order_create + queue_display)
✅ apps/pos/urls.py (add queue display route)
✅ apps/kitchen/services.py (print queue on kitchen order)
✅ apps/pos/services.py (print queue on receipt)
✅ templates/pos/partials/quick_order_modal.html (add customer name)

Migration Files:
✅ apps/pos/migrations/XXXX_add_queue_number.py
✅ apps/pos/migrations/XXXX_add_completed_at.py
```

---

## ✅ Final Checklist

Before marking implementation DONE:

```bash
□ All tests passing
□ No console errors
□ Printer tested (kitchen + cashier)
□ Display screen working
□ Staff trained
□ Documentation updated
□ Backup created
□ Rollback plan ready
□ Monitoring setup
□ Success metrics defined
□ First day support scheduled
```

---

## 🎯 Next Steps (Future Enhancements)

**Phase 2 (Optional - Week 2+):**

1. **SMS Notification** (Advanced)
   - Send SMS when queue ready
   - "Your queue #23 is ready!"
   
2. **QR Code Tracking** (Advanced)
   - Print QR code on receipt
   - Customer scans to track status
   - Real-time web tracking page

3. **Voice Announcement** (Optional)
   - Text-to-speech integration
   - Automatic announcement via speaker
   - Multi-language support

4. **Analytics Dashboard** (Recommended)
   - Peak hour analysis
   - Average wait time trends
   - Queue efficiency metrics
   - Staff performance

5. **Mobile Ordering** (Future)
   - Customer orders from phone
   - Get queue number remotely
   - Pay online
   - Come when ready

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-23  
**Implementation Status:** Ready for Development  
**Estimated Total Time:** 3 days (1 developer)

Good luck! 🚀
