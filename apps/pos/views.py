from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db import transaction, models
from django.utils import timezone
from decimal import Decimal
import json

from .models import Bill, BillItem, Payment, BillLog
from apps.core.models import Product, Category, ModifierOption, StoreConfig
from apps.core.models_session import StoreSession, CashierShift, ShiftPaymentSummary
from apps.tables.models import Table


def trigger_client_event(response, event_name, data=None):
    """Helper to trigger HTMX client events"""
    if data:
        response['HX-Trigger'] = json.dumps({event_name: data})
    else:
        response['HX-Trigger'] = event_name
    return response


def render_bill_panel(request, bill):
    """Helper to render bill panel with store_config context"""
    store_config = StoreConfig.get_current()
    context = {
        'bill': bill,
        'store_config': store_config
    }
    # Add active items count for conditional logic
    if bill:
        context['active_items_count'] = bill.items.filter(status='pending', is_void=False).count()
        # Check if ANY item was ever sent to kitchen (including voided ones)
        context['has_sent_items'] = bill.items.filter(status='sent').exists()
    return render(request, 'pos/partials/bill_panel.html', context)


@login_required
@ensure_csrf_cookie
def pos_main(request):
    """Main POS interface"""
    outlet = request.user.outlet
    if not outlet:
        return render(request, 'pos/no_outlet.html')
    
    from apps.core.models import StoreConfig
    store_config = StoreConfig.get_current()
    
    categories = Category.objects.filter(outlet=outlet, is_active=True)
    tables = Table.objects.filter(area__outlet=outlet)
    
    # Order products by category for better display
    products = Product.objects.filter(
        category__outlet=outlet, 
        is_active=True
    ).select_related('category', 'category__parent').prefetch_related('modifiers').order_by(
        'category__sort_order',
        'category__name',
        'name'
    )
    
    # Check for bill_id from query parameter (e.g., after join tables) or session
    bill_id = request.GET.get('bill_id') or request.session.get('active_bill_id')
    bill = None
    active_items_count = 0
    has_sent_items = False
    
    # Debug logging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"POS Main - bill_id from session: {request.session.get('active_bill_id')}")
    logger.info(f"POS Main - bill_id from GET: {request.GET.get('bill_id')}")
    logger.info(f"POS Main - final bill_id: {bill_id}")
    
    if bill_id:
        bill = Bill.objects.filter(id=bill_id, status__in=['open', 'hold']).first()
        logger.info(f"POS Main - bill found: {bill}")
        if bill:
            # Update session with new active bill
            request.session['active_bill_id'] = bill.id
            request.session.modified = True
            # Calculate active items count (pending items only)
            active_items_count = bill.items.filter(status='pending', is_void=False).count()
            # Check if ANY item was ever sent to kitchen (including voided ones)
            has_sent_items = bill.items.filter(status='sent').exists()
        else:
            # Bill not found or not open, clear session
            logger.warning(f"POS Main - bill_id {bill_id} not found or not open, clearing session")
            request.session.pop('active_bill_id', None)
            request.session.modified = True
    
    held_count = Bill.objects.filter(outlet=outlet, status='hold').count()
    
    context = {
        'categories': categories,
        'tables': tables,
        'products': products,
        'bill': bill,
        'active_items_count': active_items_count,
        'has_sent_items': has_sent_items,
        'held_count': held_count,
        'store_config': store_config,
    }
    return render(request, 'pos/main.html', context)


@login_required
def product_list(request):
    """Product list partial - HTMX"""
    outlet = request.user.outlet
    category_id = request.GET.get('category')
    search_query = request.GET.get('search', '').strip()
    
    # Order products by category sort_order and name for better grouping
    products = Product.objects.filter(
        category__outlet=outlet, 
        is_active=True
    ).select_related('category', 'category__parent').prefetch_related('modifiers').order_by(
        'category__sort_order', 
        'category__name', 
        'name'
    )
    
    if category_id and category_id != 'all':
        products = products.filter(category_id=category_id)
    
    # Search filter
    if search_query:
        products = products.filter(name__icontains=search_query)
    
    # Get active bill from session
    bill_id = request.session.get('active_bill_id')
    bill = None
    if bill_id:
        bill = Bill.objects.filter(id=bill_id, status='open').first()
    
    is_modal = request.GET.get('modal') == '1'
    template = 'pos/partials/product_grid_mini.html' if is_modal else 'pos/partials/product_grid.html'
    
    return render(request, template, {'products': products, 'bill': bill})


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
            terminal=getattr(request, 'terminal', None),  # Auto-assign terminal from middleware
        )
        
        if table_id:
            Table.objects.filter(id=table_id).update(status='occupied')
        
        request.session['active_bill_id'] = bill.id
        
        BillLog.objects.create(bill=bill, action='open', user=request.user)
    
    # Close modal and refresh page via client-side redirect
    response = HttpResponse('<script>closeModal(); window.location.reload();</script>')
    return response


@login_required
@require_http_methods(["GET"])
def add_item_modal(request, bill_id, product_id):
    """Show simple add item modal with quantity and notes"""
    bill = get_object_or_404(Bill, id=bill_id, status__in=['open', 'hold'])
    product = get_object_or_404(Product, id=product_id)
    
    # Get modifiers for this product
    modifiers = product.modifiers.filter(outlet=request.user.outlet).prefetch_related('options')
    
    return render(request, 'pos/partials/add_item_modal.html', {
        'bill': bill,
        'product': product,
        'modifiers': modifiers,
    })


