"""Kitchen services for printing and KDS operations"""
from .models import KitchenOrder, PrinterConfig


def get_printer(config):
    """Get printer instance based on config"""
    try:
        from escpos.printer import Network, Usb
        
        if config.connection_type == 'network':
            return Network(config.ip_address, config.port)
        elif config.connection_type == 'usb':
            return Usb(int(config.usb_vendor, 16), int(config.usb_product, 16))
    except Exception as e:
        print(f"Printer error: {e}")
    return None


def print_kitchen_order(bill, station, items):
    """Print order to kitchen printer"""
    config = PrinterConfig.objects.filter(
        outlet=bill.outlet,
        station=station,
        is_active=True
    ).first()
    
    if not config:
        print(f"No printer configured for station: {station}")
        return
    
    try:
        p = get_printer(config)
        if not p:
            return
        
        p.set(align='center', bold=True, double_height=True)
        p.text(f"--- {station.upper()} ---\n")
        p.set(align='left', bold=False, double_height=False)
        
        p.text(f"Bill: {bill.bill_number}\n")
        if bill.table:
            p.set(bold=True, double_height=True)
            p.text(f"Meja: {bill.table.number}\n")
            p.set(bold=False, double_height=False)
        elif bill.queue_number:
            p.set(bold=True, double_height=True)
            p.text(f"Antrian: #{bill.queue_number}\n")
            p.set(bold=False, double_height=False)
        
        p.text(f"Waktu: {bill.created_at.strftime('%H:%M')}\n")
        p.text("-" * 32 + "\n")
        
        for item in items:
            p.set(bold=True)
            p.text(f"{item.quantity}x {item.product.name}\n")
            p.set(bold=False)
            
            if item.modifiers:
                for mod in item.modifiers:
                    p.text(f"   - {mod['name']}\n")
            
            if item.notes:
                p.set(bold=True)
                p.text(f"   !! {item.notes}\n")
                p.set(bold=False)
        
        p.text("-" * 32 + "\n")
        p.cut()
        p.close()
        
    except Exception as e:
        print(f"Print error: {e}")


def create_kitchen_order(bill, station, items):
    """Create or get existing KDS entry - UPSERT pattern to prevent duplicates"""
    kitchen_order, created = KitchenOrder.objects.get_or_create(
        bill=bill,
        station=station,
        defaults={'status': 'new'}
    )
    
    # If already exists and status is 'ready' or 'served', reset to 'new'
    if not created and kitchen_order.status in ['ready', 'served']:
        kitchen_order.status = 'new'
        kitchen_order.save()
    
    return kitchen_order
