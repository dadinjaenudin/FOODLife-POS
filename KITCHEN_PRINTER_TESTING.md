# Kitchen Printer System - Testing Guide

## System Overview

The Kitchen Printer System is now integrated into the POS. When you click "Send to Kitchen", the system creates kitchen tickets that will be picked up by the printer service.

## Current Setup Status

✅ **Database Tables Created:**
- `kitchen_stationprinter` - Printer routing configuration (4 printers configured)
- `kitchen_kitchenticket` - Print jobs (one per station per order)
- `kitchen_kitchenitemticket` - Junction table linking tickets to bill items
- `kitchen_kitchenlog` - Audit trail for all ticket state changes
- `kitchen_printerhealthcheck` - Printer health monitoring

✅ **Printers Configured:**
- KITCHEN → 192.168.1.101:9100 (priority 1 - primary)
- KITCHEN → 192.168.1.111:9100 (priority 2 - backup)
- BAR → 192.168.1.102:9100
- DESSERT → 192.168.1.103:9100

✅ **Products:**
- 143 products have `printer_target='kitchen'` configured
- Ready to route to appropriate stations

✅ **POS Integration:**
- "Send to Kitchen" button calls new ticket creation system
- Automatically groups items by `printer_target`
- Creates one ticket per station

---

## Testing Flow

### Step 1: Access POS System
```
URL: http://localhost:8001/pos/
Login with your credentials
```

### Step 2: Create a New Bill
1. Click "New Bill" or select a table
2. Add items to the bill
3. Items should automatically have `printer_target` populated

### Step 3: Send to Kitchen
1. Look for "Send to Kitchen" button in the bill panel
2. It should show a badge with the number of pending items (e.g., "3")
3. Click the button
4. Expected result:
   - Success notification: "✓ Berhasil kirim X item ke Y station"
   - Items change status from `pending` → `sent`
   - Kitchen tickets created in database

### Step 4: Verify in Database

**Check tickets created:**
```bash
docker exec fnb_edge_web python manage.py shell -c "
from apps.kitchen.models import KitchenTicket, KitchenTicketItem
print(f'Total tickets: {KitchenTicket.objects.count()}')
for ticket in KitchenTicket.objects.all()[:5]:
    print(f'Ticket #{ticket.id}: {ticket.printer_target} - {ticket.status} - {ticket.items.count()} items')
"
```

**Check ticket details:**
```bash
docker exec fnb_edge_web python manage.py dbshell -c "
SELECT 
    kt.id,
    kt.printer_target,
    kt.status,
    COUNT(kti.id) as items_count,
    kt.created_at
FROM kitchen_kitchenticket kt
LEFT JOIN kitchen_kitchenitemticket kti ON kt.id = kti.kitchen_ticket_id
GROUP BY kt.id
ORDER BY kt.created_at DESC
LIMIT 5;
"
```

### Step 5: Check Admin Interface
```
URL: http://localhost:8001/admin/kitchen/kitchenticket/
```

View:
- All kitchen tickets
- Ticket status (NEW, PRINTING, PRINTED, FAILED)
- Items in each ticket
- Audit logs

---

## Expected Behavior

### Scenario 1: Single Station Order
**Given:**
- Bill with 3 items, all have `printer_target='kitchen'`

**When:** Click "Send to Kitchen"

**Then:**
- Creates 1 ticket for KITCHEN station
- Ticket has 3 items linked
- Notification: "✓ Berhasil kirim 3 item ke 1 station"

### Scenario 2: Multi-Station Order
**Given:**
- Bill with 6 items:
  - 2 items → BAR
  - 3 items → KITCHEN
  - 1 item → DESSERT

**When:** Click "Send to Kitchen"

**Then:**
- Creates 3 tickets (one per station)
- BAR ticket has 2 items
- KITCHEN ticket has 3 items
- DESSERT ticket has 1 item
- Notification: "✓ Berhasil kirim 6 item ke 3 station"

### Scenario 3: No Items to Send
**Given:**
- Bill with no pending items (all already sent or voided)

**When:** Click "Send to Kitchen"

**Then:**
- No tickets created
- Warning notification: "Tidak ada item baru untuk dikirim"

---

## Database Inspection Commands

### View All Tickets
```bash
docker exec fnb_edge_web python manage.py shell
```

```python
from apps.kitchen.models import *

# List all tickets
for ticket in KitchenTicket.objects.all():
    print(f"#{ticket.id}: {ticket.printer_target} - {ticket.status}")
    print(f"  Bill: #{ticket.bill.bill_number}")
    print(f"  Items: {ticket.items.count()}")
    print(f"  Created: {ticket.created_at}")
    print()
```

