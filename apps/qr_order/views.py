from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from collections import defaultdict

from apps.tables.models import Table
from apps.pos.models import Bill, BillItem
from apps.core.models import Product, Category, User


def guest_menu(request, outlet_id, table_id):
    """Guest ordering page via QR"""
    table = get_object_or_404(Table, id=table_id, area__outlet_id=outlet_id)
    categories = Category.objects.filter(outlet_id=outlet_id, is_active=True)
    products = Product.objects.filter(category__outlet_id=outlet_id, is_active=True)
    
    bill = table.get_active_bill()
    
    return render(request, 'qr_order/menu.html', {
        'table': table,
        'categories': categories,
        'products': products,
        'bill': bill,
        'outlet_id': outlet_id,
    })


def guest_cart(request, outlet_id, table_id):
    """Guest cart partial - HTMX"""
    table = get_object_or_404(Table, id=table_id, area__outlet_id=outlet_id)
    bill = table.get_active_bill()
    
    return render(request, 'qr_order/partials/cart.html', {
        'bill': bill,
        'outlet_id': outlet_id,
        'table_id': table_id,
    })


@require_http_methods(["POST"])
def guest_add_item(request, outlet_id, table_id):
    """Guest adds item to order - HTMX"""
    table = get_object_or_404(Table, id=table_id, area__outlet_id=outlet_id)
    product_id = request.POST.get('product_id')
    quantity = int(request.POST.get('quantity', 1))
    notes = request.POST.get('notes', '')
    
    product = get_object_or_404(Product, id=product_id)
    
    # Get system user for guest orders
    system_user = User.objects.filter(username='system').first()
    if not system_user:
        system_user = User.objects.create_user(
            username='system',
            email='system@pos.local',
            role='waiter'
        )
    
    bill = table.get_active_bill()
    if not bill:
        bill = Bill.objects.create(
            outlet_id=outlet_id,
            table=table,
            bill_type='dine_in',
            created_by=system_user,
            notes='QR Order'
        )
        table.status = 'occupied'
        table.save()
    
    # Check if same item exists
    existing_item = BillItem.objects.filter(
        bill=bill,
        product=product,
        notes=notes,
        is_void=False,
        status='pending'
    ).first()
    
    if existing_item:
        existing_item.quantity += quantity
        existing_item.save()
    else:
        BillItem.objects.create(
            bill=bill,
            product=product,
            quantity=quantity,
            unit_price=product.price,
            notes=notes,
            created_by=system_user,
            status='pending',
        )
    
    bill.calculate_totals()
    
    return render(request, 'qr_order/partials/cart.html', {
        'bill': bill,
        'outlet_id': outlet_id,
        'table_id': table_id,
    })


@require_http_methods(["POST"])
def guest_remove_item(request, outlet_id, table_id, item_id):
    """Guest removes item from order - HTMX"""
    table = get_object_or_404(Table, id=table_id, area__outlet_id=outlet_id)
    item = get_object_or_404(BillItem, id=item_id, status='pending')
    
    bill = item.bill
    item.delete()
    bill.calculate_totals()
    
    return render(request, 'qr_order/partials/cart.html', {
        'bill': bill,
        'outlet_id': outlet_id,
        'table_id': table_id,
    })


@require_http_methods(["POST"])
def guest_submit_order(request, outlet_id, table_id):
    """Guest submits order - sends to kitchen"""
    table = get_object_or_404(Table, id=table_id, area__outlet_id=outlet_id)
    bill = table.get_active_bill()
    
    if not bill:
        return HttpResponse('<div class="p-4 bg-yellow-100 text-yellow-700 rounded">Tidak ada pesanan</div>')
    
    pending_items = bill.items.filter(status='pending', is_void=False)
    
    if not pending_items.exists():
        return HttpResponse('<div class="p-4 bg-yellow-100 text-yellow-700 rounded">Tidak ada item baru untuk dikirim</div>')
    
    # Send to kitchen
    from apps.kitchen.services import print_kitchen_order, create_kitchen_order
    
    grouped = defaultdict(list)
    for item in pending_items:
        grouped[item.product.printer_target].append(item)
    
    for station, items in grouped.items():
        if station != 'none':
            create_kitchen_order(bill, station, items)
            print_kitchen_order(bill, station, items)
    
    pending_items.update(status='sent')
    
    return render(request, 'qr_order/partials/order_submitted.html', {
        'bill': bill,
        'outlet_id': outlet_id,
        'table_id': table_id,
    })


def guest_order_status(request, outlet_id, table_id):
    """Guest checks order status - HTMX"""
    table = get_object_or_404(Table, id=table_id, area__outlet_id=outlet_id)
    bill = table.get_active_bill()
    
    return render(request, 'qr_order/partials/order_status.html', {
        'bill': bill,
        'outlet_id': outlet_id,
        'table_id': table_id,
    })
