"""Kitchen services for printing and KDS operations"""
from django.db import transaction
from django.utils import timezone
from .models import KitchenOrder, PrinterConfig, KitchenTicket, KitchenTicketItem, KitchenTicketLog
import logging

logger = logging.getLogger(__name__)


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
        brand=bill.brand,
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


# ============================================================================
# KITCHEN PRINTER SERVICE FUNCTIONS
# ============================================================================

@transaction.atomic
def create_kitchen_tickets(bill, item_ids=None):
    """
    Create kitchen tickets from bill
    Groups items by printer_target and creates one ticket per station
    
    Args:
        bill: Bill instance
        item_ids: Optional list of specific BillItem IDs to create tickets for.
                  If None, creates tickets for all non-void items.
        
    Returns:
        list: List of created KitchenTicket instances
        
    Example:
        Bill with 6 items:
        - 2 items → BAR
        - 3 items → KITCHEN
        - 1 item → DESSERT
        
        Creates 3 tickets (one per station)
    """
    logger.info(f"Creating kitchen tickets for bill #{bill.bill_number}")
    
    # Group items by printer_target
    items_by_station = {}
    
    # Filter items - if item_ids provided, use only those items
    items_query = bill.items.filter(is_void=False).exclude(printer_target='').exclude(printer_target='none')
    if item_ids is not None:
        items_query = items_query.filter(id__in=item_ids)
        logger.info(f"Filtering for specific {len(item_ids)} item(s)")
    
    for item in items_query:
        # Use printer_target, fallback to 'kitchen' if empty
        station = item.printer_target or 'kitchen'
        
        if station not in items_by_station:
            items_by_station[station] = []
        
        items_by_station[station].append(item)
    
    if not items_by_station:
        logger.warning(f"No items to print for bill #{bill.bill_number}")
        return []
    
    tickets = []
    
    # Create 1 ticket per station
    for station_code, items in items_by_station.items():
        logger.info(f"Creating ticket for station '{station_code}' with {len(items)} items")
        
        ticket = KitchenTicket.objects.create(
            bill=bill,
            brand=bill.brand,
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
            old_status='',
            new_status='new',
            metadata={
                'items_count': len(items),
                'bill_number': bill.bill_number,
                'bill_type': bill.bill_type,
                'table': str(bill.table) if bill.table else None,
            }
        )
        
        tickets.append(ticket)
        logger.info(f"✓ Created ticket #{ticket.id} for {station_code.upper()}")
    
    # === CHECKER TICKET ===
    # Create a checker ticket containing ALL items from ALL stations
    # Only if a checker printer is configured for this brand
    from .models import StationPrinter
    has_checker_printer = StationPrinter.objects.filter(
        brand=bill.brand,
        station_code='checker',
        is_active=True
    ).exists()

    if has_checker_printer:
        # Collect ALL items from all stations for checker
        all_items = []
        for items in items_by_station.values():
            all_items.extend(items)

        logger.info(f"Creating CHECKER ticket with ALL {len(all_items)} items")

        checker_ticket = KitchenTicket.objects.create(
            bill=bill,
            brand=bill.brand,
            printer_target='checker',
            status='new'
        )

        for item in all_items:
            KitchenTicketItem.objects.create(
                kitchen_ticket=checker_ticket,
                bill_item=item,
                quantity=item.quantity
            )

        KitchenTicketLog.log_action(
            ticket=checker_ticket,
            action='created',
            actor='system',
            old_status='',
            new_status='new',
            metadata={
                'items_count': len(all_items),
                'bill_number': bill.bill_number,
                'bill_type': bill.bill_type,
                'table': str(bill.table) if bill.table else None,
                'is_checker': True,
                'stations_included': list(items_by_station.keys()),
            }
        )

        tickets.append(checker_ticket)
        logger.info(f"✓ Created CHECKER ticket #{checker_ticket.id} with {len(all_items)} items from {list(items_by_station.keys())}")

    logger.info(f"Successfully created {len(tickets)} ticket(s) for bill #{bill.bill_number}")

    return tickets


def get_bill_kitchen_status(bill):
    """
    Get kitchen ticket status summary for a bill
    
    Returns:
        dict: {
            'has_tickets': bool,
            'total_tickets': int,
            'new_tickets': int,
            'printing_tickets': int,
            'printed_tickets': int,
            'failed_tickets': int,
            'all_printed': bool,
            'has_failures': bool,
        }
    """
    tickets = bill.kitchen_tickets.all()
    
    status_count = {
        'new': 0,
        'printing': 0,
        'printed': 0,
        'failed': 0,
    }
    
    for ticket in tickets:
        status_count[ticket.status] = status_count.get(ticket.status, 0) + 1
    
    total = len(tickets)
    
    return {
        'has_tickets': total > 0,
        'total_tickets': total,
        'new_tickets': status_count['new'],
        'printing_tickets': status_count['printing'],
        'printed_tickets': status_count['printed'],
        'failed_tickets': status_count['failed'],
        'all_printed': total > 0 and status_count['printed'] == total,
        'has_failures': status_count['failed'] > 0,
    }


def reprint_kitchen_ticket(ticket, actor):
    """
    Create a reprint of a kitchen ticket
    
    Args:
        ticket: Original KitchenTicket instance
        actor: Who requested reprint (e.g., 'admin:username')
        
    Returns:
        KitchenTicket: New ticket instance (reprint)
    """
    with transaction.atomic():
        new_ticket = KitchenTicket.objects.create(
            bill=ticket.bill,
            brand=ticket.brand or ticket.bill.brand,
            printer_target=ticket.printer_target,
            status='new',
            is_reprint=True,
            original_ticket=ticket
        )
        
        # Copy items
        for item in ticket.items.all():
            KitchenTicketItem.objects.create(
                kitchen_ticket=new_ticket,
                bill_item=item.bill_item,
                quantity=item.quantity
            )
        
        # Log reprint
        KitchenTicketLog.log_action(
            ticket=new_ticket,
            action='created',
            actor=actor,
            old_status='',
            new_status='new',
            metadata={
                'reprint_of': ticket.id,
                'original_status': ticket.status,
            }
        )
        
        logger.info(f"Created reprint ticket #{new_ticket.id} from #{ticket.id} by {actor}")
        
        return new_ticket
