#!/usr/bin/env python
"""
Test script to simulate Send to Kitchen flow
Creates a test bill and tickets
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_fnb.settings')
django.setup()

from apps.pos.models import Bill, BillItem
from apps.core.models import Product, Brand, User
from apps.kitchen.services import create_kitchen_tickets
from apps.kitchen.models import KitchenTicket, KitchenTicketItem
from django.utils import timezone

def test_send_to_kitchen():
    """Test creating kitchen tickets from a bill"""
    
    print("=== Kitchen Printer Test ===\n")
    
    # Get or create test data
    try:
        brand = Brand.objects.first()
        user = User.objects.first()
        
        # Find products with different printer targets
        kitchen_product = Product.objects.filter(printer_target='kitchen').first()
        
        if not kitchen_product:
            print("ERROR: No products with printer_target found")
            return
        
        print(f"Using brand: {brand.name}")
        print(f"Using user: {user.username}")
        print(f"Test product: {kitchen_product.name} → {kitchen_product.printer_target}\n")
        
        # Create test bill
        bill = Bill.objects.create(
            brand=brand,
            bill_type='dine_in',
            bill_number=f'TEST-{timezone.now().strftime("%Y%m%d-%H%M%S")}',
            status='open',
            created_by=user,
        )
        
        print(f"✓ Created test bill: {bill.bill_number}\n")
        
        # Add items to bill
        items_data = [
            {'product': kitchen_product, 'qty': 2, 'target': 'kitchen'},
            {'product': kitchen_product, 'qty': 1, 'target': 'bar'},
            {'product': kitchen_product, 'qty': 3, 'target': 'kitchen'},
        ]
        
        print("Adding items to bill:")
        for item_data in items_data:
            item = BillItem.objects.create(
                bill=bill,
                product=item_data['product'],
                quantity=item_data['qty'],
                unit_price=item_data['product'].price,
                status='pending',
                printer_target=item_data['target'],
                created_by=user,
            )
            print(f"  + {item.product.name} x{item.quantity} → {item.printer_target}")
        
        print(f"\n✓ Added {bill.items.count()} items\n")
        
        # Test create_kitchen_tickets
        print("Calling create_kitchen_tickets()...")
        tickets = create_kitchen_tickets(bill)
        
        print(f"\n✓ Created {len(tickets)} ticket(s):\n")
        
        for ticket in tickets:
            print(f"Ticket #{ticket.id}:")
            print(f"  Station: {ticket.printer_target.upper()}")
            print(f"  Status: {ticket.status}")
            print(f"  Items:")
            for ticket_item in ticket.items.all():
                bi = ticket_item.bill_item
                print(f"    - {bi.product.name} x{bi.quantity}")
            print()
        
        # Show summary
        print("\n=== Summary ===")
        print(f"Bill: {bill.bill_number}")
        print(f"Total items: {bill.items.count()}")
        print(f"Kitchen tickets: {bill.kitchen_tickets.count()}")
        print(f"Total tickets in system: {KitchenTicket.objects.count()}")
        
        print("\n✅ Test completed successfully!")
        print("\nNext steps:")
        print("1. Check admin panel: http://localhost:8001/admin/kitchen/kitchenticket/")
        print("2. Try Send to Kitchen button in POS")
        print("3. Build printer service to poll and print tickets")
        
    except Exception as e:
        import traceback
        print(f"\n❌ Error: {e}")
        traceback.print_exc()

if __name__ == '__main__':
    test_send_to_kitchen()