@login_required
@require_http_methods(["POST"])
def add_item(request, bill_id):
    """Add item to bill - HTMX"""
    try:
        # Get bill - allow both 'open' and 'hold' status, but prefer active bill from session
        active_bill_id = request.session.get('active_bill_id')
        bill = None
        
        if active_bill_id:
            # Use active bill from session if available
            try:
                bill = Bill.objects.select_related('table', 'table__area', 'outlet').get(id=active_bill_id, status__in=['open', 'hold'])
                # If bill was on hold, resume it to open
                if bill.status == 'hold':
                    bill.status = 'open'
                    bill.save()
            except Bill.DoesNotExist:
                # Active bill from session no longer exists, clear it
                request.session.pop('active_bill_id', None)
                # Try bill_id from URL as fallback
                try:
                    bill = Bill.objects.select_related('table', 'table__area', 'outlet').get(id=bill_id, status__in=['open', 'hold'])
                    # If bill was on hold, resume it to open
                    if bill.status == 'hold':
                        bill.status = 'open'
                        bill.save()
                        # Set as active bill
                        request.session['active_bill_id'] = bill.id
                        request.session.modified = True
                except Bill.DoesNotExist:
                    # No valid bill found - return empty bill panel
                    response = render_bill_panel(request, None)
                    return trigger_client_event(response, 'billNotFound', {'message': 'Bill not found or already closed. Please select a table to start new order.'})
        else:
            try:
                bill = Bill.objects.select_related('table', 'table__area', 'outlet').get(id=bill_id, status__in=['open', 'hold'])
                # If bill was on hold, resume it to open
                if bill.status == 'hold':
                    bill.status = 'open'
                    bill.save()
                    # Set as active bill
                    request.session['active_bill_id'] = bill.id
                    request.session.modified = True
            except Bill.DoesNotExist:
                # No valid bill found - return empty bill panel
                response = render_bill_panel(request, None)
                return trigger_client_event(response, 'billNotFound', {'message': 'Bill not found or already closed. Please select a table to start new order.'})
        
        product_id = request.POST.get('product_id')
        
        # DEBUG: Log what we received
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"=== ADD ITEM DEBUG ===")
        logger.info(f"Received product_id: '{product_id}' (type: {type(product_id)})")
        logger.info(f"All POST data: {dict(request.POST)}")
        
        # Handle product_id conversion
        if product_id:
            original_id = product_id
            try:
                # Remove thousand separator (dot) and convert to int
                # Example: "2.265" -> "2265" -> 2265
                product_id = str(product_id).replace('.', '').replace(',', '')
                product_id = int(product_id)
                logger.info(f"Converted '{original_id}' -> {product_id} (int)")
            except (ValueError, TypeError) as e:
                logger.error(f"Error converting product_id '{original_id}': {e}")
                return HttpResponse(
                    f'<div class="p-3 bg-red-100 text-red-700 rounded">Invalid product ID: {original_id}</div>', 
                    status=400
                )
        else:
            logger.error("No product_id provided in POST data")
            return HttpResponse(
                '<div class="p-3 bg-red-100 text-red-700 rounded">Product ID is required</div>', 
                status=400
            )
        
        quantity = int(request.POST.get('quantity', 1))
        notes = request.POST.get('notes', '')
        modifiers = request.POST.getlist('modifiers')
        
        logger.info(f"Looking for Product with id={product_id}")
        logger.info(f"Received modifiers: {modifiers}")
        
        try:
            product = Product.objects.get(id=product_id)
            logger.info(f"Found product: {product.name}")
        except Product.DoesNotExist:
            logger.error(f"Product with id={product_id} not found in database")
            # List available products for debugging
            available_ids = list(Product.objects.values_list('id', flat=True)[:10])
            logger.error(f"Available product IDs (first 10): {available_ids}")
            return HttpResponse(
                f'<div class="p-3 bg-red-100 text-red-700 rounded">Product not found (ID: {product_id})</div>', 
                status=404
            )
        
        modifier_price = Decimal('0')
        modifier_data = []
        for mod_id in modifiers:
            try:
                # Convert modifier ID (remove thousand separators and convert to int)
                mod_id_clean = str(mod_id).replace('.', '').replace(',', '')
                mod_id_int = int(mod_id_clean)
                logger.info(f"Converting modifier ID '{mod_id}' -> {mod_id_int}")
                
                opt = ModifierOption.objects.get(id=mod_id_int)
                modifier_price += opt.price_adjustment
                modifier_data.append({
                    'id': opt.id,
                    'name': opt.name,
                    'price': float(opt.price_adjustment)
                })
            except (ValueError, TypeError) as e:
                logger.error(f"Error converting modifier ID '{mod_id}': {e}")
                continue
            except ModifierOption.DoesNotExist:
                logger.error(f"ModifierOption with id={mod_id_int} not found")
                continue
        
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
        
        response = render_bill_panel(request, bill)
        return trigger_client_event(response, 'itemAdded')
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error adding item: {str(e)}", exc_info=True)
        return HttpResponse(f'<div class="p-3 bg-red-100 text-red-700 rounded">Error: {str(e)}</div>', status=500)


@login_required
def confirm_remove_item(request, item_id):
    """Show confirm remove item modal - HTMX"""
    item = get_object_or_404(BillItem, id=item_id, is_void=False)
    return render(request, 'pos/partials/confirm_remove_modal.html', {'item': item})


@login_required
@require_http_methods(["GET", "POST", "DELETE"])
def void_item(request, item_id):
    """Void/Remove item - DELETE for pending items (no PIN), GET+POST for sent items (with PIN)"""
    item = get_object_or_404(BillItem, id=item_id)
    
    # DELETE method - Simple remove for PENDING items only (no PIN required)
    if request.method == 'DELETE':
        if item.status != 'pending':
            return HttpResponse('Cannot delete sent items. Use void with supervisor PIN instead.', status=403)
        
        # Simply mark as void for pending items
        item.is_void = True
        item.void_reason = 'Removed before sending to kitchen'
        item.void_by = request.user
        item.save()
        
        # Recalculate bill totals
        item.bill.calculate_totals()
        
        # Create audit log
        BillLog.objects.create(
            bill=item.bill,
            action='remove_item',
            user=request.user,
            details={
                'product': item.product.name,
                'status': 'pending',
                'note': 'Item removed before kitchen preparation'
            }
        )
        
        # Refresh bill with table relation
        bill = Bill.objects.select_related('table', 'table__area').get(id=item.bill.id)
        return render_bill_panel(request, bill)
    
    # GET method - Show PIN modal for SENT items
    if request.method == 'GET':
        return render(request, 'pos/partials/void_item_pin_modal.html', {'item': item})
    
    # POST method - Process void with PIN verification for SENT items
    supervisor_pin = request.POST.get('supervisor_pin', '')
    reason = request.POST.get('reason', '')
    
    if not supervisor_pin or len(supervisor_pin) != 6:
        return HttpResponse('PIN must be 6 digits', status=400)
    
    if not reason.strip():
        return HttpResponse('Reason is required', status=400)
    
    # Verify PIN belongs to supervisor/manager/admin
    from apps.core.models import User
    try:
        supervisor = User.objects.get(
            pin=supervisor_pin,
            role__in=['supervisor', 'manager', 'admin', 'owner']
        )
    except User.DoesNotExist:
        return HttpResponse('Invalid PIN or insufficient permissions', status=403)
    
    # Check if item is already processed and user doesn't have permission
    if item.status != 'pending' and not supervisor.has_permission('void_item'):
        return HttpResponse('This item has been processed and cannot be voided', status=403)
    
    # Void the item
    item.is_void = True
    item.void_reason = reason
    item.void_by = supervisor  # Record who approved (supervisor, not cashier)
    item.save()
    
    # Recalculate bill totals
    item.bill.calculate_totals()
    
    # Create audit log
    BillLog.objects.create(
        bill=item.bill,
        action='void_item',
        user=request.user,  # Cashier who initiated
        details={
            'product': item.product.name,
            'reason': reason,
            'approved_by': supervisor.get_full_name(),
            'approved_by_pin': supervisor_pin[:2] + '****'  # Partial PIN for audit
        }
    )
    
    # Refresh bill with table relation
    bill = Bill.objects.select_related('table', 'table__area').get(id=item.bill.id)
    return render_bill_panel(request, bill)


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
    
    # Refresh bill with table relation
    bill = Bill.objects.select_related('table', 'table__area').get(id=item.bill.id)
    return render_bill_panel(request, bill)


