from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, JsonResponse
from collections import defaultdict
import json

from apps.tables.models import Table
from apps.pos.models import Bill, BillItem
from apps.core.models import Product, Category, User, ModifierOption
from apps.qr_order.recommendations import RecommendationEngine


def guest_product_detail(request, brand_id, table_id, product_id):
    """Show product detail with customization options - HTMX"""
    table = get_object_or_404(Table, id=table_id, area__brand_id=brand_id)
    product = get_object_or_404(Product, id=product_id)
    
    # Get available modifiers (if any)
    modifiers = ModifierOption.objects.filter(
        modifier__product=product,
        is_available=True
    ).select_related('modifier')
    
    # Calculate discount percentage if applicable
    discount_percentage = 0
    if product.original_price and product.original_price > product.price:
        discount_percentage = int(((product.original_price - product.price) / product.original_price) * 100)
    
    # Get all product images (main + gallery)
    product_images = []
    if product.image:
        product_images.append({
            'url': product.image.url,
            'caption': product.name
        })
    
    # Add gallery photos
    for photo in product.photos.filter(is_active=True):
        product_images.append({
            'url': photo.image.url,
            'caption': photo.caption or product.name
        })
    
    # Convert to JSON for Alpine.js
    import json
    product_images_json = json.dumps(product_images)
    
    # Get recommendations
    engine = RecommendationEngine(brand_id)
    frequently_bought_together = [p for p, score in engine.get_frequently_bought_together(product_id, limit=4)]
    category_recommendations = engine.get_category_recommendations(
        product.category_id, 
        exclude_product_id=product_id, 
        limit=4
    )
    
    return render(request, 'qr_order/partials/product_detail_modal.html', {
        'product': product,
        'modifiers': modifiers,
        'discount_percentage': discount_percentage,
        'product_images': product_images_json,
        'brand_id': brand_id,
        'table_id': table_id,
        'table': table,
        'frequently_bought_together': frequently_bought_together,
        'category_recommendations': category_recommendations,
    })


@require_http_methods(["POST"])
def guest_add_item_custom(request, brand_id, table_id):
    """Guest adds item with customization - HTMX"""
    table = get_object_or_404(Table, id=table_id, area__brand_id=brand_id)
    product_id = request.POST.get('product_id')
    quantity = int(request.POST.get('quantity', 1))
    notes = request.POST.get('notes', '')
    spice_level = request.POST.get('spice_level', '')
    modifiers = request.POST.getlist('modifiers[]', [])
    
    product = get_object_or_404(Product, id=product_id)
    
    # Build complete notes
    full_notes = []
    if spice_level:
        spice_labels = {
            'mild': '🌿 Tidak Pedas',
            'normal': '🌶️ Pedas',
            'hot': '🔥 Extra Pedas'
        }
        full_notes.append(spice_labels.get(spice_level, ''))
    
    if modifiers:
        modifier_objs = ModifierOption.objects.filter(id__in=modifiers)
        for mod in modifier_objs:
            full_notes.append(f"+ {mod.name}")
    
    if notes:
        full_notes.append(notes)
    
    final_notes = ' | '.join(full_notes)
    
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
            brand_id=brand_id,
            table=table,
            bill_type='dine_in',
            created_by=system_user,
            notes='QR Order'
        )
        table.status = 'occupied'
        table.save()
    
    # Calculate price with modifiers
    modifier_price = 0
    if modifiers:
        modifier_objs = ModifierOption.objects.filter(id__in=modifiers)
        modifier_price = sum(mod.price for mod in modifier_objs)
    
    unit_price = product.price + modifier_price
    
    # Create bill item
    BillItem.objects.create(
        bill=bill,
        product=product,
        quantity=quantity,
        unit_price=unit_price,
        notes=final_notes,
        created_by=system_user,
        status='pending',
    )
    
    bill.calculate_totals()
    
    return render(request, 'qr_order/partials/cart.html', {
        'bill': bill,
        'brand_id': brand_id,
        'table_id': table_id,
        'table': table,
    })


