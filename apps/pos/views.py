from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from django.utils import timezone
from decimal import Decimal
import json

from .models import Bill, BillItem, Payment, BillLog
from apps.core.models import Product, Category, ModifierOption
from apps.tables.models import Table


def trigger_client_event(response, event_name, data=None):
    """Helper to trigger HTMX client events"""
    if data:
        response['HX-Trigger'] = json.dumps({event_name: data})
    else:
        response['HX-Trigger'] = event_name
    return response


@login_required
def pos_main(request):
    """Main POS interface"""
    outlet = request.user.outlet
    if not outlet:
        return render(request, 'pos/no_outlet.html')
    
    categories = Category.objects.filter(outlet=outlet, is_active=True)
    tables = Table.objects.filter(area__outlet=outlet)
    products = Product.objects.filter(category__outlet=outlet, is_active=True)
    
    bill_id = request.session.get('active_bill_id')
    bill = None
    if bill_id:
        bill = Bill.objects.filter(id=bill_id, status='open').first()
    
    held_count = Bill.objects.filter(outlet=outlet, status='hold').count()
    
    context = {
        'categories': categories,
        'tables': tables,
        'products': products,
        'bill': bill,
        'held_count': held_count,
    }
    return render(request, 'pos/main.html', context)


@login_required
def product_list(request):
    """Product list partial - HTMX"""
    outlet = request.user.outlet
    category_id = request.GET.get('category')
    
    products = Product.objects.filter(category__outlet=outlet, is_active=True)
    
    if category_id and category_id != 'all':
        products = products.filter(category_id=category_id)
    
    is_modal = request.GET.get('modal') == '1'
    template = 'pos/partials/product_grid_mini.html' if is_modal else 'pos/partials/product_grid.html'
    
    return render(request, template, {'products': products})


@login_required
@require_http_methods(["POST"])
def open_bill(request):
    """Open new bill - HTMX"""
    table_id = request.POST.get('table_id')
    bill_type = request.POST.get('bill_type', 'dine_in')
    guest_count = int(request.POST.get('guest_count', 1))
    
    with transaction.atomic():
        bill = Bill.objects.create(
            outlet=request.user.outlet,
            table_id=table_id if table_id else None,
            bill_type=bill_type,
            guest_count=guest_count,
            created_by=request.user,
        )
        
        if table_id:
            Table.objects.filter(id=table_id).update(status='occupied')
        
        request.session['active_bill_id'] = bill.id
        
        BillLog.objects.create(bill=bill, action='open', user=request.user)
    
    response = render(request, 'pos/partials/bill_panel.html', {'bill': bill})
    return trigger_client_event(response, 'billOpened', {'bill_id': bill.id})


@login_required
@require_http_methods(["POST"])
def add_item(request, bill_id):
    """Add item to bill - HTMX"""
    bill = get_object_or_404(Bill, id=bill_id, status='open')
    product_id = request.POST.get('product_id')
    quantity = int(request.POST.get('quantity', 1))
    notes = request.POST.get('notes', '')
    modifiers = request.POST.getlist('modifiers')
    
    product = get_object_or_404(Product, id=product_id)
    
    modifier_price = Decimal('0')
    modifier_data = []
    for mod_id in modifiers:
        opt = ModifierOption.objects.get(id=mod_id)
        modifier_price += opt.price_adjustment
        modifier_data.append({
            'id': opt.id,
            'name': opt.name,
            'price': float(opt.price_adjustment)
        })
    
    existing_item = BillItem.objects.filter(
        bill=bill,
        product=product,
        notes=notes,
        modifiers=modifier_data,
        is_void=False,
        status='pending'
    ).first()
    
    if existing_item:
        existing_item.quantity += quantity
        existing_item.save()
        item = existing_item
    else:
        item = BillItem.objects.create(
            bill=bill,
            product=product,
            quantity=quantity,
            unit_price=product.price,
            modifier_price=modifier_price,
            notes=notes,
            modifiers=modifier_data,
            created_by=request.user,
        )
    
    bill.calculate_totals()
    
    BillLog.objects.create(
        bill=bill,
        action='add_item',
        user=request.user,
        details={'product': product.name, 'quantity': quantity}
    )
    
    response = render(request, 'pos/partials/bill_items.html', {'bill': bill})
    return trigger_client_event(response, 'itemAdded')