@login_required
@require_http_methods(["GET"])
def edit_item_modal(request, item_id):
    """Show edit item modal with current modifiers pre-selected"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        item = get_object_or_404(BillItem.objects.select_related('product', 'bill'), id=item_id, is_void=False)
        
        # Get modifiers for this product
        modifiers = item.product.modifiers.filter(outlet=request.user.outlet).prefetch_related('options')
        
        # Get currently selected modifier option IDs
        selected_modifier_ids = [mod['id'] for mod in item.modifiers] if item.modifiers else []
        
        logger.info(f"Edit item {item_id}: status={item.status}, selected_modifiers={selected_modifier_ids}")
        
        return render(request, 'pos/partials/edit_item_modal.html', {
            'item': item,
            'modifiers': modifiers,
            'selected_modifier_ids': selected_modifier_ids,
        })
    except Exception as e:
        logger.error(f"Error loading edit modal for item {item_id}: {str(e)}")
        return HttpResponse(f"Error: {str(e)}", status=400)


@login_required
@require_http_methods(["POST"])
def update_item(request, item_id):
    """Update item with new modifiers, quantity, and notes - HTMX"""
    import logging
    from decimal import Decimal
    logger = logging.getLogger(__name__)
    
    try:
        # Log all POST data first
        logger.info(f"=== UPDATE ITEM {item_id} ===")
        logger.info(f"POST data: {dict(request.POST)}")
        
        item = get_object_or_404(BillItem.objects.select_related('product', 'bill'), id=item_id, is_void=False)
        
        # Check if item can be edited
        if item.status != 'pending':
            logger.warning(f"Cannot edit item {item_id} with status {item.status}")
            return HttpResponse(f"Cannot edit item with status: {item.status}. Only pending items can be edited.", status=400)
        
        # Get form data
        quantity = int(request.POST.get('quantity', 1))
        notes = request.POST.get('notes', '').strip()
        modifiers = request.POST.getlist('modifiers')
        
        logger.info(f"Parsed: quantity={quantity}, notes={notes}, modifiers={modifiers}")
        
        # Update quantity and notes
        item.quantity = max(1, quantity)
        item.notes = notes  # Keep as empty string if blank, don't set to None
        
        # Process modifiers
        modifier_data = []
        modifier_total = Decimal('0')
        
        if modifiers:
            from apps.core.models import ModifierOption
            
            for mod_id in modifiers:
                try:
                    # Clean modifier ID (remove separators)
                    mod_id_clean = str(mod_id).replace('.', '').replace(',', '')
                    mod_id_int = int(mod_id_clean)
                    
                    option = ModifierOption.objects.get(id=mod_id_int)
                    modifier_total += option.price_adjustment
                    modifier_data.append({
                        'id': option.id,
                        'name': option.name,
                        'price': float(option.price_adjustment)
                    })
                    logger.info(f"Added modifier: {option.name} (${option.price_adjustment})")
                except ModifierOption.DoesNotExist:
                    logger.warning(f"Modifier option {mod_id} not found")
                    continue
                except (ValueError, TypeError) as e:
                    logger.error(f"Invalid modifier ID: {mod_id} - {str(e)}")
                    continue
        
        # Calculate new price with modifiers
        item.unit_price = item.product.price
        item.modifier_price = modifier_total
        item.modifiers = modifier_data
        
        logger.info(f"Final price: unit={item.unit_price}, modifiers={modifier_total}, total={item.unit_price + modifier_total}")
        
        item.save()
        item.bill.calculate_totals()
        
        logger.info(f"Item {item_id} updated successfully")
        
        # Refresh bill with table relation
        bill = Bill.objects.select_related('table', 'table__area').get(id=item.bill.id)
        return render_bill_panel(request, bill)
        
    except Exception as e:
        logger.error(f"Error updating item {item_id}: {str(e)}", exc_info=True)
        return HttpResponse(f"Error updating item: {str(e)}", status=400)
        
    except Exception as e:
        logger.error(f"Error updating item {item_id}: {str(e)}")
        return HttpResponse(f"Error: {str(e)}", status=400)


@login_required
@require_http_methods(["GET"])
def hold_modal(request, bill_id):
    """Show hold bill confirmation modal - HTMX"""
    bill = get_object_or_404(Bill, id=bill_id, status__in=['open', 'hold'])
    return render(request, 'pos/partials/confirm_hold_modal.html', {'bill': bill})


@login_required
@require_http_methods(["POST"])
def cancel_empty_bill(request, bill_id):
    """Cancel empty bill and clear table if exists"""
    bill = get_object_or_404(Bill, id=bill_id, status__in=['open', 'hold'])
    
    # Check if bill is empty
    if bill.items.filter(is_void=False).exists():
        return HttpResponse("Cannot cancel bill with items", status=400)
    
    with transaction.atomic():
        # Clear table if exists
        if bill.table:
            bill.table.status = 'available'
            bill.table.current_bill = None
            bill.table.save()
        
        # Log the cancellation
        BillLog.objects.create(
            bill=bill,
            action='cancel_empty',
            user=request.user,
            details={'reason': 'Empty bill cancelled by user'}
        )
        
        # Delete the bill
        bill.delete()
    
    # Clear session
    request.session.pop('active_bill_id', None)
    
    # Return empty bill panel
    response = render_bill_panel(request, None)
    return trigger_client_event(response, 'billCancelled')


@login_required
@require_http_methods(["POST"])
def hold_bill(request, bill_id):
    """Hold bill - HTMX"""
    bill = get_object_or_404(Bill, id=bill_id, status__in=['open', 'hold'])
    
    reason = request.POST.get('reason', '')
    other_reason = request.POST.get('other_reason', '')
    
    # Use other_reason if "lainnya" selected
    hold_reason = other_reason if reason == 'lainnya' else reason
    
    # If already on hold, update the reason; otherwise set to hold
    if bill.status == 'hold':
        # Update hold reason
        if hold_reason:
            bill.notes = f"Hold: {hold_reason}"
        bill.save()
    else:
        # Set to hold
        bill.status = 'hold'
        if hold_reason:
            bill.notes = f"Hold: {hold_reason}" if not bill.notes else f"{bill.notes}\nHold: {hold_reason}"
        bill.save()
        
        if bill.table:
            bill.table.status = 'occupied'
            bill.table.save()
        
        request.session.pop('active_bill_id', None)
    
    BillLog.objects.create(
        bill=bill, 
        action='hold', 
        user=request.user,
        details={'reason': hold_reason} if hold_reason else {}
    )
    
    response = render_bill_panel(request, None)
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
    
    return render_bill_panel(request, bill)


@login_required
@require_http_methods(["DELETE", "POST"])
def cancel_bill(request, bill_id):
    """Cancel/Void bill - DELETE for pending-only bills, POST for bills with sent items (requires PIN)"""
    bill = get_object_or_404(Bill, id=bill_id, status__in=['open', 'hold'])
    
    # DELETE method - Simple void for bills with ONLY pending items (no PIN required)
    if request.method == 'DELETE':
        has_sent_items = bill.items.filter(status='sent', is_void=False).exists()
        if has_sent_items:
            return HttpResponse('Cannot delete bills with sent items. Use POST with supervisor PIN.', status=403)
        
        # Simple void for pending-only bills
        reason = request.GET.get('reason', '') or request.POST.get('reason', '') or 'Cancelled before kitchen preparation'
        bill.status = 'cancelled'
        bill.notes = f"Cancelled: {reason}"
        bill.save()
        
        if bill.table:
            bill.table.status = 'available'
            bill.table.save()
        
        # Clear active bill from session
        request.session.pop('active_bill_id', None)
        
        # Log the action
        BillLog.objects.create(
            bill=bill,
            action='cancel_bill',
            user=request.user,
            details={'reason': reason, 'note': 'Cancelled before kitchen preparation'}
        )
        
        # Get next available held bill to open
        next_bill = Bill.objects.filter(
            outlet=request.user.outlet,
            status='hold'
        ).order_by('-created_at').first()
        
        if next_bill:
            # Resume next held bill
            next_bill.status = 'open'
            next_bill.save()
            request.session['active_bill_id'] = next_bill.id
            bill_to_show = next_bill
        else:
            bill_to_show = None
        
        response = render(request, 'pos/partials/bill_panel.html', {'bill': bill_to_show})
        return trigger_client_event(response, 'billCancelled')
    
    # POST method - Void with PIN verification for bills with SENT items
    supervisor_pin = request.POST.get('supervisor_pin', '')
    reason = request.POST.get('reason', '')
    
    if not supervisor_pin or len(supervisor_pin) != 6:
        return HttpResponse('PIN must be 6 digits', status=400)
    
    if not reason.strip():
        return HttpResponse('Reason is required', status=400)
    
    # Verify PIN belongs to supervisor/manager/admin
    from apps.core.models import User
    try:
        supervisor = User.objects.get(
            pin=supervisor_pin,
            role__in=['supervisor', 'manager', 'admin', 'owner']
        )
    except User.DoesNotExist:
        return HttpResponse('Invalid PIN or insufficient permissions', status=403)
    
    # Void the bill
    bill.status = 'cancelled'
    bill.notes = f"Voided by {supervisor.get_full_name()}: {reason}"
    bill.save()
    
    if bill.table:
        bill.table.status = 'available'
        bill.table.save()
    
    # Clear active bill from session
    request.session.pop('active_bill_id', None)
    
    # Create audit log
    BillLog.objects.create(
        bill=bill,
        action='void_bill',
        user=request.user,  # Cashier who initiated
        details={
            'reason': reason,
            'approved_by': supervisor.get_full_name(),
            'approved_by_pin': supervisor_pin[:2] + '****',
            'total_amount': float(bill.total)
        }
    )
    
    # Get next available held bill to open
    next_bill = Bill.objects.filter(
        outlet=request.user.outlet,
        status='hold'
    ).order_by('-created_at').first()
    
    if next_bill:
        # Resume next held bill
        next_bill.status = 'open'
        next_bill.save()
        request.session['active_bill_id'] = next_bill.id
        bill_to_show = next_bill
    else:
        bill_to_show = None
    
    response = render(request, 'pos/partials/bill_panel.html', {'bill': bill_to_show})
    return trigger_client_event(response, 'billVoided')


@login_required
def confirm_void_modal(request, bill_id):
    """Show void confirmation modal - checks if PIN required based on sent items"""
    bill = get_object_or_404(Bill, id=bill_id, status__in=['open', 'hold'])
    
    # Check if there are any sent items (already in kitchen)
    has_sent_items = bill.items.filter(status='sent', is_void=False).exists()
    
    if has_sent_items:
        # Show PIN modal for bills with sent items
        return render(request, 'pos/partials/void_bill_pin_modal.html', {'bill': bill})
    else:
        # Show simple confirmation for pending-only bills
        return render(request, 'pos/partials/confirm_void_modal.html', {'bill': bill})


@login_required
def held_bills(request):
    """List held bills - HTMX"""
    bills = Bill.objects.filter(
        outlet=request.user.outlet,
        status='hold'
    ).select_related('table', 'created_by').prefetch_related('items__product').order_by('-created_at')
    
    return render(request, 'pos/partials/held_bills_list.html', {'bills': bills})


@login_required
@require_http_methods(["POST"])
def send_to_kitchen(request, bill_id):
    """Send pending items to kitchen - HTMX"""
    bill = get_object_or_404(Bill, id=bill_id)
    
    # CRITICAL: Only get items that are pending (not yet sent)
    pending_items = bill.items.filter(status='pending', is_void=False)
    
    if not pending_items.exists():
        # Don't remove bill panel, just show alert and return same panel
        response = render_bill_panel(request, bill)
        response['HX-Trigger'] = '{"showNotification": {"message": "Tidak ada item baru untuk dikirim", "type": "warning"}}'
        return response
    
    try:
        from collections import defaultdict
        from apps.kitchen.services import print_kitchen_order, create_kitchen_order
        
        # Group items by station
        grouped = defaultdict(list)
        for item in pending_items:
            grouped[item.product.printer_target].append(item)
        
        print(f"DEBUG: Sending {pending_items.count()} pending items to kitchen")
        
        # IMPORTANT: Update status BEFORE creating kitchen orders to prevent race condition
        pending_items.update(status='sent')
        
        for station, items in grouped.items():
            if station != 'none':
                # Use get_or_create pattern to prevent duplicates
                kitchen_order = create_kitchen_order(bill, station, items)
                print(f"DEBUG: KitchenOrder {kitchen_order.id} for station {station}, bill {bill.bill_number}, created: {kitchen_order.status}")
                
                try:
                    print_kitchen_order(bill, station, items)
                except Exception as e:
                    print(f"Print error (will continue): {e}")
        
        BillLog.objects.create(
            bill=bill, 
            action='send_kitchen', 
            user=request.user,
            details={'items_count': len(pending_items)}
        )
        
        response = render_bill_panel(request, bill)
        return trigger_client_event(response, 'sentToKitchen')
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HttpResponse(f'<div class="p-3 bg-red-100 text-red-700 rounded">Error: {str(e)}</div>')


@login_required
def payment_modal(request, bill_id):
    """Payment modal - HTMX"""
    bill = get_object_or_404(Bill, id=bill_id)
    context = {
        'bill': bill,
        'amount_int': int(bill.get_remaining()),
        'total_int': int(bill.total),
        'paid_int': int(bill.get_paid_amount())
    }
    return render(request, 'pos/partials/payment_modal.html', context)


@login_required
@require_http_methods(["POST"])
def process_payment(request, bill_id):
    """Process payment - supports split payment with multiple payment methods"""
    bill = get_object_or_404(Bill, id=bill_id, status='open')
    
    # Check if this is a split payment (multiple payment methods)
    payment_count = 0
    total_paid = Decimal('0')
    
    # Process split payments array
    for key in request.POST.keys():
        if key.startswith('payments[') and key.endswith('][method]'):
            index = key.split('[')[1].split(']')[0]
            method = request.POST.get(f'payments[{index}][method]')
            amount = Decimal(request.POST.get(f'payments[{index}][amount]', 0))
            reference = request.POST.get(f'payments[{index}][reference]', '')
            
            if amount > 0:
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
                    details={'method': method, 'amount': float(amount), 'split': True}
                )
                
                total_paid += amount
                payment_count += 1
    
    # Process current payment (if any)
    method = request.POST.get('method')
    amount = Decimal(request.POST.get('amount', 0))
    reference = request.POST.get('reference', '')
    
    if amount > 0:
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
            details={
                'method': method, 
                'amount': float(amount),
                'split': payment_count > 0
            }
        )
        
        total_paid += amount
        payment_count += 1
    
    # Check if bill is fully paid
    if bill.get_remaining() <= 0:
        bill.status = 'paid'
        bill.closed_by = request.user
        bill.closed_at = timezone.now()
        bill.save()
        
        # Update table status and unjoin if part of group
        if bill.table:
            # Get all tables in the same group
            from apps.tables.models import TableGroup
            table_group = bill.table.table_group
            
            if table_group:
                # Get all tables in this group
                joined_tables = Table.objects.filter(table_group=table_group)
                # Clear group and set status to dirty
                joined_tables.update(table_group=None, status='dirty')
                # Delete the group
                table_group.delete()
            else:
                # Single table, just update status
                bill.table.status = 'dirty'
                bill.table.save()
        
        # Check if this was a split bill and auto-resume original bill
        split_original_bill_id = request.session.pop('split_original_bill_id', None)
        if split_original_bill_id:
            # Check if original bill still exists and is open or hold
            original_bill = Bill.objects.filter(id=split_original_bill_id, status__in=['open', 'hold']).first()
            if original_bill:
                # Set original bill as active
                request.session['active_bill_id'] = original_bill.id
                request.session.modified = True
            else:
                # Original bill already paid or doesn't exist, clear session
                request.session.pop('active_bill_id', None)
        else:
            # Normal flow - clear active bill from session
            request.session.pop('active_bill_id', None)
        
        BillLog.objects.create(
            bill=bill, 
            action='close', 
            user=request.user,
            details={
                'total_payments': payment_count,
                'split_payment': payment_count > 1
            }
        )
        
        # Print receipt
        from apps.pos.services import print_receipt
        try:
            print_receipt(bill)
        except:
            pass  # Don't fail if printing fails
        
        response = render(request, 'pos/partials/payment_success.html', {
            'bill': bill,
            'split_payment': payment_count > 1,
            'payment_count': payment_count
        })
        return trigger_client_event(response, 'paymentComplete')
    
    # Still has remaining balance
    return render(request, 'pos/partials/payment_modal.html', {'bill': bill})


@login_required
def split_bill_modal(request, bill_id):
    """Split bill modal - Enhanced UI"""
    bill = get_object_or_404(Bill, id=bill_id, status__in=['open', 'hold'])
    items = bill.items.filter(is_void=False)
    tables = Table.objects.filter(area__outlet=bill.outlet, status='available')
    
    context = {
        'bill': bill,
        'items': items,
        'tables': tables,
    }
    return render(request, 'pos/partials/split_bill_modal.html', context)


@login_required
@require_http_methods(["POST"])
def split_bill(request, bill_id):
    """Split bill into multiple bills - Enhanced with qty split support"""
    original_bill = get_object_or_404(Bill, id=bill_id, status__in=['open', 'hold'])
    split_items = request.POST.getlist('split_items[]')
    new_table_id = request.POST.get('new_table_id')
    guest_count = int(request.POST.get('guest_count', 1))
    
    if not split_items:
        return JsonResponse({'error': 'Please select items to split'}, status=400)
    
    with transaction.atomic():
        # Create new bill
        new_bill = Bill.objects.create(
            outlet=original_bill.outlet,
            table_id=new_table_id if new_table_id else original_bill.table_id,
            bill_type=original_bill.bill_type,
            guest_count=guest_count,
            created_by=request.user,
            notes=f"Split from {original_bill.bill_number}"
        )
        
        moved_count = 0
        # Process each selected item with qty split support
        for item_id in split_items:
            item = BillItem.objects.get(id=item_id, bill=original_bill)
            split_qty_key = f'split_qty_{item_id}'
            split_qty = int(request.POST.get(split_qty_key, item.quantity))
            
            if split_qty >= item.quantity:
                # Move entire item to new bill
                item.bill = new_bill
                item.save()
                moved_count += 1
            else:
                # Split qty: create new item in new bill with split qty
                BillItem.objects.create(
                    bill=new_bill,
                    product=item.product,
                    quantity=split_qty,
                    unit_price=item.unit_price,
                    modifier_price=item.modifier_price,
                    notes=item.notes,
                    modifiers=item.modifiers,
                    status=item.status,
                    created_by=request.user
                )
                
                # Reduce qty in original bill
                item.quantity -= split_qty
                item.save()
                moved_count += 1
        
        # Recalculate totals
        original_bill.calculate_totals()
        new_bill.calculate_totals()
        
        # Keep both bills as 'open' (not held) so both can be paid immediately
        # This is the key change - both bills stay active for immediate payment
        new_bill.status = 'open'
        new_bill.save()
        
        # Set new bill as active in session for immediate payment
        # After payment of new bill, user will return to original bill via split_original_bill_id
        request.session['active_bill_id'] = new_bill.id
        request.session['split_original_bill_id'] = original_bill.id  # Store for after payment
        request.session.modified = True
        
        # Update table status if different
        if new_table_id and new_table_id != str(original_bill.table_id):
            new_table = Table.objects.get(id=new_table_id)
            new_table.status = 'occupied'
            new_table.save()
        
        # Log actions
        BillLog.objects.create(
            bill=original_bill,
            action='split_bill',
            user=request.user,
            details={
                'new_bill': new_bill.bill_number,
                'items_moved': moved_count,
                'new_table': new_bill.table.number if new_bill.table else None
            }
        )
        
        BillLog.objects.create(
            bill=new_bill,
            action='open',
            user=request.user,
            details={'split_from': original_bill.bill_number}
        )
    
    return JsonResponse({
        'success': True,
        'message': f'Bill split successfully! {moved_count} items moved',
        'original_bill': {
            'id': original_bill.id,
            'number': original_bill.bill_number,
            'total': float(original_bill.total),
            'items_count': original_bill.items.count()
        },
        'new_bill': {
            'id': new_bill.id,
            'number': new_bill.bill_number,
            'total': float(new_bill.total),
            'items_count': new_bill.items.count()
        }
    })


@login_required
def merge_bills_modal(request, bill_id):
    """Merge bills modal - Select bills to merge"""
    current_bill = get_object_or_404(Bill, id=bill_id, outlet=request.user.outlet)
    outlet = request.user.outlet
    open_bills = Bill.objects.filter(
        outlet=outlet,
        status='open'
    ).exclude(id=bill_id).prefetch_related('items').order_by('-created_at')[:20]
    
    context = {
        'current_bill': current_bill,
        'open_bills': open_bills,
    }
    return render(request, 'pos/partials/merge_bills_modal.html', context)


@login_required
@require_http_methods(["POST"])
def merge_bills(request):
    """Merge multiple bills into one"""
    bill_ids = request.POST.getlist('bill_ids')
    target_bill_id = request.POST.get('target_bill_id')
    
    if len(bill_ids) < 1:
        return JsonResponse({'error': 'Please select at least 1 bill to merge'}, status=400)
    
    if not target_bill_id:
        return JsonResponse({'error': 'Please select target bill'}, status=400)
    
    with transaction.atomic():
        target_bill = get_object_or_404(Bill, id=target_bill_id, status__in=['open', 'hold'])
        source_bills = Bill.objects.filter(id__in=bill_ids, status='open').exclude(id=target_bill_id)
        
        merged_count = 0
        merged_bills = []
        
        for source_bill in source_bills:
            # Move all items to target bill
            items = source_bill.items.filter(is_void=False)
            items_count = items.count()
            items.update(bill=target_bill)
            
            merged_count += items_count
            merged_bills.append(source_bill.bill_number)
            
            # Log source bill closure
            BillLog.objects.create(
                bill=source_bill,
                action='merge_bill',
                user=request.user,
                details={
                    'merged_into': target_bill.bill_number,
                    'items_moved': items_count
                }
            )
            
            # Close source bill
            source_bill.status = 'cancelled'
            source_bill.notes += f"\nMerged into {target_bill.bill_number}"
            source_bill.save()
            
            # Free up source table if different
            if source_bill.table and source_bill.table != target_bill.table:
                source_bill.table.status = 'available'
                source_bill.table.save()
        
        # Update target bill guest count
        total_guests = sum([b.guest_count for b in source_bills]) + target_bill.guest_count
        target_bill.guest_count = total_guests
        target_bill.calculate_totals()
        
        # Log merge on target bill
        BillLog.objects.create(
            bill=target_bill,
            action='merge_bill',
            user=request.user,
            details={
                'merged_from': merged_bills,
                'total_items_added': merged_count,
                'total_guests': total_guests
            }
        )
    
    return JsonResponse({
        'success': True,
        'message': f'{len(merged_bills)} bills merged into {target_bill.bill_number}',
        'target_bill': target_bill.bill_number,
        'merged_bills': merged_bills,
        'total_items': merged_count
    })


@login_required
def move_table_modal(request, bill_id):
    """Move table modal"""
    bill = get_object_or_404(Bill, id=bill_id, status__in=['open', 'hold'])
    tables = Table.objects.filter(
        area__outlet=bill.outlet,
        status__in=['available', 'reserved']
    ).exclude(id=bill.table_id).order_by('area__name', 'number')
    
    context = {
        'bill': bill,
        'tables': tables,
    }
    return render(request, 'pos/partials/move_table_modal.html', context)


@login_required
@require_http_methods(["POST"])
def move_table(request, bill_id):
    """Move bill to different table"""
    bill = get_object_or_404(Bill, id=bill_id, status__in=['open', 'hold'])
    new_table_id = request.POST.get('new_table_id') or request.POST.get('table_id')
    
    if not new_table_id:
        return JsonResponse({'error': 'Please select a table'}, status=400)
    
    new_table = get_object_or_404(Table, id=new_table_id)
    
    if new_table.status not in ['available', 'reserved']:
        return JsonResponse({'error': 'Table is not available'}, status=400)
    
    with transaction.atomic():
        old_table = bill.table
        old_table_number = old_table.number if old_table else None
        
        # Update old table status
        if old_table:
            old_table.status = 'available'
            old_table.save()
        
        # Update bill table
        bill.table = new_table
        bill.save()
        
        # Update new table status
        new_table.status = 'occupied'
        new_table.save()
        
        # Log action
        BillLog.objects.create(
            bill=bill,
            action='move_table',
            user=request.user,
            details={
                'old_table': old_table_number,
                'new_table': new_table.number
            }
        )
    
    # Return JSON response
    return JsonResponse({
        'success': True,
        'message': f'Bill moved from Table {old_table_number} to Table {new_table.number}'
    })


@login_required
def transfer_bill_modal(request, bill_id):
    """Transfer bill to another cashier modal"""
    bill = get_object_or_404(Bill, id=bill_id, status__in=['open', 'hold'])
    cashiers = request.user.__class__.objects.filter(
        outlet=bill.outlet,
        role__in=['cashier', 'waiter', 'manager']
    ).exclude(id=request.user.id).order_by('username')
    
    context = {
        'bill': bill,
        'cashiers': cashiers,
    }
    return render(request, 'pos/partials/transfer_bill_modal.html', context)


@login_required
@require_http_methods(["POST"])
def transfer_bill(request, bill_id):
    """Transfer bill to another cashier"""
    bill = get_object_or_404(Bill, id=bill_id, status__in=['open', 'hold'])
    new_cashier_id = request.POST.get('new_cashier_id')
    notes = request.POST.get('notes', '')
    
    if not new_cashier_id:
        return JsonResponse({'error': 'Please select a cashier'}, status=400)
    
    new_cashier = get_object_or_404(request.user.__class__, id=new_cashier_id)
    
    with transaction.atomic():
        old_cashier = bill.created_by
        
        # Update bill creator
        bill.created_by = new_cashier
        if notes:
            bill.notes += f"\n{notes}"
        bill.save()
        
        # Log action
        BillLog.objects.create(
            bill=bill,
            action='transfer',
            user=request.user,
            details={
                'from_cashier': old_cashier.username,
                'to_cashier': new_cashier.username,
                'notes': notes
            }
        )
    
    return JsonResponse({
        'success': True,
        'message': f'Bill transferred to {new_cashier.get_full_name() or new_cashier.username}',
        'new_cashier': new_cashier.username
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


# ============================================================
# SESSION & SHIFT MANAGEMENT
# ============================================================

@login_required
@require_http_methods(['POST'])
def session_open(request):
    """Open new store session (business date)"""
    store_config = StoreConfig.get_current()
    
    # Check if session already open
    current_session = StoreSession.get_current(store_config)
    if current_session:
        return JsonResponse({
            'error': 'Session already open',
            'session_id': str(current_session.id),
            'business_date': str(current_session.business_date)
        }, status=400)
    
    # Get business date from request or use today
    business_date = request.POST.get('business_date', timezone.now().date())
    notes = request.POST.get('notes', '')
    
    # Create new session
    session = StoreSession.objects.create(
        store=store_config,
        business_date=business_date,
        opened_by=request.user,
        is_current=True,
        settings={
            'notes': notes,
            'opened_from_terminal': str(request.terminal.id) if hasattr(request, 'terminal') else None
        }
    )
    
    return JsonResponse({
        'success': True,
        'message': f'Session opened for {business_date}',
        'session_id': str(session.id),
        'business_date': str(session.business_date)
    })


@login_required
def shift_open_form(request):
    """Show shift open modal"""
    store_config = StoreConfig.get_current()
    current_session = StoreSession.get_current(store_config)
    
    if not current_session:
        return render(request, 'pos/partials/session_required.html')
    
    # Check if user already has open shift
    existing_shift = CashierShift.objects.filter(
        cashier=request.user,
        status='open'
    ).first()
    
    if existing_shift:
        return JsonResponse({
            'error': 'You already have an open shift',
            'shift_id': str(existing_shift.id)
        }, status=400)
    
    context = {
        'current_session': current_session,
        'terminal': request.terminal if hasattr(request, 'terminal') else None
    }
    return render(request, 'pos/partials/shift_open_modal.html', context)


@login_required
@require_http_methods(['POST'])
def shift_open(request):
    """Open new cashier shift"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        store_config = StoreConfig.get_current()
        current_session = StoreSession.get_current(store_config)
        
        logger.info(f"Shift open request - User: {request.user}, Session: {current_session}")
        
        if not current_session:
            return JsonResponse({'error': 'No active session. Open session first.'}, status=400)
        
        # Check existing shift
        existing_shift = CashierShift.objects.filter(
            cashier=request.user,
            status='open'
        ).first()
        
        if existing_shift:
            return JsonResponse({
                'error': 'You already have an open shift',
                'shift_id': str(existing_shift.id)
            }, status=400)
        
        opening_cash = Decimal(request.POST.get('opening_cash', '0'))
        notes = request.POST.get('notes', '')
        terminal = request.terminal if hasattr(request, 'terminal') else None
        
        # Fallback: Try to get terminal from session
        if not terminal:
            terminal_id = request.session.get('terminal_id')
            if terminal_id:
                from apps.core.models import POSTerminal
                try:
                    terminal = POSTerminal.objects.get(id=terminal_id, is_active=True)
                    request.terminal = terminal  # Cache for future use
                except POSTerminal.DoesNotExist:
                    pass
        
        logger.info(f"Terminal check - Has attr: {hasattr(request, 'terminal')}, Terminal: {terminal}")
        logger.info(f"Opening cash: {opening_cash}, Notes: {notes}")
        
        if not terminal:
            return JsonResponse({'error': 'Terminal not detected. Please ensure terminal is setup.'}, status=400)
    except Exception as e:
        logger.error(f"Error in shift_open: {str(e)}", exc_info=True)
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=400)
    
    # Create shift
    shift = CashierShift.objects.create(
        store_session=current_session,
        cashier=request.user,
        terminal=terminal,
        opening_cash=opening_cash,
        notes=notes
    )
    
    # Store shift in session
    request.session['active_shift_id'] = str(shift.id)
    
    return JsonResponse({
        'success': True,
        'message': 'Shift opened successfully',
        'shift_id': str(shift.id),
        'opening_cash': float(opening_cash)
    })