def guest_menu(request, brand_id, table_id):
    """Guest ordering page via QR"""
    table = get_object_or_404(Table, id=table_id, area__brand_id=brand_id)
    categories = Category.objects.filter(brand_id=brand_id, is_active=True)
    products = Product.objects.filter(category__brand_id=brand_id, is_active=True).select_related('category')
    
    bill = table.get_active_bill()
    
    # Prepare products data for Alpine.js
    products_json = json.dumps([{
        'id': p.id,
        'name': p.name,
        'description': p.description or '',
        'category_id': p.category_id,
        'price': float(p.price),
    } for p in products])
    
    # Get recommendations
    engine = RecommendationEngine(brand_id)
    popular_items = engine.get_popular_items(limit=6)
    trending_items = engine.get_trending_items(limit=4)
    
    # Get cart-based recommendations if there's an active bill
    cart_recommendations = []
    if bill and bill.items.exists():
        cart_product_ids = list(bill.items.values_list('product_id', flat=True))
        cart_recommendations = engine.get_recommended_for_cart(cart_product_ids, limit=4)
    
    return render(request, 'qr_order/menu.html', {
        'table': table,
        'categories': categories,
        'products': products,
        'products_json': products_json,
        'bill': bill,
        'brand_id': brand_id,
        'popular_items': popular_items,
        'trending_items': trending_items,
        'cart_recommendations': cart_recommendations,
    })


def guest_cart(request, brand_id, table_id):
    """Guest cart partial - HTMX"""
    table = get_object_or_404(Table, id=table_id, area__brand_id=brand_id)
    bill = table.get_active_bill()
    
    return render(request, 'qr_order/partials/cart.html', {
        'bill': bill,
        'brand_id': brand_id,
        'table_id': table_id,
        'table': table,
    })


@require_http_methods(["POST"])
def guest_add_item(request, brand_id, table_id):
    """Guest adds item to order - HTMX"""
    table = get_object_or_404(Table, id=table_id, area__brand_id=brand_id)
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
            brand_id=brand_id,
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
        'brand_id': brand_id,
        'table_id': table_id,
        'table': table,
    })


@require_http_methods(["POST"])
def guest_remove_item(request, brand_id, table_id, item_id):
    """Guest removes item from order - HTMX"""
    table = get_object_or_404(Table, id=table_id, area__brand_id=brand_id)
    item = get_object_or_404(BillItem, id=item_id, status='pending')
    
    bill = item.bill
    item.delete()
    bill.calculate_totals()
    
    return render(request, 'qr_order/partials/cart.html', {
        'bill': bill,
        'brand_id': brand_id,
        'table_id': table_id,
        'table': table,
    })


@require_http_methods(["POST"])
def guest_update_item(request, brand_id, table_id, item_id):
    """Guest updates item quantity - HTMX"""
    table = get_object_or_404(Table, id=table_id, area__brand_id=brand_id)
    item = get_object_or_404(BillItem, id=item_id, status='pending')
    action = request.POST.get('action')
    
    bill = item.bill
    
    if action == 'increase':
        item.quantity += 1
        item.save()
    elif action == 'decrease':
        if item.quantity > 1:
            item.quantity -= 1
            item.save()
        else:
            item.delete()
    
    bill.calculate_totals()
    
    return render(request, 'qr_order/partials/cart.html', {
        'bill': bill,
        'brand_id': brand_id,
        'table_id': table_id,
        'table': table,
    })


@require_http_methods(["POST"])
def guest_submit_order(request, brand_id, table_id):
    """Guest submits order - sends to kitchen"""
    table = get_object_or_404(Table, id=table_id, area__brand_id=brand_id)
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
        'brand_id': brand_id,
        'table_id': table_id,
        'table': table,
    })


def guest_order_status(request, brand_id, table_id):
    """Guest checks order status - HTMX"""
    table = get_object_or_404(Table, id=table_id, area__brand_id=brand_id)
    bill = table.get_active_bill()
    
    return render(request, 'qr_order/partials/order_status.html', {
        'bill': bill,
        'brand_id': brand_id,
        'table_id': table_id,
        'table': table,
    })