@login_required
@require_http_methods(["POST"])
def void_item(request, item_id):
    """Void item - HTMX with permission check"""
    item = get_object_or_404(BillItem, id=item_id)
    
    if item.status != 'pending' and not request.user.has_permission('void_item'):
        return HttpResponse(
            '<div class="p-3 bg-red-100 text-red-700 rounded">Anda tidak memiliki akses untuk void item yang sudah diproses</div>',
            status=403
        )
    
    reason = request.POST.get('reason', '')
    item.is_void = True
    item.void_reason = reason
    item.void_by = request.user
    item.save()
    
    item.bill.calculate_totals()
    
    BillLog.objects.create(
        bill=item.bill,
        action='void_item',
        user=request.user,
        details={'product': item.product.name, 'reason': reason}
    )
    
    return render(request, 'pos/partials/bill_items.html', {'bill': item.bill})


@login_required
@require_http_methods(["POST"])
def update_item_qty(request, item_id):
    """Update item quantity - HTMX"""
    item = get_object_or_404(BillItem, id=item_id, is_void=False)
    action = request.POST.get('action')
    
    if action == 'increase':
        item.quantity += 1
    elif action == 'decrease' and item.quantity > 1:
        item.quantity -= 1
    
    item.save()
    item.bill.calculate_totals()
    
    return render(request, 'pos/partials/bill_items.html', {'bill': item.bill})


@login_required
@require_http_methods(["POST"])
def hold_bill(request, bill_id):
    """Hold bill - HTMX"""
    bill = get_object_or_404(Bill, id=bill_id, status='open')
    bill.status = 'hold'
    bill.save()
    
    if bill.table:
        bill.table.status = 'occupied'
        bill.table.save()
    
    request.session.pop('active_bill_id', None)
    
    BillLog.objects.create(bill=bill, action='hold', user=request.user)
    
    response = render(request, 'pos/partials/bill_panel.html', {'bill': None})
    return trigger_client_event(response, 'billHeld')


@login_required
@require_http_methods(["POST"])
def resume_bill(request, bill_id):
    """Resume held bill - HTMX"""
    bill = get_object_or_404(Bill, id=bill_id, status='hold')
    bill.status = 'open'
    bill.save()
    
    request.session['active_bill_id'] = bill.id
    
    BillLog.objects.create(bill=bill, action='resume', user=request.user)
    
    return render(request, 'pos/partials/bill_panel.html', {'bill': bill})


@login_required
@require_http_methods(["POST"])
def cancel_bill(request, bill_id):
    """Cancel bill - HTMX"""
    bill = get_object_or_404(Bill, id=bill_id, status__in=['open', 'hold'])
    
    if not request.user.has_permission('cancel_bill'):
        return HttpResponse(
            '<div class="p-3 bg-red-100 text-red-700 rounded">Anda tidak memiliki akses untuk cancel bill</div>',
            status=403
        )
    
    reason = request.POST.get('reason', '')
    bill.status = 'cancelled'
    bill.notes = f"Cancelled: {reason}"
    bill.save()
    
    if bill.table:
        bill.table.status = 'available'
        bill.table.save()
    
    request.session.pop('active_bill_id', None)
    
    BillLog.objects.create(
        bill=bill,
        action='cancel',
        user=request.user,
        details={'reason': reason}
    )
    
    response = render(request, 'pos/partials/bill_panel.html', {'bill': None})
    return trigger_client_event(response, 'billCancelled')


@login_required
def held_bills(request):
    """List held bills - HTMX"""
    bills = Bill.objects.filter(
        outlet=request.user.outlet,
        status='hold'
    ).select_related('table')
    
    return render(request, 'pos/partials/held_bills_list.html', {'bills': bills})


@login_required
@require_http_methods(["POST"])
def send_to_kitchen(request, bill_id):
    """Send pending items to kitchen - HTMX"""
    bill = get_object_or_404(Bill, id=bill_id)
    pending_items = bill.items.filter(status='pending', is_void=False)
    
    if not pending_items.exists():
        return HttpResponse('<div class="p-3 bg-yellow-100 text-yellow-700 rounded">Tidak ada item untuk dikirim</div>')
    
    from collections import defaultdict
    from apps.kitchen.services import print_kitchen_order, create_kitchen_order
    
    grouped = defaultdict(list)
    for item in pending_items:
        grouped[item.product.printer_target].append(item)
    
    for station, items in grouped.items():
        if station != 'none':
            create_kitchen_order(bill, station, items)
            print_kitchen_order(bill, station, items)
    
    pending_items.update(status='sent')
    
    BillLog.objects.create(bill=bill, action='send_kitchen', user=request.user)
    
    response = render(request, 'pos/partials/bill_items.html', {'bill': bill})
    return trigger_client_event(response, 'sentToKitchen')