@login_required
def shift_close_form(request):
    """Show shift close modal with reconciliation"""
    shift_id = request.session.get('active_shift_id')
    if not shift_id:
        return JsonResponse({'error': 'No active shift'}, status=400)
    
    shift = get_object_or_404(CashierShift, id=shift_id, status='open')
    
    # Calculate expected amounts per payment method
    from django.db.models import Sum, Count
    
    payment_breakdown = Payment.objects.filter(
        bill__created_by=request.user,
        bill__closed_at__gte=shift.shift_start,
        bill__status='paid'
    ).values('method').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('method')
    
    # Get bills stats
    bills_stats = {
        'total': Bill.objects.filter(created_by=request.user, created_at__gte=shift.shift_start).count(),
        'paid': Bill.objects.filter(created_by=request.user, closed_at__gte=shift.shift_start, status='paid').count(),
        'open': Bill.objects.filter(created_by=request.user, created_at__gte=shift.shift_start, status='open').count(),
        'held': Bill.objects.filter(created_by=request.user, created_at__gte=shift.shift_start, status='hold').count(),
    }
    
    total_sales = Bill.objects.filter(
        created_by=request.user,
        closed_at__gte=shift.shift_start,
        status='paid'
    ).aggregate(Sum('total'))['total__sum'] or Decimal('0')
    
    expected_cash = shift.opening_cash
    cash_payment = next((p for p in payment_breakdown if p['method'] == 'cash'), None)
    if cash_payment:
        expected_cash += Decimal(str(cash_payment['total']))
    
    context = {
        'shift': shift,
        'payment_breakdown': list(payment_breakdown),  # Convert to list for template
        'bills_stats': bills_stats,
        'total_sales': float(total_sales) if total_sales else 0,
        'expected_cash': float(expected_cash) if expected_cash else 0,
        'duration_hours': shift.hours_since_open() if hasattr(shift, 'hours_since_open') else 0,
    }
    
    return render(request, 'pos/partials/shift_close_modal.html', context)


