from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db import transaction, models
from django.utils import timezone
from decimal import Decimal
import uuid
import json

from .models import Bill, BillItem, Payment, BillLog
from apps.core.models import Product, Category, ModifierOption, Store, Modifier
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
    store_config = Store.get_current()
    
    # Add active items count for conditional logic
    if bill:
        # Force fresh query to avoid cached items
        bill.refresh_from_db()
        active_items_count = bill.items.filter(status='pending', is_void=False).count()
        # Check if ANY item was ever sent to kitchen (including voided ones)
        has_sent_items = bill.items.filter(status='sent').exists()
    else:
        active_items_count = 0
        has_sent_items = False
    
    context = {
        'bill': bill,
        'store_config': store_config,
        'active_items_count': active_items_count,
        'has_sent_items': has_sent_items
    }
    return render(request, 'pos/partials/bill_panel.html', context)


@ensure_csrf_cookie
def pos_main(request):
    """Main POS interface"""
    from apps.core.models import Store, ProductPhoto, POSTerminal
    from django.db.models import Prefetch
    from django.contrib.auth import authenticate, login
    import logging
    logger = logging.getLogger(__name__)
    
    store_config = Store.get_current()
    
    # ========== KIOSK MODE AUTO-LOGIN (DISABLED) ==========
    # Auto-login disabled - require manual login for security & audit trail
    # Terminal will be set in session after successful login
    # Check for token parameter (from POS launcher terminal validation)
    session_token = request.GET.get('token')
    terminal_code_param = request.GET.get('terminal')
    kiosk_mode = request.GET.get('kiosk')
    
    # Store terminal code in session PERSISTENTLY (survive logout)
    # Use different key to distinguish from active terminal
    if terminal_code_param:
        request.session['launcher_terminal_code'] = terminal_code_param
        logger.info(f"Launcher terminal code stored persistently: {terminal_code_param}")
    
    if False and session_token and terminal_code_param and not request.user.is_authenticated:
        # Verify token matches session storage (simple validation)
        # In production, you'd want to store tokens in database with expiry
        try:
            terminal = POSTerminal.objects.get(
                terminal_code=terminal_code_param,
                is_active=True
            )
            
            # Auto-login with a default cashier user for this terminal
            # Try to find a user associated with this terminal's store/brand
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # Try to find cashier for this brand
            cashier_user = User.objects.filter(
                brand=terminal.brand,
                role__in=['cashier', 'admin'],
                is_active=True
            ).first()
            
            if cashier_user:
                # Bypass password authentication for terminal session
                login(request, cashier_user, backend='django.contrib.auth.backends.ModelBackend')
                logger.info(f"Auto-login successful for terminal {terminal_code_param} with user {cashier_user.username}")
                
                # Store terminal info in session
                request.session['terminal_code'] = terminal_code_param
                request.session['terminal_id'] = str(terminal.id)
                request.session['kiosk_mode'] = True
                request.session['session_token'] = session_token
                
                # IMPORTANT: Set request.terminal so it's available immediately
                request.terminal = terminal
                logger.info(f"Terminal attached to request: {terminal_code_param}")
                
                # DON'T redirect - just continue with the request
                # Session cookie will be set in response
                # Fall through to normal POS rendering below
            else:
                logger.warning(f"No cashier user found for terminal {terminal_code_param}")
                return render(request, 'pos/terminal_not_found.html', {
                    'terminal_code': terminal_code_param,
                    'store_config': store_config,
                    'error': 'No cashier user found for this terminal'
                })
        except POSTerminal.DoesNotExist:
            logger.warning(f"Terminal not found during token auth: {terminal_code_param}")
            return render(request, 'pos/terminal_not_found.html', {
                'terminal_code': terminal_code_param,
                'store_config': store_config
            })
    
    # Standard login check (if not in kiosk mode or already authenticated)
    if not request.user.is_authenticated:
        # Debug: Check if launcher terminal is in session before redirect
        launcher_terminal = request.session.get('launcher_terminal_code')
        logger.info(f"[Before Login] launcher_terminal_code in session: {launcher_terminal}")
        
        # Store current URL for redirect after login
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(request.get_full_path())
    
    # ========== TERMINAL DETECTION ==========
    # Priority: 1) Already set by auto-login, 2) URL parameter, 3) Session
    
    # Check if terminal already set by auto-login (kiosk mode)
    if hasattr(request, 'terminal') and request.terminal:
        logger.info(f"Terminal already set from auto-login: {request.terminal.terminal_code}")
    else:
        # Check URL parameter first
        terminal_code = request.GET.get('terminal')
        
        if terminal_code:
            # Validate terminal exists and is active
            try:
                terminal = POSTerminal.objects.get(terminal_code=terminal_code, is_active=True)
                # Store in session for subsequent requests
                request.session['terminal_code'] = terminal_code
                request.session['terminal_id'] = str(terminal.id)
                request.terminal = terminal  # Attach to request
                logger.info(f"Terminal detected from URL: {terminal_code}")
            except POSTerminal.DoesNotExist:
                logger.warning(f"Terminal not found: {terminal_code}")
                return render(request, 'pos/terminal_not_found.html', {
                    'terminal_code': terminal_code,
                    'store_config': store_config
                })
        else:
            # Check session for existing terminal
            terminal_code = request.session.get('terminal_code')
            terminal_id = request.session.get('terminal_id')
            
            # Debug: Check launcher terminal in session
            launcher_terminal_check = request.session.get('launcher_terminal_code')
            logger.info(f"[Terminal Detection] terminal_code={terminal_code}, launcher_terminal_code={launcher_terminal_check}")
            
            # If no terminal in session, check launcher terminal (persistent across logout)
            if not terminal_code:
                launcher_terminal = request.session.get('launcher_terminal_code')
                if launcher_terminal:
                    logger.info(f"Using launcher terminal code (from config.json): {launcher_terminal}")
                    terminal_code = launcher_terminal
                    # Try to lookup terminal
                    try:
                        terminal = POSTerminal.objects.get(terminal_code=terminal_code, is_active=True)
                        request.session['terminal_code'] = terminal_code
                        request.session['terminal_id'] = str(terminal.id)
                        request.terminal = terminal
                        logger.info(f"Terminal set from launcher config: {terminal_code}")
                        # Set variables so the check below passes
                        terminal_id = str(terminal.id)
                    except POSTerminal.DoesNotExist:
                        logger.warning(f"Launcher terminal not found in DB: {launcher_terminal}")
                        # Clear invalid launcher terminal
                        request.session.pop('launcher_terminal_code', None)
            
            if terminal_code and terminal_id:
                try:
                    terminal = POSTerminal.objects.get(id=terminal_id, terminal_code=terminal_code, is_active=True)
                    request.terminal = terminal
                    logger.info(f"Terminal from session: {terminal_code}")
                except POSTerminal.DoesNotExist:
                    # Terminal in session but not in DB or not active
                    logger.warning(f"Terminal in session not found in DB: {terminal_code}")
                    request.session.pop('terminal_code', None)
                    request.session.pop('terminal_id', None)
                    return render(request, 'pos/terminal_required.html', {
                        'store_config': store_config
                    })
            else:
                # No terminal detected at all
                logger.warning("No terminal detected - showing setup prompt")
                return render(request, 'pos/terminal_required.html', {
                    'store_config': store_config
                })
    # ========================================

    brand = request.user.brand
    if not brand and store_config and store_config.brand:
        request.user.brand = store_config.brand
        if not request.user.company and store_config.company:
            request.user.company = store_config.company
        request.user.save(update_fields=['brand', 'company'] if request.user.company else ['brand'])
        brand = request.user.brand

    if not brand:
        return render(request, 'pos/no_brand.html')
    
    categories = Category.objects.filter(brand=brand, is_active=True)
    parent_categories = categories.filter(parent__isnull=True)
    parent_id = request.GET.get('parent')
    selected_parent = None
    if parent_id:
        selected_parent = parent_categories.filter(id=parent_id).first()
    if not selected_parent and parent_categories.exists():
        selected_parent = parent_categories.first()
    subcategories = categories.filter(parent=selected_parent) if selected_parent else Category.objects.none()
    tables = Table.objects.filter(area__brand = brand)
    
    # Order products by category for better display
    products = Product.objects.filter(
        category__brand = brand, 
        is_active=True
    ).select_related('category', 'category__parent').prefetch_related(
        'product_modifiers__modifier',
        Prefetch(
            'photos',
            queryset=ProductPhoto.objects.filter(is_primary=True).order_by('sort_order'),
            to_attr='primary_photos'
        )
    ).order_by(
        'category__sort_order',
        'category__name',
        'name'
    )
    if selected_parent:
        products = products.filter(
            models.Q(category=selected_parent) | models.Q(category__parent=selected_parent)
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
        # Query bill with prefetch_related to load items efficiently
        bill = Bill.objects.filter(
            id=bill_id, 
            status__in=['open', 'hold']
        ).prefetch_related('items').first()
        
        logger.info(f"POS Main - bill found: {bill}")
        if bill:
            # Update session with new active bill
            request.session['active_bill_id'] = bill.id
            request.session.modified = True
            # Calculate active items count (pending items only)
            active_items_count = bill.items.filter(status='pending', is_void=False).count()
            # Check if ANY item was ever sent to kitchen (including voided ones)
            has_sent_items = bill.items.filter(status='sent').exists()
            logger.info(f"POS Main - bill {bill.bill_number} has {bill.items.count()} total items")
        else:
            # Bill not found or not open, clear session
            logger.warning(f"POS Main - bill_id {bill_id} not found or not open, clearing session")
            request.session.pop('active_bill_id', None)
            request.session.modified = True
    
    held_count = Bill.objects.filter(brand=brand, status='hold').count()
    
    # Build a dictionary of product quantities in the current bill
    bill_items_dict = {}
    if bill:
        for item in bill.items.filter(status='pending', is_void=False):
            if item.product_id in bill_items_dict:
                bill_items_dict[item.product_id] += item.quantity
            else:
                bill_items_dict[item.product_id] = item.quantity
    
    # MinIO settings for product images
    minio_endpoint = 'http://localhost:9002'
    minio_bucket = 'product-images'
    
    context = {
        'categories': categories,
        'parent_categories': parent_categories,
        'subcategories': subcategories,
        'selected_parent': selected_parent,
        'tables': tables,
        'products': products,
        'bill': bill,
        'bill_items_dict': bill_items_dict,
        'active_items_count': active_items_count,
        'has_sent_items': has_sent_items,
        'held_count': held_count,
        'store_config': store_config,
        'terminal': terminal,  # Add terminal to context
        'minio_endpoint': minio_endpoint,
        'minio_bucket': minio_bucket,
    }
    return render(request, 'pos/main.html', context)


@login_required
def kitchen_printer_status(request):
    """Kitchen printer status summary for POS widget"""
    from apps.kitchen.models import StationPrinter
    store_config = Store.get_current()

    brand = request.user.brand
    if not brand and store_config and store_config.brand:
        brand = store_config.brand

    printers = StationPrinter.objects.filter(brand=brand, is_active=True).order_by('station_code') if brand else StationPrinter.objects.none()

    online = 0
    offline = 0
    unknown = 0
    last_checked = None

    printer_rows = []
    for printer in printers:
        latest_health = printer.health_checks.order_by('-checked_at').first()
        if latest_health is None:
            status = 'unknown'
            unknown += 1
        elif latest_health.is_online:
            status = 'online'
            online += 1
        else:
            status = 'offline'
            offline += 1

        if latest_health and (last_checked is None or latest_health.checked_at > last_checked):
            last_checked = latest_health.checked_at

        printer_rows.append({
            'id': printer.id,
            'station_code': printer.station_code,
            'printer_name': printer.printer_name,
            'printer_ip': printer.printer_ip,
            'printer_port': printer.printer_port,
            'status': status,
        })

    if offline > 0:
        overall = 'offline'
    elif online > 0 and unknown == 0:
        overall = 'online'
    elif online > 0 and unknown > 0:
        overall = 'degraded'
    else:
        overall = 'unknown'

    return JsonResponse({
        'overall': overall,
        'counts': {
            'total': printers.count(),
            'online': online,
            'offline': offline,
            'unknown': unknown,
        },
        'last_checked': last_checked.isoformat() if last_checked else None,
        'printers': printer_rows,
    })


@login_required
def kitchen_agent_status(request):
    """Kitchen agent service status for POS widget"""
    import subprocess

    status = 'unknown'
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', 'kitchen-agent'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            status = 'running'
        else:
            status = 'stopped'
    except Exception:
        status = 'unknown'

    return JsonResponse({'status': status})


@login_required
@require_http_methods(["POST"])
def kitchen_agent_start(request):
    """Start kitchen-agent systemd service"""
    import subprocess

    try:
        result = subprocess.run(
            ['systemctl', 'start', 'kitchen-agent'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return JsonResponse({'success': True, 'message': 'Kitchen agent started'})
        return JsonResponse({'success': False, 'message': result.stderr or 'Failed to start agent'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def kitchen_agent_stop(request):
    """Stop kitchen-agent systemd service"""
    import subprocess

    try:
        result = subprocess.run(
            ['systemctl', 'stop', 'kitchen-agent'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return JsonResponse({'success': True, 'message': 'Kitchen agent stopped'})
        return JsonResponse({'success': False, 'message': result.stderr or 'Failed to stop agent'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def product_list(request):
    """Product list partial - HTMX"""
    from apps.core.models import ProductPhoto
    from django.db.models import Prefetch
    
    brand = request.user.brand
    category_id = request.GET.get('category')
    parent_id = request.GET.get('parent')
    search_query = request.GET.get('search', '').strip()
    
    # Order products by category sort_order and name for better grouping
    products = Product.objects.filter(
        category__brand = brand, 
        is_active=True
    ).select_related('category', 'category__parent').prefetch_related(
        'product_modifiers__modifier',
        Prefetch(
            'photos',
            queryset=ProductPhoto.objects.filter(is_primary=True).order_by('sort_order'),
            to_attr='primary_photos'
        )
    ).order_by(
        'category__sort_order', 
        'category__name', 
        'name'
    )
    
    if parent_id and parent_id != 'all':
        products = products.filter(
            models.Q(category_id=parent_id) | models.Q(category__parent_id=parent_id)
        )
    elif category_id and category_id != 'all':
        products = products.filter(category_id=category_id)
    
    # Search filter
    if search_query:
        products = products.filter(name__icontains=search_query)
    
    # Get active bill from session
    bill_id = request.session.get('active_bill_id')
    bill = None
    if bill_id:
        bill = Bill.objects.filter(id=bill_id, status='open').first()
    
    # MinIO settings
    minio_endpoint = 'http://localhost:9002'
    minio_bucket = 'product-images'
    
    is_modal = request.GET.get('modal') == '1'
    template = 'pos/partials/product_grid_mini.html' if is_modal else 'pos/partials/product_grid.html'
    
    return render(request, template, {
        'products': products, 
        'bill': bill,
        'minio_endpoint': minio_endpoint,
        'minio_bucket': minio_bucket,
    })


@login_required
@require_http_methods(["POST"])
def open_bill(request):
    """Open new bill - HTMX"""
    table_id = request.POST.get('table_id')
    bill_type = request.POST.get('bill_type', 'dine_in')
    guest_count = int(request.POST.get('guest_count', 1))
    
    with transaction.atomic():
        bill = Bill.objects.create(
            brand = request.user.brand,
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
    modifiers = Modifier.objects.filter(
        product_modifiers__product=product,
        brand=request.user.brand
    ).prefetch_related('options')
    
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
                bill = Bill.objects.select_related('table', 'table__area', 'brand').get(id=active_bill_id, status__in=['open', 'hold'])
                # If bill was on hold, resume it to open
                if bill.status == 'hold':
                    bill.status = 'open'
                    bill.save()
            except Bill.DoesNotExist:
                # Active bill from session no longer exists, clear it
                request.session.pop('active_bill_id', None)
                # Try bill_id from URL as fallback
                try:
                    bill = Bill.objects.select_related('table', 'table__area', 'brand').get(id=bill_id, status__in=['open', 'hold'])
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
                bill = Bill.objects.select_related('table', 'table__area', 'brand').get(id=bill_id, status__in=['open', 'hold'])
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
        
        # Handle product_id conversion (UUID)
        if product_id:
            original_id = product_id
            try:
                product_id = uuid.UUID(str(product_id))
                logger.info(f"Converted '{original_id}' -> {product_id} (uuid)")
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
        for key, value in request.POST.items():
            if key.startswith('modifier_') and value:
                modifiers.append(value)
        if modifiers:
            modifiers = list(dict.fromkeys(modifiers))
        
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
        
        options = ModifierOption.objects.filter(
            modifier__product_modifiers__product=product,
            modifier__brand=request.user.brand
        )
        options_map = {str(opt.id): opt for opt in options}

        modifier_ids = list(modifiers)
        if not modifier_ids:
            for value in request.POST.values():
                try:
                    value_uuid = str(uuid.UUID(str(value)))
                except (ValueError, TypeError):
                    continue
                if value_uuid in options_map:
                    modifier_ids.append(value_uuid)
        if modifier_ids:
            modifier_ids = list(dict.fromkeys(modifier_ids))

        modifier_price = Decimal('0')
        modifier_data = []
        for mod_id in modifier_ids:
            opt = options_map.get(str(mod_id))
            if not opt:
                logger.error(f"ModifierOption with id={mod_id} not found")
                continue
            modifier_price += opt.price_adjustment
            modifier_data.append({
                'id': str(opt.id),
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
                printer_target=product.printer_target,  # Set printer target from product
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
@require_http_methods(["POST"])
def quick_add_product(request, bill_id, product_id):
    """Quick add product from product grid - adds 1 quantity of simple product (no modifiers)"""
    try:
        bill = Bill.objects.select_related('table', 'table__area', 'brand').get(id=bill_id, status__in=['open', 'hold'])
        
        # If bill was on hold, resume it
        if bill.status == 'hold':
            bill.status = 'open'
            bill.save()
        
        product = Product.objects.get(id=product_id)
        
        # Find existing pending item without modifiers and notes
        existing_item = BillItem.objects.filter(
            bill=bill,
            product=product,
            notes='',
            modifiers=[],
            is_void=False,
            status='pending'
        ).first()
        
        if existing_item:
            existing_item.quantity += 1
            existing_item.save()
        else:
            BillItem.objects.create(
                bill=bill,
                product=product,
                quantity=1,
                unit_price=product.price,
                modifier_price=0,
                notes='',
                modifiers=[],
                printer_target=product.printer_target,
                created_by=request.user,
            )
        
        bill.calculate_totals()
        
        # Build updated bill_items_dict
        bill_items_dict = {}
        for item in bill.items.filter(status='pending', is_void=False):
            if item.product_id in bill_items_dict:
                bill_items_dict[item.product_id] += item.quantity
            else:
                bill_items_dict[item.product_id] = item.quantity
        
        # Return updated product card and bill panel
        from django.template.loader import render_to_string
        from apps.core.models import ProductPhoto
        from django.db.models import Prefetch
        
        product = Product.objects.filter(id=product_id).select_related('category', 'category__parent').prefetch_related(
            'product_modifiers__modifier',
            Prefetch(
                'photos',
                queryset=ProductPhoto.objects.filter(is_primary=True).order_by('sort_order'),
                to_attr='primary_photos'
            )
        ).first()
        
        minio_endpoint = 'http://localhost:9002'
        minio_bucket = 'product-images'
        
        product_card_html = render_to_string('pos/partials/product_card.html', {
            'product': product,
            'bill': bill,
            'bill_items_dict': bill_items_dict,
            'minio_endpoint': minio_endpoint,
            'minio_bucket': minio_bucket,
        }, request=request)
        
        bill_panel_html = render_bill_panel(request, bill).content.decode('utf-8')
        
        return JsonResponse({
            'product_card_html': product_card_html,
            'bill_panel_html': bill_panel_html,
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in quick_add_product: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def quick_remove_product(request, bill_id, product_id):
    """Quick remove product from product grid - removes 1 quantity"""
    try:
        bill = Bill.objects.select_related('table', 'table__area', 'brand').get(id=bill_id, status__in=['open', 'hold'])
        product = Product.objects.get(id=product_id)
        
        # Find existing pending item without modifiers and notes
        existing_item = BillItem.objects.filter(
            bill=bill,
            product=product,
            notes='',
            modifiers=[],
            is_void=False,
            status='pending'
        ).first()
        
        if existing_item:
            if existing_item.quantity > 1:
                existing_item.quantity -= 1
                existing_item.save()
            else:
                existing_item.is_void = True
                existing_item.save()
            
            bill.calculate_totals()
        
        # Build updated bill_items_dict
        bill_items_dict = {}
        for item in bill.items.filter(status='pending', is_void=False):
            if item.product_id in bill_items_dict:
                bill_items_dict[item.product_id] += item.quantity
            else:
                bill_items_dict[item.product_id] = item.quantity
        
        # Return updated product card and bill panel
        from django.template.loader import render_to_string
        from apps.core.models import ProductPhoto
        from django.db.models import Prefetch
        
        product = Product.objects.filter(id=product_id).select_related('category', 'category__parent').prefetch_related(
            'product_modifiers__modifier',
            Prefetch(
                'photos',
                queryset=ProductPhoto.objects.filter(is_primary=True).order_by('sort_order'),
                to_attr='primary_photos'
            )
        ).first()
        
        minio_endpoint = 'http://localhost:9002'
        minio_bucket = 'product-images'
        
        product_card_html = render_to_string('pos/partials/product_card.html', {
            'product': product,
            'bill': bill,
            'bill_items_dict': bill_items_dict,
            'minio_endpoint': minio_endpoint,
            'minio_bucket': minio_bucket,
        }, request=request)
        
        bill_panel_html = render_bill_panel(request, bill).content.decode('utf-8')
        
        return JsonResponse({
            'product_card_html': product_card_html,
            'bill_panel_html': bill_panel_html,
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in quick_remove_product: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


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
        modifiers = Modifier.objects.filter(
            product_modifiers__product=item.product,
            brand=request.user.brand
        ).prefetch_related('options')
        
        # Get currently selected modifier option IDs
        selected_modifier_ids = [str(mod.get('id')) for mod in item.modifiers] if item.modifiers else []
        
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
        for key, value in request.POST.items():
            if key.startswith('modifier_') and value:
                modifiers.append(value)
        if modifiers:
            modifiers = list(dict.fromkeys(modifiers))
        
        logger.info(f"Parsed: quantity={quantity}, notes={notes}, modifiers={modifiers}")
        
        # Update quantity and notes
        item.quantity = max(1, quantity)
        item.notes = notes  # Keep as empty string if blank, don't set to None
        
        # Process modifiers
        modifier_data = []
        modifier_total = Decimal('0')
        
        if modifiers:
            from apps.core.models import ModifierOption
            import uuid

            options = ModifierOption.objects.filter(
                modifier__product_modifiers__product=item.product,
                modifier__brand=request.user.brand
            )
            options_map = {str(opt.id): opt for opt in options}

            for mod_id in modifiers:
                opt = options_map.get(str(mod_id))
                if not opt:
                    try:
                        mod_uuid = str(uuid.UUID(str(mod_id)))
                    except (ValueError, TypeError):
                        logger.error(f"Invalid modifier ID: {mod_id}")
                        continue
                    opt = options_map.get(mod_uuid)
                if not opt:
                    logger.warning(f"Modifier option {mod_id} not found")
                    continue
                modifier_total += opt.price_adjustment
                modifier_data.append({
                    'id': str(opt.id),
                    'name': opt.name,
                    'price': float(opt.price_adjustment)
                })
                logger.info(f"Added modifier: {opt.name} (${opt.price_adjustment})")
        
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
            brand = request.user.brand,
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
        brand = request.user.brand,
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
        brand = request.user.brand,
        status='hold'
    ).select_related('table', 'created_by').prefetch_related('items__product').order_by('-created_at')
    
    return render(request, 'pos/partials/held_bills_list.html', {'bills': bills})


@login_required
def member_pin_modal(request, bill_id):
    """Show member PIN input modal"""
    bill = get_object_or_404(Bill, id=bill_id, status__in=['open', 'hold'])
    return render(request, 'pos/partials/member_pin_modal.html', {'bill': bill})


@login_required
@require_http_methods(["POST"])
def verify_member_pin(request, bill_id):
    """Verify member code and attach member to bill - API endpoint returns JSON"""
    from django.http import JsonResponse
    
    bill = get_object_or_404(Bill, id=bill_id, status__in=['open', 'hold'])
    pin = request.POST.get('pin', '').strip()
    
    # Dummy member lookup - always returns same member data
    # TODO: Replace with actual member lookup from database
    if pin and len(pin) > 0:
        # Dummy member data
        member_data = {
            'member_id': '1223343',
            'member_name': 'DADIN JAENUDIN'
        }
        
        # Save member info to bill
        bill.member_code = member_data['member_id']
        bill.member_name = member_data['member_name']
        bill.save()
        
        return JsonResponse({
            'success': True,
            'member_id': member_data['member_id'],
            'member_name': member_data['member_name'],
            'message': 'Member attached successfully'
        })
    else:
        return JsonResponse({
            'success': False,
            'message': 'Please enter valid member code.'
        }, status=400)


@login_required
def refresh_bill_panel(request, bill_id):
    """Refresh bill panel - HTMX"""
    bill = get_object_or_404(Bill, id=bill_id, status__in=['open', 'hold'])
    return render_bill_panel(request, bill)


@login_required
@require_http_methods(["POST"])
def send_to_kitchen(request, bill_id):
    """Send pending items to kitchen - HTMX
    
    Uses new KitchenTicket system - creates tickets for printer polling
    """
    bill = get_object_or_404(Bill, id=bill_id)
    
    # CRITICAL: Only get items that are pending (not yet sent)
    pending_items = bill.items.filter(status='pending', is_void=False)
    
    if not pending_items.exists():
        # Don't remove bill panel, just show alert and return same panel
        response = render_bill_panel(request, bill)
        response['HX-Trigger'] = '{"showNotification": {"message": "Tidak ada item baru untuk dikirim", "type": "warning"}}'
        return response
    
    try:
        from apps.kitchen.services import create_kitchen_tickets
        
        print(f"\n{'='*60}")
        print(f"DEBUG: send_to_kitchen for Bill #{bill.bill_number}")
        print(f"Total bill items: {bill.items.count()}")
        print(f"Pending items to send: {pending_items.count()}")
        
        # Get item IDs before update
        pending_item_ids = list(pending_items.values_list('id', flat=True))
        print(f"Pending item IDs: {pending_item_ids}")
        
        # Print status of all items BEFORE update
        print("\nItem status BEFORE update:")
        for item in bill.items.all():
            print(f"  - Item #{item.id}: {item.product.name} - Status: {item.status}")
        
        # IMPORTANT: Update status BEFORE creating kitchen tickets to prevent race condition
        updated_count = pending_items.update(status='sent')
        print(f"\nUpdated {updated_count} items to 'sent' status")
        
        # Print status of all items AFTER update
        print("\nItem status AFTER update:")
        for item in bill.items.all():
            print(f"  - Item #{item.id}: {item.product.name} - Status: {item.status}")
        
        # Create kitchen tickets ONLY for these specific items
        print(f"\nCalling create_kitchen_tickets with item_ids: {pending_item_ids}")
        tickets = create_kitchen_tickets(bill, item_ids=pending_item_ids)
        print(f"{'='*60}\n")
        
        print(f"DEBUG: Created {len(tickets)} kitchen ticket(s) for bill #{bill.bill_number}")
        for ticket in tickets:
            print(f"  - Ticket #{ticket.id}: {ticket.printer_target.upper()} ({ticket.items.count()} items)")
        
        BillLog.objects.create(
            bill=bill, 
            action='send_kitchen', 
            user=request.user,
            details={
                'items_count': pending_items.count(),
                'tickets_count': len(tickets),
                'tickets': [t.id for t in tickets]
            }
        )
        
        response = render_bill_panel(request, bill)
        
        # Show success notification
        notification = {
            "showNotification": {
                "message": f"✓ Berhasil kirim {pending_items.count()} item ke {len(tickets)} station",
                "type": "success"
            }
        }
        response['HX-Trigger'] = str(notification).replace("'", '"')
        
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


def send_receipt_to_local_printer(bill, terminal_id=None):
    """Send receipt to local printer via POS Launcher API"""
    try:
        import requests
        from datetime import datetime
        
        print(f"\n[Receipt Print] Starting for Bill #{bill.bill_number}")
        
        # Prepare receipt data
        receipt_data = {
            'bill_number': bill.bill_number,
            'receipt_number': bill.bill_number,
            'date': bill.created_at.strftime('%d/%m/%Y'),
            'time': bill.created_at.strftime('%H:%M:%S'),
            'cashier': bill.created_by.get_full_name() if bill.created_by else 'Cashier',
            'customer_name': bill.customer_name or '',
            'table_number': bill.table.number if bill.table else '',
            'items': [],
            'subtotal': float(bill.subtotal),
            'tax': float(bill.tax_amount) if bill.tax_amount else 0,
            'service_charge': float(bill.service_charge) if bill.service_charge else 0,
            'discount': float(bill.discount_amount) if bill.discount_amount else 0,
            'total': float(bill.total),
            'payment_method': '',
            'paid_amount': float(bill.get_paid_amount()),
            'change': float(bill.get_paid_amount() - bill.total) if bill.get_paid_amount() > bill.total else 0
        }
        
        # Get payment method (use first payment or combine multiple)
        payments = bill.payments.all()
        if payments.count() == 1:
            receipt_data['payment_method'] = payments.first().get_method_display()
        elif payments.count() > 1:
            receipt_data['payment_method'] = 'Split Payment'
        
        # Add items
        for item in bill.items.filter(is_void=False):
            item_data = {
                'code': item.product.sku if item.product else '',
                'name': item.product.name if item.product else item.notes,
                'quantity': int(item.quantity),
                'price': float(item.unit_price),
                'modifiers': []
            }
            
            # Add modifiers
            if item.modifiers:
                try:
                    modifiers_list = json.loads(item.modifiers) if isinstance(item.modifiers, str) else item.modifiers
                    for mod in modifiers_list:
                        item_data['modifiers'].append({
                            'name': mod.get('name', '')
                        })
                except:
                    pass
            
            receipt_data['items'].append(item_data)
        
        print(f"[Receipt Print] Data prepared: {len(receipt_data['items'])} items")
        
        # Send to local API (use host.docker.internal for Docker to reach host machine)
        local_api_url = 'http://host.docker.internal:5000/api/print/receipt'
        
        try:
            response = requests.post(
                local_api_url,
                json=receipt_data,
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print_to = result.get('print_to', 'printer')
                    if print_to == 'file':
                        print(f"[Receipt Print] ✅ SUCCESS - Saved to file: {result.get('file_path')}")
                    else:
                        print(f"[Receipt Print] ✅ SUCCESS - Printed to: {result.get('printer')}")
                    return True
                else:
                    print(f"[Receipt Print] ❌ FAILED - {result.get('error')}")
                    return False
            else:
                print(f"[Receipt Print] ❌ HTTP {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            print(f"[Receipt Print] ⚠️ Local API not running (port 5000)")
            return False
        except requests.exceptions.Timeout:
            print(f"[Receipt Print] ⚠️ Request timeout")
            return False
            
    except Exception as e:
        print(f"[Receipt Print] ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


@login_required
@require_http_methods(["POST"])
def process_payment(request, bill_id):
    """Process payment - supports split payment with multiple payment methods"""
    print(f"\n{'='*50}")
    print(f"PROCESS PAYMENT CALLED - Bill ID: {bill_id}")
    print(f"Request method: {request.method}")
    print(f"User: {request.user}")
    print(f"{'='*50}\n")
    
    try:
        # Debug: Log all POST data
        print(f"\n=== PAYMENT DEBUG ===")
        print(f"Bill ID: {bill_id}")
        print(f"POST data: {dict(request.POST)}")
        print(f"====================\n")
        
        # Check if bill exists
        print("Step 1: Checking if bill exists...")
        try:
            bill = Bill.objects.get(id=bill_id)
            print(f"  ? Bill found: {bill.bill_number}")
        except Bill.DoesNotExist:
            print(f"  ? Bill not found")
            return JsonResponse({
                'error': f'Bill #{bill_id} not found'
            }, status=404)
        
        # Check if bill is open
        print(f"Step 2: Checking bill status...")
        print(f"  Bill status: {bill.status}")
        if bill.status not in ['open', 'hold']:
            print(f"  ? Bill is not open or hold")
            return JsonResponse({
                'error': f'Bill #{bill_id} is {bill.status}, cannot process payment'
            }, status=400)
        print(f"  ? Bill is open or hold")
        
        # Helper function to parse amount (handle comma format)
        print("Step 3: Defining parse_amount function...")
        def parse_amount(value):
            if not value:
                return Decimal('0')
            # Remove commas and convert to Decimal
            cleaned = str(value).replace(',', '')
            print(f"  parse_amount: '{value}' -> '{cleaned}'")
            return Decimal(cleaned)
        
        # Check if this is a split payment (multiple payment methods)
        print("Step 4: Checking for split payments...")
        payment_count = 0
        total_paid = Decimal('0')
        
        # Process split payments array
        print("Step 5: Processing split payments array...")
        for key in request.POST.keys():
            if key.startswith('payments[') and key.endswith('][method]'):
                print(f"  Found split payment key: {key}")
                index = key.split('[')[1].split(']')[0]
                method = request.POST.get(f'payments[{index}][method]')
                amount = parse_amount(request.POST.get(f'payments[{index}][amount]', 0))
                reference = request.POST.get(f'payments[{index}][reference]', '')
                
                print(f"  Split payment {index}: method={method}, amount={amount}, ref={reference}")
                
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
        amount_raw = request.POST.get('amount', 0)
        reference = request.POST.get('reference', '')
        
        print(f"Processing current payment...")
        print(f"  method: {method}")
        print(f"  amount_raw: {amount_raw} (type: {type(amount_raw)})")
        print(f"  reference: {reference}")
        
        try:
            amount = parse_amount(amount_raw)
            print(f"  amount parsed: {amount} (type: {type(amount)})")
        except Exception as e:
            print(f"ERROR parsing amount: {e}")
            raise
        
        if amount > 0:
            print(f"Amount > 0, creating payment...")
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
            
            # Queue receipt print via Print Agent
            from apps.pos.print_queue import queue_print_receipt
            print(f"\n[VIEWS] Calling queue_print_receipt for Bill #{bill.bill_number}")
            print(f"[VIEWS] terminal_id from session: {request.session.get('terminal_id')}")
            try:
                queue_print_receipt(bill, terminal_id=request.session.get('terminal_id'))
                print(f"[VIEWS] ✅ queue_print_receipt completed")
            except Exception as e:
                print(f"[VIEWS] ❌ Print queue failed: {e}")
                import traceback
                traceback.print_exc()
                pass  # Don't fail if printing fails
            
            # Send receipt to local printer (POS Launcher)
            print(f"\n[VIEWS] Calling send_receipt_to_local_printer for Bill #{bill.bill_number}")
            try:
                send_receipt_to_local_printer(bill, terminal_id=request.session.get('terminal_id'))
                print(f"[VIEWS] ✅ send_receipt_to_local_printer completed")
            except Exception as e:
                print(f"[VIEWS] ❌ Local printer failed: {e}")
                import traceback
                traceback.print_exc()
                pass  # Don't fail if printing fails
            
            response = render(request, 'pos/partials/payment_success.html', {
                'bill': bill,
                'split_payment': payment_count > 1,
                'payment_count': payment_count
            })
            return trigger_client_event(response, 'paymentComplete')
        
        # Still has remaining balance
        return render(request, 'pos/partials/payment_modal.html', {'bill': bill})
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"ERROR in process_payment: {str(e)}")
        print(error_detail)
        return JsonResponse({
            'error': f'Payment processing failed: {str(e)}'
        }, status=400)


@login_required
def split_bill_modal(request, bill_id):
    """Split bill modal - Enhanced UI"""
    bill = get_object_or_404(Bill, id=bill_id, status__in=['open', 'hold'])
    items = bill.items.filter(is_void=False)
    tables = Table.objects.filter(area__brand=bill.brand, status='available')
    
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
            brand = original_bill.brand,
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
                    printer_target=item.product.printer_target,
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
    current_bill = get_object_or_404(Bill, id=bill_id)
    
    # Get Brand from store config
    store_config = Store.get_current()
    brand = store_config.brand
    
    # Get all open bills except current bill (include hold status too)
    open_bills = Bill.objects.filter(
        brand = brand,
        status__in=['open', 'hold']  # Include both open and hold bills
    ).exclude(id=bill_id).prefetch_related('items', 'table', 'created_by').order_by('-created_at')
    
    context = {
        'current_bill': current_bill,
        'open_bills': open_bills,
        'debug_info': {
            'current_bill_id': current_bill.id,
            'brand_id': brand.id,
            'brand_name': brand.name,
            'open_bills_count': open_bills.count(),
        }
    }
    return render(request, 'pos/partials/merge_bills_modal.html', context)


@login_required
@require_http_methods(["POST"])
def merge_bills(request):
    """Merge multiple bills into one"""
    import logging
    logger = logging.getLogger(__name__)
    
    bill_ids = request.POST.getlist('bill_ids')
    target_bill_id = request.POST.get('target_bill_id')
    
    logger.info(f"=== MERGE BILLS DEBUG ===")
    logger.info(f"Target Bill ID: {target_bill_id}")
    logger.info(f"Source Bill IDs: {bill_ids}")
    
    if len(bill_ids) < 1:
        return JsonResponse({'error': 'Please select at least 1 bill to merge'}, status=400)
    
    if not target_bill_id:
        return JsonResponse({'error': 'Please select target bill'}, status=400)
    
    with transaction.atomic():
        target_bill = get_object_or_404(Bill, id=target_bill_id, status__in=['open', 'hold'])
        source_bills = Bill.objects.filter(id__in=bill_ids, status__in=['open', 'hold']).exclude(id=target_bill_id)
        
        merged_count = 0
        merged_bills = []
        
        for source_bill in source_bills:
            # Move all items to target bill (including sent items, but exclude voided ones)
            items = source_bill.items.filter(is_void=False)
            items_count = items.count()
            
            logger.info(f"Moving {items_count} items from bill {source_bill.bill_number} to {target_bill.bill_number}")
            
            # Use update to move items - this preserves all item properties including status
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
        
        # Recalculate totals for target bill
        target_bill.calculate_totals()
        
        # Verify items were moved
        final_item_count = target_bill.items.filter(is_void=False).count()
        logger.info(f"Target bill {target_bill.bill_number} now has {final_item_count} items (added {merged_count})")
        
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
        
        # Set target bill as active in session
        request.session['active_bill_id'] = target_bill.id
        request.session.modified = True
        
        logger.info(f"Merge completed. Target bill ID {target_bill.id} set as active in session")
    
    return JsonResponse({
        'success': True,
        'message': f'{len(merged_bills)} bills merged into {target_bill.bill_number}',
        'target_bill': target_bill.bill_number,
        'target_bill_id': target_bill.id,
        'merged_bills': merged_bills,
        'total_items': merged_count,
        'final_item_count': final_item_count,  # Total items in target bill after merge
        'redirect': True  # Signal to reload/redirect
    })


@login_required
def move_table_modal(request, bill_id):
    """Move table modal"""
    bill = get_object_or_404(Bill, id=bill_id, status__in=['open', 'hold'])
    tables = Table.objects.filter(
        area__brand=bill.brand,
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
        brand=bill.brand,
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
@require_http_methods(["POST", "GET"])
def reprint_receipt(request, bill_id):
    """Reprint receipt - HTMX"""
    bill = get_object_or_404(Bill, id=bill_id)
    
    if not request.user.has_permission('reprint'):
        return HttpResponse(
            '<div class="p-3 bg-red-100 text-red-700 rounded">Tidak memiliki akses reprint</div>',
            status=403
        )
    
    # Queue reprint via Print Agent
    from apps.pos.print_queue import queue_print_receipt
    print(f"\n[VIEWS] Reprint - Calling queue_print_receipt for Bill #{bill.bill_number}")
    try:
        queue_print_receipt(bill, terminal_id=request.session.get('terminal_id'))
        print(f"[VIEWS] ✅ queue_print_receipt completed")
    except Exception as e:
        print(f"[VIEWS] ❌ Print queue failed: {e}")
        import traceback
        traceback.print_exc()
    
    BillLog.objects.create(bill=bill, action='reprint_receipt', user=request.user)
    
    # Return success or print preview URL
    return JsonResponse({
        'success': True,
        'message': 'Receipt printed',
        'print_url': f'/pos/bill/{bill.id}/print-preview/'
    })


@login_required
def print_preview(request, bill_id):
    """Print preview - Opens in new window for browser print"""
    bill = get_object_or_404(Bill, id=bill_id)
    
    context = {
        'bill': bill,
        'items': bill.items.filter(is_void=False),
        'payments': bill.payments.all()
    }
    
    return render(request, 'pos/print_receipt.html', context)


@login_required
def bill_data_json(request, bill_id):
    """Return bill data as JSON for local printer integration"""
    bill = get_object_or_404(Bill, id=bill_id)
    
    items = bill.items.filter(is_void=False)
    payments = bill.payments.all()
    
    data = {
        'outlet_name': bill.outlet.name if bill.outlet else '',
        'outlet_address': getattr(bill.outlet, 'address', '') if bill.outlet else '',
        'outlet_phone': getattr(bill.outlet, 'phone', '') if bill.outlet else '',
        'bill_number': bill.bill_number,
        'date': bill.created_at.isoformat() if bill.created_at else '',
        'cashier': bill.server.get_full_name() if bill.server else '',
        'customer_name': bill.customer_name or '',
        'table': bill.table.number if bill.table else None,
        'items': [
            {
                'name': item.product.name,
                'qty': item.quantity,
                'price': float(item.unit_price),
                'subtotal': float(item.total)
            }
            for item in items
        ],
        'payments': [
            {
                'method': payment.get_method_display(),
                'amount': float(payment.amount)
            }
            for payment in payments
        ],
        'subtotal': float(bill.subtotal),
        'discount': float(bill.discount_amount) if bill.discount_amount else 0,
        'tax': float(bill.tax_amount) if bill.tax_amount else 0,
        'service': float(bill.service_charge) if bill.service_charge else 0,
        'total': float(bill.total),
        'footer': bill.brand.receipt_footer if bill.brand and bill.brand.receipt_footer else 'Terima Kasih!'
    }
    
    return JsonResponse(data)


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
    modifiers = Modifier.objects.filter(
        product_modifiers__product=product
    ).prefetch_related('options')
    
    return render(request, 'pos/partials/modifier_modal.html', {
        'product': product,
        'modifiers': modifiers,
    })


@login_required
def quick_order_modal(request):
    """Quick order modal - HTMX"""
    categories = Category.objects.filter(brand=request.user.brand, is_active=True)
    products = Product.objects.filter(category__brand=request.user.brand, is_active=True)
    
    return render(request, 'pos/partials/quick_order_modal.html', {
        'categories': categories,
        'products': products,
    })


@login_required
@require_http_methods(["POST"])
def quick_order_create(request):
    """Create quick order with direct payment - HTMX"""
    from apps.pos.utils import generate_queue_number
    
    items_data = request.POST.get('items')
    payment_method = request.POST.get('payment_method', 'cash')
    payment_amount = Decimal(request.POST.get('payment_amount', 0))
    customer_name = request.POST.get('customer_name', '')
    
    items = json.loads(items_data)
    
    with transaction.atomic():
        # Generate queue number using utility function
        queue_number = generate_queue_number(request.user.brand)
        
        bill = Bill.objects.create(
            brand=request.user.brand,
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
                printer_target=product.printer_target,
                created_by=request.user,
                status='pending',
            )
        
        bill.calculate_totals()
        
        # Create payment record
        Payment.objects.create(
            bill=bill,
            method=payment_method,
            amount=bill.total,  # Use actual bill total, not payment_amount
            created_by=request.user,
        )
        
        # Quick orders are always paid immediately
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
        
        # Queue receipt print via Print Agent
        from apps.pos.print_queue import queue_print_receipt
        print(f"\n[VIEWS] Quick order - Calling queue_print_receipt for Bill #{bill.bill_number}")
        try:
            queue_print_receipt(bill, terminal_id=request.session.get('terminal_id'))
            print(f"[VIEWS] ✅ queue_print_receipt completed")
        except Exception as e:
            print(f"[VIEWS] ❌ Print queue failed: {e}")
            import traceback
            traceback.print_exc()
    
    change = payment_amount - bill.total if payment_amount > bill.total else Decimal('0')
    
    return render(request, 'pos/partials/quick_order_success.html', {
        'bill': bill,
        'queue_number': queue_number,
        'change': change,
        'payment_amount': payment_amount,
        'payment_method': payment_method,
    })


@login_required
def queue_display(request):
    """
    Real-time queue display for TV/Monitor
    Auto-refresh via HTMX every 5 seconds
    NOW SERVING: Shows orders completed in last 3 minutes only
    """
    from apps.pos.utils import get_active_queues, get_serving_queues, get_queue_statistics
    
    brand = request.user.brand
    
    # Get current serving (completed in last 3 minutes only)
    serving = get_serving_queues(brand, limit=2, minutes=3)
    
    # Get preparing orders (paid but not completed) - show up to 20
    preparing = get_active_queues(brand, limit=20)
    
    # Get statistics
    stats = get_queue_statistics(brand)
    
    return render(request, 'pos/queue_display.html', {
        'serving': serving,
        'preparing': preparing,
        'stats': stats,
        'avg_wait': stats['avg_wait_minutes'],
    })


@login_required
@require_http_methods(['POST'])
def mark_queue_completed(request, bill_id):
    """
    Mark queue order as completed (ready for pickup)
    Called when kitchen finishes preparing the order
    """
    bill = get_object_or_404(Bill, id=bill_id, brand=request.user.brand)
    
    if bill.status != 'paid':
        return JsonResponse({
            'success': False,
            'message': 'Only paid orders can be marked as completed'
        }, status=400)
    
    # Mark as completed using model method
    bill.mark_completed(request.user)
    
    return JsonResponse({
        'success': True,
        'message': f'Queue #{bill.queue_number} marked as completed',
        'queue_number': bill.queue_number
    })


# ============================================================
# SESSION & SHIFT MANAGEMENT
# ============================================================

@login_required
@require_http_methods(['POST'])
def session_open(request):
    """Open new store session (business date)"""
    store_config = Store.get_current()
    
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
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        store_config = Store.get_current()
        if not store_config:
            logger.error("No store config found")
            return JsonResponse({
                'error': 'Store configuration not found. Please contact administrator.'
            }, status=400)
        
        current_session = StoreSession.get_current(store_config)
        
        if not current_session:
            logger.warning("No active session found")
            return render(request, 'pos/partials/session_required.html')
        
        # Clear stale shift_id from session if it's no longer open
        session_shift_id = request.session.get('active_shift_id')
        logger.info(f"Session shift_id: {session_shift_id}")
        
        if session_shift_id:
            try:
                session_shift = CashierShift.objects.get(id=session_shift_id)
                logger.info(f"Found shift in session: {session_shift.id}, status: {session_shift.status}")
                
                if session_shift.status == 'closed':
                    # Shift already closed, remove from session
                    del request.session['active_shift_id']
                    request.session.modified = True
                    logger.info(f"Cleared closed shift {session_shift_id} from session")
            except CashierShift.DoesNotExist:
                # Shift doesn't exist, remove from session
                del request.session['active_shift_id']
                request.session.modified = True
                logger.info(f"Cleared non-existent shift {session_shift_id} from session")
        
        # Check if user already has open shift
        existing_shift = CashierShift.objects.filter(
            cashier=request.user,
            status='open'
        ).first()
        
        logger.info(f"Existing open shift check: {existing_shift}")
        
        if existing_shift:
            logger.warning(f"User {request.user} already has open shift {existing_shift.id}")
            # Calculate shift duration
            duration = timezone.now() - existing_shift.shift_start
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            
            context = {
                'has_open_shift': True,
                'existing_shift': existing_shift,
                'duration': f"{hours}h {minutes}m"
            }
            return render(request, 'pos/partials/shift_open_modal.html', context)
        
        context = {
            'current_session': current_session,
            'terminal': request.terminal if hasattr(request, 'terminal') else None
        }
        return render(request, 'pos/partials/shift_open_modal.html', context)
    except Exception as e:
        logger.error(f"Error in shift_open_form: {str(e)}", exc_info=True)
        return JsonResponse({
            'error': f'Server error: {str(e)}'
        }, status=400)


@login_required
@require_http_methods(['POST'])
def shift_open(request):
    """Open new cashier shift"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        store_config = Store.get_current()
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
    
    response = JsonResponse({
        'success': True,
        'message': 'Shift opened successfully',
        'shift_id': str(shift.id),
        'opening_cash': float(opening_cash)
    })
    
    # Trigger client event to update UI
    response['HX-Trigger'] = json.dumps({'shiftStatusChanged': {'hasActiveShift': True}})
    
    return response


@login_required
def shift_close_form(request):
    """Show shift close modal with reconciliation"""
    shift_id = request.session.get('active_shift_id')
    if not shift_id:
        # Return empty div instead of error to prevent HTMX error popup
        return HttpResponse('<div></div>', content_type='text/html')
    
    try:
        shift = CashierShift.objects.get(id=shift_id, status='open')
    except CashierShift.DoesNotExist:
        # Shift not found or already closed, clear session and return empty
        request.session.pop('active_shift_id', None)
        return HttpResponse('<div></div>', content_type='text/html')
    
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
    
    # Helper function to clean currency input
    def clean_currency(value):
        """Remove commas and non-digit chars, convert to Decimal"""
        if not value:
            return Decimal('0')
        # Remove everything except digits
        cleaned = ''.join(filter(str.isdigit, str(value)))
        return Decimal(cleaned) if cleaned else Decimal('0')
    
    # Get actual amounts per payment method
    actual_cash = clean_currency(request.POST.get('actual_cash', '0'))
    notes = request.POST.get('notes', '')
    
    # Delete existing payment summaries to avoid duplicates
    ShiftPaymentSummary.objects.filter(cashier_shift=shift).delete()
    
    # Create payment summaries
    payment_methods = ['cash', 'card', 'qris', 'ewallet', 'transfer', 'voucher']
    for method in payment_methods:
        actual_amount_key = f'actual_{method}'
        actual_amount = clean_currency(request.POST.get(actual_amount_key, '0'))
        
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
        
        # Clear session explicitly
        if 'active_shift_id' in request.session:
            del request.session['active_shift_id']
            request.session.modified = True
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Shift {shift.id} closed. Session cleared. Shift status: {shift.status}")
        
        response = JsonResponse({
            'success': True,
            'message': 'Shift closed successfully',
            'cash_difference': float(difference),
            'shift_id': str(shift.id),
            'print_url': f'/pos/shift/{shift.id}/print-reconciliation/'
        })
        
        # Trigger client event to update UI
        response['HX-Trigger'] = json.dumps({'shiftStatusChanged': {'hasActiveShift': False}})
        
        return response
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error closing shift: {str(e)}", exc_info=True)
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
    """Get current shift status (for sidebar indicator)"""
    shift_id = request.session.get('active_shift_id')
    shift = None
    
    # Try to get shift from session first
    if shift_id:
        try:
            shift = CashierShift.objects.get(id=shift_id, status='open')
        except CashierShift.DoesNotExist:
            # Clear invalid session
            if 'active_shift_id' in request.session:
                del request.session['active_shift_id']
                request.session.modified = True
    
    # If no shift in session, check if user has any open shift
    if not shift:
        shift = CashierShift.objects.filter(
            cashier=request.user,
            status='open'
        ).first()
        
        # If found, update session
        if shift:
            request.session['active_shift_id'] = str(shift.id)
            request.session.modified = True
    
    if not shift:
        return render(request, 'pos/partials/shift_status.html', {'has_shift': False})
    
    # Calculate duration
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


# ==================== CASH DROP VIEWS ====================

@login_required
def cash_drop_form(request):
    """Show cash drop modal"""
    shift_id = request.session.get('active_shift_id')
    if not shift_id:
        return JsonResponse({'error': 'No active shift'}, status=400)
    
    shift = get_object_or_404(CashierShift, id=shift_id, status='open')
    
    context = {
        'shift': shift,
    }
    
    return render(request, 'pos/partials/cash_drop_modal.html', context)


@login_required
@require_http_methods(['POST'])
def cash_drop_create(request):
    """Create cash drop transaction"""
    from apps.core.models_session import CashDrop
    from apps.core.models import Company, Brand, Store
    
    shift_id = request.session.get('active_shift_id')
    if not shift_id:
        return JsonResponse({'error': 'No active shift'}, status=400)
    
    shift = get_object_or_404(CashierShift, id=shift_id, status='open')
    
    # Helper function to clean currency input
    def clean_currency(value):
        """Remove commas and non-digit chars, convert to Decimal"""
        if not value:
            return Decimal('0')
        # Remove everything except digits
        cleaned = ''.join(filter(str.isdigit, str(value)))
        return Decimal(cleaned) if cleaned else Decimal('0')
    
    # Get form data
    amount = clean_currency(request.POST.get('amount', '0'))
    reason = request.POST.get('reason', 'regular')
    notes = request.POST.get('notes', '')
    
    # Validate amount
    if amount <= 0:
        return JsonResponse({'error': 'Amount must be greater than zero'}, status=400)
    
    # Get multi-tenant context
    store_config = Store.get_current()
    brand = request.user.brand
    company = brand.company if brand else None
    
    if not all([company, brand, store_config]):
        return JsonResponse({'error': 'Store configuration incomplete'}, status=400)
    
    try:
        # Create cash drop
        cash_drop = CashDrop.objects.create(
            company=company,
            brand = brand,
            store=store_config,
            cashier_shift=shift,
            amount=amount,
            reason=reason,
            notes=notes,
            created_by=request.user
        )
        
        # Return success response with receipt
        response_html = f"""
        <div class="fixed inset-0 z-50 overflow-y-auto" x-data="{{ isOpen: true }}" x-show="isOpen" x-cloak>
            <div class="fixed inset-0 bg-black bg-opacity-50 transition-opacity" @click="isOpen = false"></div>
            
            <div class="flex items-center justify-center min-h-screen p-4">
                <div class="relative bg-white rounded-2xl shadow-2xl max-w-md w-full transform transition-all">
                    <!-- Success Header -->
                    <div class="bg-gradient-to-r from-green-600 to-emerald-600 text-white p-6 rounded-t-2xl">
                        <div class="flex items-center gap-3">
                            <div class="w-12 h-12 bg-white/20 rounded-full flex items-center justify-center">
                                <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                                </svg>
                            </div>
                            <div>
                                <h3 class="text-2xl font-bold">Cash Drop Recorded</h3>
                                <p class="text-green-100 text-sm">Successfully saved</p>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Receipt Details -->
                    <div class="p-6 space-y-4">
                        <div class="bg-gray-50 rounded-lg p-4 space-y-3">
                            <div class="flex justify-between items-center pb-2 border-b border-gray-200">
                                <span class="text-sm text-gray-600">Receipt Number</span>
                                <span class="font-mono font-bold text-blue-600">{cash_drop.receipt_number}</span>
                            </div>
                            <div class="flex justify-between items-center">
                                <span class="text-sm text-gray-600">Amount</span>
                                <span class="text-2xl font-bold text-green-600">Rp {amount:,.0f}</span>
                            </div>
                            <div class="flex justify-between items-center">
                                <span class="text-sm text-gray-600">Reason</span>
                                <span class="font-medium">{dict(CashDrop.REASON_CHOICES).get(reason, reason)}</span>
                            </div>
                            <div class="flex justify-between items-center">
                                <span class="text-sm text-gray-600">Time</span>
                                <span class="font-medium">{cash_drop.created_at.strftime('%H:%M:%S')}</span>
                            </div>
                        </div>
                        
                        <!-- Info -->
                        <div class="bg-blue-50 border-l-4 border-blue-500 p-3 rounded">
                            <p class="text-sm text-blue-800">
                                <strong>Important:</strong> This amount has been recorded and will be reflected in your shift reconciliation.
                            </p>
                        </div>
                    </div>
                    
                    <!-- Actions -->
                    <div class="p-6 border-t flex gap-3">
                        <button 
                            onclick="window.open('/pos/cash-drop/{cash_drop.id}/print/', '_blank')"
                            class="flex-1 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition flex items-center justify-center gap-2">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                            </svg>
                            Print Receipt
                        </button>
                        <button 
                            @click="isOpen = false; document.getElementById('modal-container').innerHTML = '';"
                            class="flex-1 px-4 py-2.5 bg-gray-600 hover:bg-gray-700 text-white font-semibold rounded-lg transition">
                            Close
                        </button>
                    </div>
                </div>
            </div>
        </div>
        """
        
        return HttpResponse(response_html)
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error creating cash drop: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def cash_drop_print(request, drop_id):
    """Print cash drop receipt"""
    from apps.core.models_session import CashDrop
    
    cash_drop = get_object_or_404(CashDrop, id=drop_id)
    
    # Mark as printed
    cash_drop.mark_printed()
    
    context = {
        'cash_drop': cash_drop,
    }
    
    return render(request, 'pos/partials/cash_drop_receipt.html', context)


@login_required
def shift_status_header(request):
    """Return shift status header partial for HTMX polling"""
    active_shift_id = request.session.get('active_shift_id')
    active_shift = None
    duration_str = ""
    
    if active_shift_id:
        try:
            active_shift = CashierShift.objects.get(id=active_shift_id, status='open')
        except CashierShift.DoesNotExist:
            active_shift = None
            request.session.pop('active_shift_id', None)

    if not active_shift:
        active_shift = CashierShift.objects.filter(
            cashier=request.user,
            status='open'
        ).first()
        if active_shift:
            request.session['active_shift_id'] = str(active_shift.id)
            request.session.modified = True

    if active_shift:
        duration = timezone.now() - active_shift.shift_start
        hours = int(duration.total_seconds() // 3600)
        minutes = int((duration.total_seconds() % 3600) // 60)
        duration_str = f"{hours}h {minutes}m"
    
    context = {
        'active_shift': active_shift,
        'duration_str': duration_str if active_shift else None,
    }
    
    return render(request, 'pos/partials/shift_status_header.html', context)


@login_required
def shift_status_check(request):
    """API endpoint to check if cashier has active shift"""
    active_shift_id = request.session.get('active_shift_id')
    has_active_shift = False
    active_shift = None
    
    if active_shift_id:
        try:
            active_shift = CashierShift.objects.get(id=active_shift_id, status='open')
        except CashierShift.DoesNotExist:
            request.session.pop('active_shift_id', None)

    if not active_shift:
        active_shift = CashierShift.objects.filter(
            cashier=request.user,
            status='open'
        ).first()
        if active_shift:
            request.session['active_shift_id'] = str(active_shift.id)
            request.session.modified = True

    has_active_shift = active_shift is not None
    
    return JsonResponse({
        'has_active_shift': has_active_shift,
    })