@login_required
def payment_modal(request, bill_id):
    """Payment modal - HTMX"""
    bill = get_object_or_404(Bill, id=bill_id)
    return render(request, 'pos/partials/payment_modal.html', {'bill': bill})


@login_required
@require_http_methods(["POST"])
def process_payment(request, bill_id):
    """Process payment - HTMX"""
    bill = get_object_or_404(Bill, id=bill_id, status='open')
    
    method = request.POST.get('method')
    amount = Decimal(request.POST.get('amount', 0))
    reference = request.POST.get('reference', '')
    
    Payment.objects.create(
        bill=bill,
        method=method,
        amount=amount,
        reference=reference,
        created_by=request.user,
    )
    
    BillLog.objects.create(
        bill=bill,
        action='payment',
        user=request.user,
        details={'method': method, 'amount': float(amount)}
    )
    
    if bill.get_remaining() <= 0:
        bill.status = 'paid'
        bill.closed_by = request.user
        bill.closed_at = timezone.now()
        bill.save()
        
        if bill.table:
            bill.table.status = 'dirty'
            bill.table.save()
        
        request.session.pop('active_bill_id', None)
        
        BillLog.objects.create(bill=bill, action='close', user=request.user)
        
        from apps.pos.services import print_receipt
        print_receipt(bill)
        
        response = render(request, 'pos/partials/payment_success.html', {'bill': bill})
        return trigger_client_event(response, 'paymentComplete')
    
    return render(request, 'pos/partials/payment_modal.html', {'bill': bill})


@login_required
def split_bill_modal(request, bill_id):
    """Split bill modal - HTMX"""
    bill = get_object_or_404(Bill, id=bill_id)
    return render(request, 'pos/partials/split_bill_modal.html', {'bill': bill})


@login_required
@require_http_methods(["POST"])
def split_bill(request, bill_id):
    """Split bill into multiple bills - HTMX"""
    original_bill = get_object_or_404(Bill, id=bill_id, status='open')
    split_items = request.POST.getlist('split_items')
    
    if not split_items:
        return HttpResponse('<div class="p-3 bg-yellow-100 text-yellow-700 rounded">Pilih item untuk di-split</div>')
    
    with transaction.atomic():
        new_bill = Bill.objects.create(
            outlet=original_bill.outlet,
            table=original_bill.table,
            bill_type=original_bill.bill_type,
            guest_count=1,
            created_by=request.user,
            notes=f"Split from {original_bill.bill_number}"
        )
        
        BillItem.objects.filter(id__in=split_items).update(bill=new_bill)
        
        original_bill.calculate_totals()
        new_bill.calculate_totals()
        
        BillLog.objects.create(
            bill=original_bill,
            action='split_bill',
            user=request.user,
            details={'new_bill': new_bill.bill_number}
        )
    
    return render(request, 'pos/partials/split_bill_result.html', {
        'original_bill': original_bill,
        'new_bill': new_bill
    })


@login_required
@require_http_methods(["POST"])
def reprint_receipt(request, bill_id):
    """Reprint receipt - HTMX"""
    bill = get_object_or_404(Bill, id=bill_id)
    
    if not request.user.has_permission('reprint'):
        return HttpResponse(
            '<div class="p-3 bg-red-100 text-red-700 rounded">Tidak memiliki akses reprint</div>',
            status=403
        )
    
    from apps.pos.services import print_receipt
    print_receipt(bill)
    
    BillLog.objects.create(bill=bill, action='reprint_receipt', user=request.user)
    
    return HttpResponse('<div class="p-3 bg-green-100 text-green-700 rounded">Receipt dicetak ulang</div>')


@login_required
@require_http_methods(["POST"])
def reprint_kitchen(request, bill_id):
    """Reprint kitchen order - HTMX"""
    bill = get_object_or_404(Bill, id=bill_id)
    station = request.POST.get('station', 'kitchen')
    
    items = bill.items.filter(
        product__printer_target=station,
        is_void=False
    )
    
    from apps.kitchen.services import print_kitchen_order
    print_kitchen_order(bill, station, list(items))
    
    BillLog.objects.create(
        bill=bill,
        action='reprint_kitchen',
        user=request.user,
        details={'station': station}
    )
    
    return HttpResponse(f'<div class="p-3 bg-green-100 text-green-700 rounded">Order {station} dicetak ulang</div>')