@login_required
@require_http_methods(['POST'])
def shift_close(request):
    """Close cashier shift with reconciliation"""
    shift_id = request.session.get('active_shift_id')
    if not shift_id:
        return JsonResponse({'error': 'No active shift'}, status=400)
    
    shift = get_object_or_404(CashierShift, id=shift_id, status='open')
    
    # Get actual amounts per payment method
    actual_cash = Decimal(request.POST.get('actual_cash', '0'))
    notes = request.POST.get('notes', '')
    
    # Delete existing payment summaries to avoid duplicates
    ShiftPaymentSummary.objects.filter(cashier_shift=shift).delete()
    
    # Create payment summaries
    payment_methods = ['cash', 'card', 'qris', 'ewallet', 'transfer', 'voucher']
    for method in payment_methods:
        actual_amount_key = f'actual_{method}'
        actual_amount = Decimal(request.POST.get(actual_amount_key, '0'))
        
        if actual_amount > 0 or method == 'cash':  # Always create cash summary
            summary = ShiftPaymentSummary.objects.create(
                cashier_shift=shift,
                payment_method=method,
                actual_amount=actual_amount
            )
            summary.calculate_expected()
    
    # Close shift
    try:
        difference = shift.close_shift(
            actual_cash=actual_cash,
            closed_by=request.user,
            notes=notes
        )
        
        # Clear session
        if 'active_shift_id' in request.session:
            del request.session['active_shift_id']
        
        return JsonResponse({
            'success': True,
            'message': 'Shift closed successfully',
            'cash_difference': float(difference),
            'shift_id': str(shift.id),
            'print_url': f'/pos/shift/{shift.id}/print-reconciliation/'
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def shift_print_reconciliation(request, shift_id):
    """Print shift reconciliation report"""
    from django.db.models import Sum, Count
    
    shift = get_object_or_404(CashierShift, id=shift_id)
    
    # Get payment summaries
    payment_summaries = ShiftPaymentSummary.objects.filter(
        cashier_shift=shift
    ).order_by('payment_method')
    
    # Calculate cash sales
    cash_summary = payment_summaries.filter(payment_method='cash').first()
    cash_sales = cash_summary.expected_amount if cash_summary else Decimal('0')
    
    # Get bills stats
    bills_stats = {
        'total': Bill.objects.filter(
            created_by=shift.cashier, 
            created_at__gte=shift.shift_start
        ).count(),
        'paid': Bill.objects.filter(
            created_by=shift.cashier, 
            closed_at__gte=shift.shift_start, 
            status='paid'
        ).count(),
        'open': Bill.objects.filter(
            created_by=shift.cashier, 
            created_at__gte=shift.shift_start, 
            status='open'
        ).count(),
        'held': Bill.objects.filter(
            created_by=shift.cashier, 
            created_at__gte=shift.shift_start, 
            status='hold'
        ).count(),
    }
    
    # Calculate total sales
    total_sales = Bill.objects.filter(
        created_by=shift.cashier,
        closed_at__gte=shift.shift_start,
        status='paid'
    ).aggregate(Sum('total'))['total__sum'] or Decimal('0')
    
    # Calculate duration
    if shift.shift_end:
        duration = shift.shift_end - shift.shift_start
        duration_hours = duration.total_seconds() / 3600
    else:
        duration_hours = 0
    
    context = {
        'shift': shift,
        'payment_summaries': payment_summaries,
        'cash_sales': cash_sales,
        'bills_stats': bills_stats,
        'total_sales': total_sales,
        'duration_hours': duration_hours,
    }
    
    return render(request, 'pos/partials/shift_reconciliation_print.html', context)


@login_required
def shift_history(request):
    """Show closed shift history for reprint"""
    # Get last 10 closed shifts for current user or all users (if supervisor)
    if request.user.role in ['owner', 'manager', 'supervisor']:
        # Show all shifts
        shifts = CashierShift.objects.filter(
            status='closed'
        ).select_related('cashier', 'terminal', 'store_session').order_by('-shift_end')[:20]
    else:
        # Show only user's own shifts
        shifts = CashierShift.objects.filter(
            cashier=request.user,
            status='closed'
        ).select_related('terminal', 'store_session').order_by('-shift_end')[:10]
    
    context = {
        'shifts': shifts,
    }
    
    return render(request, 'pos/partials/shift_reprint_modal.html', context)


@login_required
@login_required
def shift_my_dashboard(request):
    """Show real-time shift dashboard"""
    from django.db.models import Sum, Count, Avg, F, DecimalField
    from django.utils import timezone
    from datetime import datetime, timedelta
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        shift_id = request.session.get('active_shift_id')
        if not shift_id:
            # Return HTML error message instead of JSON
            return render(request, 'pos/partials/shift_dashboard_error.html', {
                'error_title': 'No Active Shift',
                'error_message': 'Please open a shift first to view your dashboard.',
                'error_icon': 'clock'
            })
        
        try:
            shift = CashierShift.objects.get(id=shift_id, status='open')
        except CashierShift.DoesNotExist:
            logger.error(f"Shift not found: {shift_id}")
            return render(request, 'pos/partials/shift_dashboard_error.html', {
                'error_title': 'Shift Not Found',
                'error_message': 'The shift session could not be found. Please close this and open a new shift.',
                'error_icon': 'alert'
            })
    except Exception as e:
        logger.error(f"Error in shift_my_dashboard: {str(e)}", exc_info=True)
        return render(request, 'pos/partials/shift_dashboard_error.html', {
            'error_title': 'Error',
            'error_message': f'An error occurred: {str(e)}',
            'error_icon': 'alert'
        })
    
    # Calculate duration
    now = timezone.now()
    duration = now - shift.shift_start
    duration_hours = duration.total_seconds() / 3600
    
    try:
        # Get all bills for this shift
        bills = Bill.objects.filter(
            created_by=shift.cashier,
            created_at__gte=shift.shift_start
        )
        
        # Total sales (paid bills only)
        paid_bills = bills.filter(status='paid')
        total_sales = paid_bills.aggregate(Sum('total'))['total__sum'] or Decimal('0')
        
        # Bills count
        bills_count = bills.count()
        paid_bills_count = paid_bills.count()
        open_bills_count = bills.filter(status='open').count()
        
        # Average bill
        average_bill = paid_bills.aggregate(Avg('total'))['total__avg'] or Decimal('0')
        
        # Payment methods breakdown
        payment_colors = {
            'cash': '#10b981',
            'card': '#3b82f6',
            'qris': '#8b5cf6',
            'ewallet': '#f59e0b',
            'transfer': '#06b6d4',
            'voucher': '#ec4899',
        }
        
        payment_methods = Payment.objects.filter(
            bill__created_by=shift.cashier,
            bill__created_at__gte=shift.shift_start,
            bill__status='paid'
        ).values('method').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')
        
        # Add colors to payment methods
        payment_methods_list = []
        for pm in payment_methods:
            pm['color'] = payment_colors.get(pm['method'], '#6b7280')
            payment_methods_list.append(pm)
        
        # Top 5 selling items
        from apps.pos.models import BillItem
        top_items = BillItem.objects.filter(
            bill__created_by=shift.cashier,
            bill__created_at__gte=shift.shift_start,
            bill__status='paid',
            is_void=False
        ).values('product__name').annotate(
            quantity=Sum('quantity'),
            total_unit_price=Sum('unit_price')
        ).order_by('-quantity')[:5]
        
        # Calculate revenue manually
        top_items_list = []
        for item in top_items:
            # Get total price by multiplying sum of quantities * average unit price
            revenue = Decimal('0')
            items = BillItem.objects.filter(
                bill__created_by=shift.cashier,
                bill__created_at__gte=shift.shift_start,
                bill__status='paid',
                is_void=False,
                product__name=item['product__name']
            )
            for bill_item in items:
                revenue += bill_item.quantity * bill_item.unit_price
            
            top_items_list.append({
                'name': item['product__name'],
                'quantity': item['quantity'],
                'revenue': revenue
            })
        
        # Sales per hour
        shift_start_hour = shift.shift_start.hour
        current_hour = now.hour
        
        # Generate hours range
        hourly_sales = []
        max_amount = 0
        
        if shift.shift_start.date() == now.date():
            # Same day
            hours_range = range(shift_start_hour, current_hour + 1)
        else:
            # Multi-day (just show last 12 hours for simplicity)
            hours_range = range(max(0, current_hour - 11), current_hour + 1)
        
        for hour in hours_range:
            hour_start = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            hour_end = hour_start + timedelta(hours=1)
            
            hour_sales = paid_bills.filter(
                closed_at__gte=hour_start,
                closed_at__lt=hour_end
            ).aggregate(Sum('total'))['total__sum'] or Decimal('0')
            
            hourly_sales.append({
                'hour': hour,
                'amount': float(hour_sales),
                'percentage': 0  # Will calculate after knowing max
            })
            
            if float(hour_sales) > max_amount:
                max_amount = float(hour_sales)
        
        # Calculate percentages for chart
        for hour_data in hourly_sales:
            if max_amount > 0:
                hour_data['percentage'] = (hour_data['amount'] / max_amount) * 100
            else:
                hour_data['percentage'] = 0
        
        context = {
            'shift': shift,
            'duration_hours': duration_hours,
            'total_sales': total_sales,
            'bills_count': bills_count,
            'paid_bills': paid_bills_count,
            'open_bills': open_bills_count,
            'average_bill': average_bill,
            'payment_methods': payment_methods_list,
            'top_items': top_items_list,
            'hourly_sales': hourly_sales,
        }
        
        return render(request, 'pos/partials/shift_dashboard_modal.html', context)
        
    except Exception as e:
        logger.error(f"Error calculating dashboard data: {str(e)}", exc_info=True)
        return render(request, 'pos/partials/shift_dashboard_error.html', {
            'error_title': 'Error Loading Dashboard',
            'error_message': f'Unable to load dashboard data: {str(e)}',
            'error_icon': 'alert'
        })


@login_required
def shift_print_interim(request, shift_id):
    """Print interim shift report (shift still in progress)"""
    from django.db.models import Sum, Count, Avg
    
    shift = get_object_or_404(CashierShift, id=shift_id, status='open')
    
    # Calculate duration
    now = timezone.now()
    duration = now - shift.shift_start
    duration_hours = duration.total_seconds() / 3600
    
    # Get bills
    bills = Bill.objects.filter(
        created_by=shift.cashier,
        created_at__gte=shift.shift_start
    )
    
    paid_bills = bills.filter(status='paid')
    total_sales = paid_bills.aggregate(Sum('total'))['total__sum'] or Decimal('0')
    average_bill = paid_bills.aggregate(Avg('total'))['total__avg'] or Decimal('0')
    
    bills_count = bills.count()
    paid_bills_count = paid_bills.count()
    open_bills_count = bills.filter(status='open').count()
    
    # Payment methods
    payment_methods = Payment.objects.filter(
        bill__created_by=shift.cashier,
        bill__created_at__gte=shift.shift_start,
        bill__status='paid'
    ).values('method').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    # Calculate expected cash
    cash_payment = next((p for p in payment_methods if p['method'] == 'cash'), None)
    expected_cash = shift.opening_cash
    if cash_payment:
        expected_cash += Decimal(str(cash_payment['total']))
    
    # Top items
    from apps.pos.models import BillItem
    top_items = BillItem.objects.filter(
        bill__created_by=shift.cashier,
        bill__created_at__gte=shift.shift_start,
        bill__status='paid',
        is_void=False
    ).values('product__name').annotate(
        quantity=Sum('quantity'),
        total_unit_price=Sum('unit_price')
    ).order_by('-quantity')[:5]
    
    # Calculate revenue manually
    top_items_list = []
    for item in top_items:
        revenue = Decimal('0')
        items = BillItem.objects.filter(
            bill__created_by=shift.cashier,
            bill__created_at__gte=shift.shift_start,
            bill__status='paid',
            is_void=False,
            product__name=item['product__name']
        )
        for bill_item in items:
            revenue += bill_item.quantity * bill_item.unit_price
        
        top_items_list.append({
            'name': item['product__name'],
            'quantity': item['quantity'],
            'revenue': revenue
        })
    
    context = {
        'shift': shift,
        'duration_hours': duration_hours,
        'total_sales': total_sales,
        'average_bill': average_bill,
        'bills_count': bills_count,
        'paid_bills': paid_bills_count,
        'open_bills': open_bills_count,
        'payment_methods': list(payment_methods),
        'expected_cash': expected_cash,
        'top_items': top_items_list,
    }
    
    return render(request, 'pos/partials/shift_interim_print.html', context)


@login_required
def shift_status(request):
    """Get current shift status (for top bar indicator)"""
    shift_id = request.session.get('active_shift_id')
    
    if not shift_id:
        return render(request, 'pos/partials/shift_status.html', {'has_shift': False})
    
    try:
        shift = CashierShift.objects.get(id=shift_id, status='open')
        duration = timezone.now() - shift.shift_start
        hours = int(duration.total_seconds() // 3600)
        minutes = int((duration.total_seconds() % 3600) // 60)
        
        return render(request, 'pos/partials/shift_status.html', {
            'has_shift': True,
            'shift_id': str(shift.id),
            'opening_cash': shift.opening_cash,
            'duration': f"{hours}h {minutes}m",
            'terminal': shift.terminal.terminal_code if shift.terminal else 'Unknown'
        })
    except CashierShift.DoesNotExist:
        # Clear invalid session
        if 'active_shift_id' in request.session:
            del request.session['active_shift_id']
        return render(request, 'pos/partials/shift_status.html', {'has_shift': False})