### View Ticket Items
```python
ticket = KitchenTicket.objects.first()
for item in ticket.items.all():
    bi = item.bill_item
    print(f"- {bi.product.name} x{bi.quantity}")
```

### View Audit Logs
```python
from apps.kitchen.models import KitchenTicketLog

for log in KitchenTicketLog.objects.all()[:10]:
    print(f"{log.timestamp}: {log.action} by {log.actor}")
    print(f"  Ticket #{log.ticket_id} - {log.old_status} → {log.new_status}")
```

### View Printer Configuration
```python
for printer in StationPrinter.objects.all():
    print(f"{printer.station_code} → {printer.printer_ip}:{printer.printer_port}")
    print(f"  Priority: {printer.priority}, Active: {printer.is_active}")
    print(f"  Total prints: {printer.total_prints}, Failed: {printer.failed_prints}")
```

---

## Troubleshooting

### Issue: No tickets created
**Check:**
1. Are items marked with `printer_target`?
   ```python
   from apps.pos.models import Bill
   bill = Bill.objects.get(id=YOUR_BILL_ID)
   for item in bill.items.all():
       print(f"{item.product.name}: printer_target={item.printer_target}")
   ```

2. Are items in 'pending' status?
   ```python
   bill.items.filter(status='pending', is_void=False).count()
   ```

### Issue: Error when clicking button
**Check Docker logs:**
```bash
docker logs fnb_edge_web --tail 50
```

### Issue: Tickets created but status not updating
**This is expected!** The printer service will update the status:
- Tickets are created with `status='new'`
- Printer service polls for 'new' tickets
- Service updates status: new → printing → printed/failed

---

## Next Steps

### 1. Test the Flow
- [ ] Create a bill with items
- [ ] Click "Send to Kitchen"
- [ ] Verify tickets in admin panel
- [ ] Check database records

### 2. Monitor Logs
Watch for debug output in Docker logs:
```bash
docker logs -f fnb_edge_web | grep -i kitchen
```

### 3. Build Printer Service
Once ticket creation is validated, build the polling service:
- Poll `kitchen_kitchenticket` for status='new'
- Format ESC/POS commands
- Send to printer IP
- Update ticket status
- Handle errors with fallback to backup printers

---

## API Reference

### Service Function
```python
from apps.kitchen.services import create_kitchen_tickets

# Create tickets from bill
tickets = create_kitchen_tickets(bill)

# Returns list of KitchenTicket instances
# Automatically groups by printer_target
```

### Model Structure
```python
# KitchenTicket (one per station per order)
{
    'id': 1,
    'bill': Bill instance,
    'printer_target': 'kitchen',
    'status': 'new',  # new|printing|printed|failed
    'is_reprint': False,
    'created_at': datetime,
}

# KitchenTicketItem (junction table)
{
    'kitchen_ticket': KitchenTicket instance,
    'bill_item': BillItem instance,
    'quantity': 2,
}
```

---

## Test Checklist

- [ ] POS system loads without errors
- [ ] "Send to Kitchen" button visible
- [ ] Button shows correct item count badge
- [ ] Clicking button creates tickets in database
- [ ] Success notification appears
- [ ] Items status changes from 'pending' to 'sent'
- [ ] Tickets visible in admin panel
- [ ] Audit logs created
- [ ] Multiple stations handled correctly
- [ ] No duplicate tickets created

---

## System Architecture

```
┌─────────────────┐
│   POS Frontend  │  User clicks "Send to Kitchen"
└────────┬────────┘
         │ AJAX POST
         ▼
┌─────────────────────────────┐
│  /pos/bill/<id>/send-kitchen │
│  (Django View)               │
└────────┬────────────────────┘
         │ Calls
         ▼
┌─────────────────────────────┐
│  create_kitchen_tickets()   │  Groups items by printer_target
│  (Service Layer)            │  Creates 1 ticket per station
└────────┬────────────────────┘
         │ Creates
         ▼
┌─────────────────────────────┐
│  kitchen_kitchenticket      │  status='new', ready for polling
│  kitchen_kitchenitemticket  │
│  kitchen_kitchenlog         │
└────────┬────────────────────┘
         │ Polled by
         ▼
┌─────────────────────────────┐
│  Printer Service (TODO)     │  Polls every 1-5 seconds
│  (Standalone Python Script) │  Formats ESC/POS, sends to printer
└─────────────────────────────┘
```

---

## Production Considerations

1. **Idempotency:** Service prevents duplicate tickets for same bill
2. **Audit Trail:** All state changes logged immutably
3. **Error Recovery:** Failed tickets stay in database for retry
4. **Health Monitoring:** Track printer success/failure rates
5. **Backup Printers:** Automatic failover using priority system
6. **Performance:** Indexed queries for fast polling

---

**Last Updated:** 2024
**Status:** ✅ Ready for Testing