@login_required
def select_table_modal(request):
    """Select table modal - HTMX"""
    tables = Table.objects.filter(
        area__outlet=request.user.outlet,
        status='available'
    ).select_related('area')
    
    return render(request, 'pos/partials/select_table_modal.html', {'tables': tables})


@login_required
def modifier_modal(request, product_id):
    """Modifier selection modal - HTMX"""
    product = get_object_or_404(Product, id=product_id)
    modifiers = product.modifiers.prefetch_related('options')
    
    return render(request, 'pos/partials/modifier_modal.html', {
        'product': product,
        'modifiers': modifiers,
    })


@login_required
def quick_order_modal(request):
    """Quick order modal - HTMX"""
    categories = Category.objects.filter(outlet=request.user.outlet, is_active=True)
    products = Product.objects.filter(category__outlet=request.user.outlet, is_active=True)
    
    return render(request, 'pos/partials/quick_order_modal.html', {
        'categories': categories,
        'products': products,
    })


@login_required
@require_http_methods(["POST"])
def quick_order_create(request):
    """Create quick order with direct payment - HTMX"""
    items_data = request.POST.get('items')
    payment_method = request.POST.get('payment_method', 'cash')
    payment_amount = Decimal(request.POST.get('payment_amount', 0))
    customer_name = request.POST.get('customer_name', '')
    
    items = json.loads(items_data)
    
    with transaction.atomic():
        today = timezone.now().date()
        last_queue = Bill.objects.filter(
            outlet=request.user.outlet,
            bill_type='takeaway',
            created_at__date=today
        ).aggregate(max_queue=models.Max('queue_number'))
        
        queue_number = (last_queue['max_queue'] or 0) + 1
        
        bill = Bill.objects.create(
            outlet=request.user.outlet,
            bill_type='takeaway',
            customer_name=customer_name,
            queue_number=queue_number,
            created_by=request.user,
        )
        
        for item_data in items:
            product = Product.objects.get(id=item_data['product_id'])
            BillItem.objects.create(
                bill=bill,
                product=product,
                quantity=item_data['quantity'],
                unit_price=product.price,
                notes=item_data.get('notes', ''),
                created_by=request.user,
                status='pending',
            )
        
        bill.calculate_totals()
        
        Payment.objects.create(
            bill=bill,
            method=payment_method,
            amount=payment_amount,
            created_by=request.user,
        )
        
        if bill.get_remaining() <= 0:
            bill.status = 'paid'
            bill.closed_by = request.user
            bill.closed_at = timezone.now()
            bill.save()
        
        # Send to kitchen
        from collections import defaultdict
        from apps.kitchen.services import print_kitchen_order, create_kitchen_order
        
        pending_items = bill.items.filter(status='pending', is_void=False)
        grouped = defaultdict(list)
        for item in pending_items:
            grouped[item.product.printer_target].append(item)
        
        for station, items_list in grouped.items():
            if station != 'none':
                create_kitchen_order(bill, station, items_list)
                print_kitchen_order(bill, station, items_list)
        
        pending_items.update(status='sent')
        
        from apps.pos.services import print_receipt
        print_receipt(bill)
    
    change = payment_amount - bill.total if payment_amount > bill.total else Decimal('0')
    
    return render(request, 'pos/partials/quick_order_success.html', {
        'bill': bill,
        'change': change,
    })


@login_required
def queue_display(request):
    """Queue number display screen"""
    today = timezone.now().date()
    
    ready_orders = Bill.objects.filter(
        outlet=request.user.outlet,
        bill_type='takeaway',
        created_at__date=today,
        queue_number__isnull=False,
    ).filter(
        items__status='ready'
    ).distinct().order_by('queue_number')[:10]
    
    preparing_orders = Bill.objects.filter(
        outlet=request.user.outlet,
        bill_type='takeaway',
        created_at__date=today,
        queue_number__isnull=False,
    ).filter(
        items__status__in=['sent', 'preparing']
    ).distinct().order_by('queue_number')[:10]
    
    return render(request, 'pos/queue_display.html', {
        'ready_orders': ready_orders,
        'preparing_orders': preparing_orders,
    })
