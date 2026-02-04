# 🖨️ Kitchen Printer System - Database Schema Documentation

**Last Updated:** February 4, 2026  
**Status:** ✅ Production Ready  
**Version:** 1.0

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Core Tables](#core-tables)
3. [Monitoring & Audit Tables](#monitoring--audit-tables)
4. [Data Flow & Relationships](#data-flow--relationships)
5. [Indexes & Performance](#indexes--performance)
6. [Usage Examples](#usage-examples)
7. [Best Practices](#best-practices)

---

## Overview

Kitchen Printer System adalah solusi **stateless, idempotent, production-ready** untuk routing order items ke kitchen printers berdasarkan station (BAR, KITCHEN, DESSERT, etc).

### Architecture Principles

✅ **POS NEVER prints directly**  
✅ **Database is source of truth**  
✅ **Printing is auditable & reprintable**  
✅ **Printers are unreliable - system must handle failures**  
✅ **One ticket per station per order**

---

## Core Tables

### 1. `kitchen_stationprinter`

**Purpose:** Configuration table mapping station codes to physical printer IPs

```sql
CREATE TABLE kitchen_stationprinter (
    id                  BIGSERIAL PRIMARY KEY,
    brand_id            UUID NOT NULL REFERENCES core_brand(id),
    station_code        VARCHAR(50) NOT NULL,  -- 'kitchen', 'bar', 'dessert', etc.
    printer_name        VARCHAR(100) NOT NULL,
    printer_ip          INET NOT NULL,
    printer_port        INTEGER DEFAULT 9100,
    priority            INTEGER DEFAULT 1,      -- 1=primary, 2=backup
    is_active           BOOLEAN DEFAULT TRUE,
    
    -- Printer Specs
    paper_width_mm      INTEGER DEFAULT 80,
    chars_per_line      INTEGER DEFAULT 32,
    
    -- Statistics
    last_print_at       TIMESTAMP WITH TIME ZONE,
    last_error_at       TIMESTAMP WITH TIME ZONE,
    last_error_message  TEXT,
    total_prints        INTEGER DEFAULT 0,
    failed_prints       INTEGER DEFAULT 0,
    
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_station_code_active_priority 
    ON kitchen_stationprinter(station_code, is_active, priority);
CREATE INDEX idx_brand_station 
    ON kitchen_stationprinter(brand_id, station_code);
```

**Key Fields:**
- `station_code`: Matches `pos_billitem.printer_target`
- `priority`: Lower number = higher priority (for backup printers)
- `is_active`: Enable/disable printer without deleting config

**Example Data:**
```sql
INSERT INTO kitchen_stationprinter (brand_id, station_code, printer_name, printer_ip, priority, is_active)
VALUES 
    ('uuid-ayam-geprek', 'kitchen', 'Main Kitchen Printer', '192.168.1.100', 1, true),
    ('uuid-ayam-geprek', 'kitchen', 'Backup Kitchen Printer', '192.168.1.101', 2, true),
    ('uuid-ayam-geprek', 'bar', 'Bar Printer', '192.168.1.102', 1, true),
    ('uuid-ayam-geprek', 'dessert', 'Dessert Station Printer', '192.168.1.103', 1, true);
```

---

### 2. `kitchen_kitchenticket`

**Purpose:** Print jobs - one ticket per station per order

```sql
CREATE TABLE kitchen_kitchenticket (
    id                  BIGSERIAL PRIMARY KEY,
    bill_id             BIGINT NOT NULL REFERENCES pos_bill(id),
    printer_target      VARCHAR(50) NOT NULL,   -- Station code
    status              VARCHAR(20) NOT NULL,   -- 'new', 'printing', 'printed', 'failed'
    
    -- Retry Mechanism
    print_attempts      INTEGER DEFAULT 0,
    max_retries         INTEGER DEFAULT 3,
    
    -- Printer Info
    printer_ip          INET,                   -- Which printer processed this
    
    -- Error Tracking
    error_message       TEXT,
    last_error_at       TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    printed_at          TIMESTAMP WITH TIME ZONE,
    
    -- Reprint Support
    is_reprint          BOOLEAN DEFAULT FALSE,
    original_ticket_id  BIGINT REFERENCES kitchen_kitchenticket(id)
);

CREATE INDEX idx_status_created ON kitchen_kitchenticket(status, created_at);
CREATE INDEX idx_bill_target ON kitchen_kitchenticket(bill_id, printer_target);
CREATE INDEX idx_target_status ON kitchen_kitchenticket(printer_target, status);
CREATE INDEX idx_created ON kitchen_kitchenticket(created_at);
```

**Status Flow:**
```
new → printing → printed ✅
new → printing → failed → new (retry)
printed → new (reprint with is_reprint=true)
```

**Key Methods:**
```python
# Mark as printing
ticket.mark_printing(printer_ip='192.168.1.100')

# Mark success
ticket.mark_printed()

# Mark failed
ticket.mark_failed(error_message='Connection timeout')

# Check if can retry
if ticket.can_retry():
    ticket.status = 'new'
    ticket.save()
```

**Example Query - Get pending tickets:**
```sql
SELECT * FROM kitchen_kitchenticket
WHERE status = 'new'
  AND print_attempts < max_retries
ORDER BY created_at ASC
LIMIT 10;
```

---

### 3. `kitchen_kitchenticketitem`

**Purpose:** Junction table linking tickets to bill items

```sql
CREATE TABLE kitchen_kitchenticketitem (
    id                  BIGSERIAL PRIMARY KEY,
    kitchen_ticket_id   BIGINT NOT NULL REFERENCES kitchen_kitchenticket(id),
    bill_item_id        BIGINT NOT NULL REFERENCES pos_billitem(id),
    quantity            INTEGER NOT NULL
);

CREATE INDEX idx_ticket_item ON kitchen_kitchenticketitem(kitchen_ticket_id, bill_item_id);
```

**Why Separate Table?**
- Supports partial reprints (reprint specific items only)
- Allows quantity adjustment without modifying original order
- Clean separation of concerns

**Example - Get all items for a ticket:**
```sql
SELECT 
    kti.quantity,
    bi.product_id,
    p.name AS product_name,
    bi.notes,
    bi.modifiers
FROM kitchen_kitchenticketitem kti
JOIN pos_billitem bi ON kti.bill_item_id = bi.id
JOIN core_product p ON bi.product_id = p.id
WHERE kti.kitchen_ticket_id = 123;
```

---

## Monitoring & Audit Tables

### 4. `kitchen_kitchenticketlog`

**Purpose:** 🔒 **Immutable audit trail** - logs ALL state changes

```sql
CREATE TABLE kitchen_kitchenticketlog (
    id                  BIGSERIAL PRIMARY KEY,
    ticket_id           BIGINT NOT NULL REFERENCES kitchen_kitchenticket(id),
    timestamp           TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- State Change
    old_status          VARCHAR(20),
    new_status          VARCHAR(20) NOT NULL,
    
    -- Action Context
    action              VARCHAR(50) NOT NULL,   -- 'created', 'print_start', 'print_success', etc.
    actor               VARCHAR(100) NOT NULL,  -- 'printer_service', 'admin:username', 'system'
    
    -- Technical Details
    printer_ip          INET,
    error_code          VARCHAR(50),
    error_message       TEXT,
    duration_ms         INTEGER,                -- Action duration for SLA tracking
    
    -- Flexible Context
    metadata            JSONB DEFAULT '{}'
);

CREATE INDEX idx_ticket_timestamp ON kitchen_kitchenticketlog(ticket_id, timestamp DESC);
CREATE INDEX idx_action_timestamp ON kitchen_kitchenticketlog(action, timestamp DESC);
CREATE INDEX idx_timestamp ON kitchen_kitchenticketlog(timestamp DESC);
```

**Action Types:**
- `created` - Ticket created from order
- `print_start` - Printer service picked up ticket
- `print_success` - Successfully printed
- `print_failed` - Print failed with error
- `retry` - Retry attempt
- `manual_reset` - Admin reset to NEW
- `marked_printed` - Admin manually marked as printed
- `marked_failed` - Admin manually marked as failed

**Usage Example:**
```python
# Helper method
KitchenTicketLog.log_action(
    ticket=ticket,
    action='print_success',
    actor='printer_service',
    old_status='printing',
    new_status='printed',
    printer_ip='192.168.1.100',
    duration_ms=1234,
    metadata={'retry_count': 0, 'items_count': 5}
)
```

**Critical Features:**
- ✅ **Immutable** - Cannot be modified or deleted (compliance)
- ✅ **Complete history** - Every state change logged
- ✅ **Performance tracking** - `duration_ms` for SLA analysis
- ✅ **Debugging** - Full context of what happened when

**Query Examples:**

```sql
-- Debug: Why did ticket fail?
SELECT * FROM kitchen_kitchenticketlog
WHERE ticket_id = 123
ORDER BY timestamp;

-- SLA: Average print time
SELECT AVG(duration_ms) AS avg_print_time_ms
FROM kitchen_kitchenticketlog
WHERE action = 'print_success'
  AND timestamp > NOW() - INTERVAL '1 day';

-- Audit: Who reprinted tickets today?
SELECT ticket_id, actor, timestamp
FROM kitchen_kitchenticketlog
WHERE action = 'manual_reset'
  AND timestamp::date = CURRENT_DATE;
```

---

### 5. `kitchen_printerhealthcheck`

**Purpose:** 📊 **Proactive monitoring** - periodic health checks

```sql
CREATE TABLE kitchen_printerhealthcheck (
    id                  BIGSERIAL PRIMARY KEY,
    printer_id          BIGINT NOT NULL REFERENCES kitchen_stationprinter(id),
    checked_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Connection Status
    is_online           BOOLEAN NOT NULL,
    response_time_ms    INTEGER,
    
    -- Printer Status
    paper_status        VARCHAR(20) DEFAULT 'unknown',  -- 'ok', 'low', 'out', 'jam'
    
    -- Error Details
    error_code          VARCHAR(50),
    error_message       TEXT,
    
    -- Hardware Diagnostics (optional)
    temperature_ok      BOOLEAN,
    cutter_ok           BOOLEAN
);

CREATE INDEX idx_printer_checked ON kitchen_printerhealthcheck(printer_id, checked_at DESC);
CREATE INDEX idx_checked ON kitchen_printerhealthcheck(checked_at DESC);
CREATE INDEX idx_online_checked ON kitchen_printerhealthcheck(is_online, checked_at DESC);
```

**Usage Example:**
```python
# Run health check
health = PrinterHealthCheck.check_printer(printer)

if health.is_healthy():
    print("✅ Printer ready")
else:
    if not health.is_online:
        alert("🔴 Printer offline!")
    elif health.paper_status == 'out':
        alert("📄 Paper out!")
```

**Monitoring Queries:**

```sql
-- Get latest status for all printers
SELECT DISTINCT ON (printer_id)
    printer_id,
    is_online,
    response_time_ms,
    paper_status,
    checked_at
FROM kitchen_printerhealthcheck
ORDER BY printer_id, checked_at DESC;

-- Find printers offline for >5 minutes
SELECT 
    sp.station_code,
    sp.printer_name,
    sp.printer_ip,
    phc.checked_at,
    NOW() - phc.checked_at AS downtime
FROM kitchen_printerhealthcheck phc
JOIN kitchen_stationprinter sp ON phc.printer_id = sp.id
WHERE phc.is_online = FALSE
  AND phc.checked_at > NOW() - INTERVAL '10 minutes'
  AND NOT EXISTS (
      SELECT 1 FROM kitchen_printerhealthcheck phc2
      WHERE phc2.printer_id = phc.printer_id
        AND phc2.is_online = TRUE
        AND phc2.checked_at > phc.checked_at
  );

-- Uptime report (last 7 days)
SELECT 
    sp.station_code,
    sp.printer_name,
    COUNT(*) AS total_checks,
    SUM(CASE WHEN is_online THEN 1 ELSE 0 END) AS online_checks,
    ROUND(100.0 * SUM(CASE WHEN is_online THEN 1 ELSE 0 END) / COUNT(*), 2) AS uptime_percent
FROM kitchen_printerhealthcheck phc
JOIN kitchen_stationprinter sp ON phc.printer_id = sp.id
WHERE checked_at > NOW() - INTERVAL '7 days'
GROUP BY sp.id, sp.station_code, sp.printer_name;
```

---

## Data Flow & Relationships

### Entity Relationship Diagram

```
┌─────────────────┐
│  core_brand     │
└────────┬────────┘
         │
         ├──────────────────────────────────────┐
         │                                      │
         ▼                                      ▼
┌─────────────────────┐              ┌──────────────────────┐
│ kitchen_station     │              │  core_product        │
│     printer         │              │  .printer_target     │
└──────────┬──────────┘              └──────────┬───────────┘
           │                                    │
           │                                    ▼
           │                         ┌──────────────────────┐
           │                         │   pos_billitem       │
           │                         │   .printer_target    │
           │                         └──────────┬───────────┘
           │                                    │
           ▼                                    │
┌──────────────────────┐                       │
│ kitchen_printer      │                       │
│   healthcheck        │                       │
└──────────────────────┘                       │
                                               │
           ┌───────────────────────────────────┘
           │
           ▼
┌──────────────────────┐
│   pos_bill           │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ kitchen_kitchen      │
│      ticket          │◄────────────┐
└──────────┬───────────┘             │
           │                         │ (reprint)
           ├──────────────────┐      │
           │                  │      │
           ▼                  ▼      │
┌──────────────────┐  ┌──────────────────────┐
│ kitchen_kitchen  │  │ kitchen_kitchen      │
│   ticketitem     │  │    ticketlog         │
└──────────────────┘  └──────────────────────┘
```

---

### Complete Workflow

#### Step 1: Order Placed in POS

```python
# User adds items to bill
bill = Bill.objects.create(...)
for item_data in cart:
    product = Product.objects.get(id=item_data['product_id'])
    BillItem.objects.create(
        bill=bill,
        product=product,
        quantity=item_data['quantity'],
        printer_target=product.printer_target  # ← 'kitchen', 'bar', 'dessert'
    )
```

#### Step 2: Send to Kitchen (Create Tickets)

```python
# Service groups items by printer_target
from apps.kitchen.services import create_kitchen_tickets

tickets = create_kitchen_tickets(bill)
# Creates 1 ticket per unique printer_target
# e.g., 3 tickets if order has kitchen + bar + dessert items
```

#### Step 3: Printer Service Polls & Prints

```python
# Printer service (standalone Python script)
tickets = KitchenTicket.objects.filter(status='new').order_by('created_at')[:10]

for ticket in tickets:
    # Get printer for this station
    printer = StationPrinter.objects.filter(
        station_code=ticket.printer_target,
        is_active=True
    ).order_by('priority').first()
    
    # Mark as printing
    ticket.mark_printing(printer.printer_ip)
    KitchenTicketLog.log_action(ticket, 'print_start', 'printer_service')
    
    try:
        # Print via ESC/POS
        print_escpos(printer, ticket)
        
        # Success
        ticket.mark_printed()
        KitchenTicketLog.log_action(ticket, 'print_success', 'printer_service', duration_ms=1200)
        
        printer.total_prints += 1
        printer.last_print_at = timezone.now()
        printer.save()
        
    except Exception as e:
        # Failed
        ticket.mark_failed(str(e))
        KitchenTicketLog.log_action(ticket, 'print_failed', 'printer_service', error_message=str(e))
        
        printer.failed_prints += 1
        printer.save()
```

---

## Indexes & Performance

### Query Performance Optimization

**Most Common Queries:**

1. **Get pending tickets** (runs every 5-10 seconds)
```sql
SELECT * FROM kitchen_kitchenticket
WHERE status = 'new' 
ORDER BY created_at 
LIMIT 10;
-- Uses: idx_status_created
```

2. **Get printers for station**
```sql
SELECT * FROM kitchen_stationprinter
WHERE station_code = 'kitchen' 
  AND is_active = true
ORDER BY priority;
-- Uses: idx_station_code_active_priority
```

3. **Ticket history for debugging**
```sql
SELECT * FROM kitchen_kitchenticketlog
WHERE ticket_id = 123
ORDER BY timestamp DESC;
-- Uses: idx_ticket_timestamp
```

4. **Latest printer health**
```sql
SELECT DISTINCT ON (printer_id) *
FROM kitchen_printerhealthcheck
ORDER BY printer_id, checked_at DESC;
-- Uses: idx_printer_checked
```

---

## Usage Examples

### Example 1: Create Tickets from Order

```python
from django.db import transaction
from apps.kitchen.models import KitchenTicket, KitchenTicketItem, KitchenTicketLog

@transaction.atomic
def create_kitchen_tickets(bill):
    """
    Group bill items by printer_target and create tickets
    """
    # Group items by printer_target
    items_by_station = {}
    for item in bill.items.filter(is_void=False, printer_target__isnull=False).exclude(printer_target='none'):
        station = item.printer_target or 'kitchen'
        if station not in items_by_station:
            items_by_station[station] = []
        items_by_station[station].append(item)
    
    tickets = []
    
    # Create 1 ticket per station
    for station_code, items in items_by_station.items():
        ticket = KitchenTicket.objects.create(
            bill=bill,
            printer_target=station_code,
            status='new'
        )
        
        # Add items to ticket
        for item in items:
            KitchenTicketItem.objects.create(
                kitchen_ticket=ticket,
                bill_item=item,
                quantity=item.quantity
            )
        
        # Log creation
        KitchenTicketLog.log_action(
            ticket=ticket,
            action='created',
            actor='system',
            new_status='new',
            metadata={'items_count': len(items)}
        )
        
        tickets.append(ticket)
    
    return tickets
```

### Example 2: Health Check Celery Task

```python
from celery import shared_task
from apps.kitchen.models import StationPrinter, PrinterHealthCheck

@shared_task
def check_all_printers():
    """Run health check on all active printers"""
    printers = StationPrinter.objects.filter(is_active=True)
    
    results = {
        'checked': 0,
        'online': 0,
        'offline': 0,
        'errors': []
    }
    
    for printer in printers:
        try:
            health = PrinterHealthCheck.check_printer(printer)
            results['checked'] += 1
            
            if health.is_online:
                results['online'] += 1
            else:
                results['offline'] += 1
                results['errors'].append({
                    'printer': printer.printer_name,
                    'error': health.error_message
                })
        except Exception as e:
            results['errors'].append({
                'printer': printer.printer_name,
                'error': str(e)
            })
    
    return results

# Schedule in celery beat (every 5 minutes)
# CELERY_BEAT_SCHEDULE = {
#     'check-printers': {
#         'task': 'apps.kitchen.tasks.check_all_printers',
#         'schedule': crontab(minute='*/5'),
#     },
# }
```

### Example 3: Admin Reprint Action

```python
# In admin.py
def reprint_tickets(self, request, queryset):
    """Create reprint tickets"""
    reprinted = 0
    
    for original_ticket in queryset:
        # Create new ticket as reprint
        new_ticket = KitchenTicket.objects.create(
            bill=original_ticket.bill,
            printer_target=original_ticket.printer_target,
            status='new',
            is_reprint=True,
            original_ticket=original_ticket
        )
        
        # Copy items
        for item in original_ticket.items.all():
            KitchenTicketItem.objects.create(
                kitchen_ticket=new_ticket,
                bill_item=item.bill_item,
                quantity=item.quantity
            )
        
        # Log reprint
        KitchenTicketLog.log_action(
            ticket=new_ticket,
            action='created',
            actor=f'admin:{request.user.username}',
            new_status='new',
            metadata={'reprint_of': original_ticket.id}
        )
        
        reprinted += 1
    
    self.message_user(request, f"Created {reprinted} reprint ticket(s)")

reprint_tickets.short_description = "🔄 Reprint Selected Tickets"
```

---

## Best Practices

### ✅ DO's

1. **Always log state changes**
   ```python
   ticket.status = 'printed'
   ticket.save()
   KitchenTicketLog.log_action(ticket, 'print_success', 'printer_service')
   ```

2. **Use transactions for ticket creation**
   ```python
   @transaction.atomic
   def create_kitchen_tickets(bill):
       # All or nothing
   ```

3. **Check health before printing**
   ```python
   printer = get_printer_for_station(station_code)
   health = printer.health_checks.order_by('-checked_at').first()
   if health and not health.is_online:
       try_backup_printer()
   ```

4. **Handle printer failures gracefully**
   ```python
   if ticket.can_retry():
       ticket.status = 'new'  # Will be retried
   else:
       alert_manager(ticket)  # Max retries reached
   ```

5. **Use metadata for debugging context**
   ```python
   KitchenTicketLog.log_action(
       ticket, 'print_failed', 'printer_service',
       error_message=str(e),
       metadata={'retry_count': ticket.print_attempts, 'network_latency_ms': 500}
   )
   ```

### ❌ DON'Ts

1. **Never print inside POS request**
   ```python
   # ❌ WRONG
   def add_item(request):
       item = BillItem.objects.create(...)
       print_to_kitchen(item)  # Blocks user!
   
   # ✅ CORRECT
   def add_item(request):
       item = BillItem.objects.create(...)
       # Printer service will poll and print
   ```

2. **Never skip audit logging**
   ```python
   # ❌ WRONG
   ticket.status = 'printed'
   ticket.save()  # No log!
   
   # ✅ CORRECT
   ticket.mark_printed()
   KitchenTicketLog.log_action(...)
   ```

3. **Never delete audit logs**
   ```python
   # ❌ NEVER DO THIS
   KitchenTicketLog.objects.filter(ticket=ticket).delete()
   ```

4. **Never assume printer is online**
   ```python
   # ❌ WRONG
   printer = StationPrinter.objects.first()
   print_to_printer(printer)  # May be offline!
   
   # ✅ CORRECT
   printer = get_active_printer_for_station(station_code)
   if not printer:
       log_error("No active printer for {station_code}")
       return
   ```

---

## Migration History

| Migration | Date | Description |
|-----------|------|-------------|
| `0002_add_kitchen_printer_models` | 2026-02-04 | Added KitchenTicket, KitchenTicketItem, StationPrinter |
| `0003_add_audit_and_monitoring` | 2026-02-04 | Added KitchenTicketLog, PrinterHealthCheck |

---

## Future Enhancements

### Phase 2 (Post-MVP)

1. **BillKitchenStatus** - Aggregate status per bill for UI
2. **KitchenTicketBatch** - Batch printing for high-volume scenarios
3. **PrintTemplate** - Custom print layouts per station/brand
4. **StationPrinterSchedule** - Planned maintenance windows

### Phase 3 (Scale)

1. **Multi-location support** - Add `store_id` to models
2. **Queue system** - Redis/RabbitMQ for >200 orders/hour
3. **Real-time alerts** - WebSocket notifications for failures
4. **Advanced analytics** - ML-based failure prediction

---

## Support & Troubleshooting

### Common Issues

**Problem: Tickets stuck in 'printing' status**
```sql
-- Find stuck tickets (printing > 5 minutes)
SELECT * FROM kitchen_kitchenticket
WHERE status = 'printing'
  AND created_at < NOW() - INTERVAL '5 minutes';

-- Reset to NEW for retry
UPDATE kitchen_kitchenticket
SET status = 'new', printer_ip = NULL
WHERE status = 'printing'
  AND created_at < NOW() - INTERVAL '5 minutes';
```

**Problem: Printer offline but tickets still queued**
```sql
-- Find tickets for offline printer
SELECT kt.* 
FROM kitchen_kitchenticket kt
JOIN kitchen_stationprinter sp ON kt.printer_target = sp.station_code
WHERE kt.status = 'new'
  AND sp.is_active = FALSE;

-- Option 1: Wait for admin to fix printer
-- Option 2: Reroute to backup printer (manual intervention)
```

**Problem: High failure rate**
```sql
-- Get failure rate per printer
SELECT 
    sp.printer_name,
    sp.total_prints,
    sp.failed_prints,
    ROUND(100.0 * sp.failed_prints / NULLIF(sp.total_prints, 0), 2) AS failure_rate
FROM kitchen_stationprinter sp
WHERE sp.total_prints > 0
ORDER BY failure_rate DESC;
```

---

## Contact & References

- **Architecture Doc:** `KITCHEN_PRINTER_PROMPT.md`
- **API Spec:** TBD (next phase)
- **Printer Service:** TBD (next phase)

---

**🎯 This schema is production-ready for Kitchen Printer Service implementation.**
