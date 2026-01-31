"""
Print Queue Service
Creates print jobs for remote printing via Print Agent
"""
from apps.pos.models import PrintJob


def create_receipt_job(bill, terminal_id='POS-001'):
    """Create receipt print job"""
    print(f"\n[PRINT QUEUE] Creating receipt job...")
    print(f"[PRINT QUEUE]   Bill: {bill.bill_number}")
    print(f"[PRINT QUEUE]   Terminal: {terminal_id}")
    print(f"[PRINT QUEUE]   Type: {bill.bill_type}")
    if bill.queue_number:
        print(f"[PRINT QUEUE]   Queue: #{bill.queue_number}")
    
    content = {
        'store_name': bill.brand.name,  # Match agent_v2.py field name
        'address': bill.brand.address or '',  # Match agent_v2.py field name
        'phone': bill.brand.phone or '',  # Match agent_v2.py field name
        'bill_number': bill.bill_number,
        'date': bill.closed_at.strftime('%d/%m/%Y %H:%M') if bill.closed_at else '',
        'cashier': bill.closed_by.get_full_name() if bill.closed_by else '',
        'bill_type': bill.bill_type,
        'queue_number': bill.queue_number,
        'table': bill.table.number if bill.table else None,
        'items': [
            {
                'name': item.product.name,
                'qty': item.quantity,
                'price': float(item.unit_price),
                'subtotal': float(item.total)  # Match agent_v2.py field name
            }
            for item in bill.items.filter(is_void=False)
        ],
        'payments': [
            {
                'method': payment.method,
                'amount': float(payment.amount)
            }
            for payment in bill.payments.all()
        ],
        'subtotal': float(bill.subtotal),
        'discount': float(bill.discount_amount),
        'tax': float(bill.tax_amount),
        'service': float(bill.service_charge),
        'total': float(bill.total),
        'footer': bill.brand.receipt_footer or 'Terima Kasih!'
    }
    
    job = PrintJob.objects.create(
        terminal_id=terminal_id,
        bill=bill,
        job_type='receipt',
        content=content
    )
    
    print(f"[PRINT QUEUE] ✅ Receipt print job created: #{job.id} for {terminal_id}")
    return job


def create_kitchen_job(bill, station, items, terminal_id='POS-001'):
    """Create kitchen order print job"""
    content = {
        'station': station,
        'order_number': bill.bill_number,
        'date': bill.created_at.strftime('%d/%m/%Y %H:%M'),
        'table': bill.table.number if bill.table else None,
        'queue_number': bill.queue_number,
        'customer_name': bill.customer_name,
        'items': [
            {
                'name': item.product.name,
                'qty': item.quantity,
                'notes': item.notes or ''
            }
            for item in items
        ]
    }
    
    job = PrintJob.objects.create(
        terminal_id=terminal_id,
        bill=bill,
        job_type='kitchen',
        content=content
    )
    
    print(f"✅ Kitchen print job created: #{job.id} for {station}")
    return job


def queue_print_receipt(bill, terminal_id=None):
    """
    Queue receipt for remote printing
    If terminal_id not specified, use default from bill.terminal or POS-001
    """
    if not terminal_id:
        terminal_id = bill.terminal.terminal_code if bill.terminal else 'POS-001'
    
    return create_receipt_job(bill, terminal_id)


def queue_print_kitchen(bill, station, items, terminal_id=None):
    """
    Queue kitchen order for remote printing
    """
    if not terminal_id:
        # Map station to terminal
        terminal_mapping = {
            'kitchen': 'KITCHEN-01',
            'bar': 'BAR-01',
            'grill': 'GRILL-01',
        }
        terminal_id = terminal_mapping.get(station, 'KITCHEN-01')
    
    return create_kitchen_job(bill, station, items, terminal_id)
