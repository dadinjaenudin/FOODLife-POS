"""
Management Interface Views
Dashboard, Terminal Management, Reports Overview
"""
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
from decimal import Decimal

from apps.core.models import POSTerminal, StoreConfig, Category, Product, User, ProductPhoto
from apps.core.models_session import StoreSession
from apps.pos.models import Bill, Payment
from apps.tables.models import Table, TableArea
from apps.promotions.models import Promotion, Voucher
from apps.promotions.models import Promotion, Voucher
from .decorators import manager_required, supervisor_required


@manager_required
def dashboard(request):
    """
    Management Dashboard - Real-time metrics & overview
    """
    store_config = StoreConfig.get_current()
    
    # Handle case where store not configured yet
    if not store_config:
        return render(request, 'management/dashboard.html', {
            'error': 'Store configuration not found. Please run setup wizard first.',
            'store_config': None,
        })
    
    # Today's date
    today = timezone.now().date()
    
    # Get today's stats
    today_bills = Bill.objects.filter(
        created_at__date=today,
        outlet=store_config.outlet
    )
    
    closed_bills = today_bills.filter(status='paid')
    
    today_revenue = closed_bills.aggregate(
        total=Sum('total')
    )['total'] or Decimal('0')
    
    bills_count = {
        'open': today_bills.filter(status='open').count(),
        'closed': closed_bills.count(),
        'held': today_bills.filter(status='hold').count(),
    }
    
    avg_bill_value = closed_bills.aggregate(
        avg=Avg('total')
    )['avg'] or Decimal('0')
    
    # Payment methods breakdown
    payments = Payment.objects.filter(
        bill__created_at__date=today,
        bill__outlet=store_config.outlet
    ).values('method').annotate(
        total=Sum('amount')
    )
    
    payment_breakdown = {p['method']: p['total'] for p in payments}
    
    # Terminal stats
    terminals = POSTerminal.objects.filter(store=store_config, is_active=True)
    
    # Online if heartbeat within last 5 minutes
    five_min_ago = timezone.now() - timedelta(minutes=5)
    online_terminals = terminals.filter(last_heartbeat__gte=five_min_ago).count()
    offline_terminals = terminals.filter(
        Q(last_heartbeat__lt=five_min_ago) | Q(last_heartbeat__isnull=True)
    ).count()
    
    # Active cashiers (with open bills)
    active_cashiers = today_bills.filter(status='open').values('created_by__first_name', 'created_by__last_name', 'terminal__terminal_code').distinct()
    
    context = {
        'store_config': store_config,
        'current_session': None,  # Will be implemented later
        'business_date': today,
        'hours_open': 0,  # Will be implemented with session
        
        # Revenue card
        'today_revenue': today_revenue,
        'bills_count': bills_count,
        'avg_bill_value': avg_bill_value,
        
        # Terminals card
        'online_terminals': online_terminals,
        'offline_terminals': offline_terminals,
        'total_terminals': terminals.count(),
        
        # Cashiers card
        'active_shifts': [],  # Will be implemented with shift model
        'active_cashiers_count': active_cashiers.count(),
        
        # Payment breakdown
        'payment_breakdown': payment_breakdown,
        
        # Quick stats
        'last_updated': timezone.now(),
    }
    
    return render(request, 'management/dashboard.html', context)


@manager_required
def terminals_list(request):
    """
    Terminal Management Page - List all terminals with status
    """
    store_config = StoreConfig.get_current()
    
    # Get all terminals
    terminals = POSTerminal.objects.filter(
        store=store_config
    ).order_by('-is_active', '-last_heartbeat')
    
    # Filter by status
    status_filter = request.GET.get('status', 'all')
    five_min_ago = timezone.now() - timedelta(minutes=5)
    
    if status_filter == 'online':
        terminals = terminals.filter(last_heartbeat__gte=five_min_ago, is_active=True)
    elif status_filter == 'offline':
        terminals = terminals.filter(
            Q(last_heartbeat__lt=five_min_ago) | Q(last_heartbeat__isnull=True),
            is_active=True
        )
    elif status_filter == 'inactive':
        terminals = terminals.filter(is_active=False)
    
    # Filter by device type
    device_filter = request.GET.get('device_type', '')
    if device_filter:
        terminals = terminals.filter(device_type=device_filter)
    
    # Search by terminal code
    search = request.GET.get('search', '')
    if search:
        terminals = terminals.filter(terminal_code__icontains=search)
    
    # Get current shifts per terminal (simplified for now)
    terminal_ids = [t.id for t in terminals]
    
    # Add shift info to terminals
    for terminal in terminals:
        terminal.current_shift = None  # Will implement with CashierShift model
        
        # Calculate online status
        if terminal.is_active and terminal.last_heartbeat:
            time_diff = timezone.now() - terminal.last_heartbeat
            if time_diff < timedelta(minutes=5):
                terminal.status = 'online'
            elif time_diff < timedelta(minutes=10):
                terminal.status = 'warning'
            else:
                terminal.status = 'offline'
        else:
            terminal.status = 'inactive' if not terminal.is_active else 'offline'
    
    context = {
        'store_config': store_config,
        'terminals': terminals,
        'status_filter': status_filter,
        'device_filter': device_filter,
        'search': search,
        'device_types': POSTerminal.DEVICE_TYPE_CHOICES,
    }
    
    return render(request, 'management/terminals.html', context)


@manager_required
def terminal_detail(request, terminal_id):
    """
    Terminal Details Modal (HTMX partial)
    """
    terminal = get_object_or_404(POSTerminal, id=terminal_id)
    
    # Get recent activity (simplified for now)
    recent_shifts = []  # Will implement with CashierShift model
    
    recent_bills = Bill.objects.filter(
        terminal=terminal
    ).order_by('-created_at')[:10]
    
    # Total stats
    total_bills = Bill.objects.filter(terminal=terminal).count()
    total_sales = Bill.objects.filter(
        terminal=terminal,
        status='paid'
    ).aggregate(total=Sum('total'))['total'] or Decimal('0')
    
    context = {
        'terminal': terminal,
        'recent_shifts': recent_shifts,
        'recent_bills': recent_bills,
        'total_bills': total_bills,
        'total_sales': total_sales,
    }
    
    return render(request, 'management/partials/terminal_detail.html', context)


@supervisor_required
def terminal_deactivate(request, terminal_id):
    """
    Deactivate Terminal (HTMX endpoint)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    terminal = get_object_or_404(POSTerminal, id=terminal_id)
    reason = request.POST.get('reason', 'No reason provided')
    
    # Deactivate terminal
    terminal.is_active = False
    terminal.save()
    
    # Set status for display
    terminal.status = 'inactive'
    terminal.current_shift = None
    
    # TODO: Create audit log
    # TODO: Force close active shift if exists
    
    # Return updated table row HTML
    from django.template.loader import render_to_string
    html = render_to_string('management/partials/terminal_row.html', {
        'terminal': terminal,
    })
    return render(request, 'management/partials/terminal_row.html', {'terminal': terminal})


@supervisor_required
def terminal_reactivate(request, terminal_id):
    """
    Reactivate Terminal (HTMX endpoint)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    terminal = get_object_or_404(POSTerminal, id=terminal_id)
    
    terminal.is_active = True
    terminal.save()
    
    # Recalculate status
    if terminal.last_heartbeat:
        time_diff = timezone.now() - terminal.last_heartbeat
        from datetime import timedelta
        if time_diff < timedelta(minutes=5):
            terminal.status = 'online'
        elif time_diff < timedelta(minutes=10):
            terminal.status = 'warning'
        else:
            terminal.status = 'offline'
    else:
        terminal.status = 'offline'
    
    terminal.current_shift = None
    
    # Return updated table row HTML
    return render(request, 'management/partials/terminal_row.html', {'terminal': terminal})


@manager_required
def dashboard_refresh(request):
    """
    Dashboard Metrics Refresh (HTMX partial for auto-update)
    """
    # Reuse dashboard logic but return only the metrics partial
    # This will be called every 30 seconds via HTMX polling
    
    store_config = StoreConfig.get_current()
    current_session = StoreSession.objects.filter(is_closed=False).first()
    
    # Similar logic as dashboard view...
    # (abbreviated for now, will extract to service function)
    
    context = {
        'last_updated': timezone.now(),
        # ... other metrics
    }
    
    return render(request, 'management/partials/dashboard_metrics.html', context)


@manager_required
def settings(request):
    """
    Settings Page - Store Configuration
    """
    print(f"[DEBUG] settings() called - Method: {request.method}, Path: {request.path}")
    print(f"[DEBUG] Headers: {dict(request.headers)}")
    
    store_config = StoreConfig.get_current()
    
    if not store_config:
        return render(request, 'management/settings.html', {
            'error': 'Store configuration not found. Please run setup wizard first.',
        })
    
    outlet = store_config.outlet
    company = outlet.company
    
    # Get terminal count
    terminal_count = POSTerminal.objects.filter(store=store_config).count()
    
    # Get database size (SQLite)
    import os
    from django.conf import settings
    db_size = 0
    if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
        db_path = settings.DATABASES['default']['NAME']
        if os.path.exists(db_path):
            db_size = os.path.getsize(db_path) / (1024 * 1024)  # MB
    
    context = {
        'store_config': store_config,
        'outlet': outlet,
        'company': company,
        'terminal_count': terminal_count,
        'db_size': db_size,
    }
    
    return render(request, 'management/settings.html', context)


@manager_required
def settings_update(request):
    """
    Update Settings - HTMX form handler with file upload
    """
    print(f"[DEBUG] settings_update() called - Method: {request.method}")
    print(f"[DEBUG] Headers: {dict(request.headers)}")
    print(f"[DEBUG] POST data: {dict(request.POST)}")
    print(f"[DEBUG] FILES: {dict(request.FILES)}")
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    store_config = StoreConfig.get_current()
    if not store_config:
        return JsonResponse({'error': 'Store configuration not found'}, status=404)
    
    try:
        # Update StoreConfig
        store_config.store_code = request.POST.get('store_code', store_config.store_code)
        store_config.store_name = request.POST.get('store_name', store_config.store_name)
        store_config.address = request.POST.get('address', store_config.address)
        store_config.phone = request.POST.get('phone', store_config.phone)
        
        # Handle login image upload
        if 'login_image' in request.FILES:
            login_image = request.FILES['login_image']
            # Validate file size (5MB)
            if login_image.size > 5 * 1024 * 1024:
                return JsonResponse({'error': 'File size must be less than 5MB'}, status=400)
            
            # Delete old image if exists
            if store_config.login_image:
                store_config.login_image.delete(save=False)
            
            store_config.login_image = login_image
        
        # Handle remove image
        if request.POST.get('remove_login_image') == 'true':
            if store_config.login_image:
                store_config.login_image.delete(save=False)
                store_config.login_image = None
        
        store_config.save()
        
        # Update Outlet (tax & service charge)
        outlet = store_config.outlet
        outlet.tax_rate = Decimal(request.POST.get('tax_rate', outlet.tax_rate))
        outlet.service_charge = Decimal(request.POST.get('service_charge', outlet.service_charge))
        outlet.receipt_footer = request.POST.get('receipt_footer', outlet.receipt_footer)
        outlet.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Settings updated successfully'
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'error': str(e)
        }, status=400)


@manager_required
def master_data(request):
    """
    Master Data Overview - Show all master data counts
    Identifies what data needs to sync with HO/Cloud
    """
    print(f"[DEBUG] master_data() called - Method: {request.method}")
    
    store_config = StoreConfig.get_current()
    if not store_config:
        return render(request, 'management/master_data.html', {
            'error': 'Store configuration not found. Please run setup wizard first.',
        })
    
    outlet = store_config.outlet
    company = outlet.company
    
    # Count all master data
    master_data_summary = [
        {
            'name': 'Company (Tenant)',
            'table': 'core_company',
            'count': 1,  # Always 1 per Edge Server
            'sync': 'pull',  # Download from HO
            'description': 'Company/Tenant configuration',
            'icon': '🏢',
            'url': None,  # Read-only
        },
        {
            'name': 'Outlet (Brand)',
            'table': 'core_outlet',
            'count': 1,  # Always 1 per Edge Server
            'sync': 'pull',
            'description': 'Brand/Outlet configuration',
            'icon': '🏪',
            'url': None,  # Read-only
        },
        {
            'name': 'Store Configuration',
            'table': 'core_storeconfig',
            'count': 1,  # Singleton
            'sync': 'pull',
            'description': 'This Edge Server configuration',
            'icon': '⚙️',
            'url': 'management:settings',
        },
        {
            'name': 'Categories',
            'table': 'core_category',
            'count': Category.objects.filter(outlet=outlet).count(),
            'sync': 'pull',
            'description': 'Product categories (Food, Drinks, etc)',
            'icon': '📁',
            'url': 'management:categories',
        },
        {
            'name': 'Products',
            'table': 'core_product',
            'count': Product.objects.filter(category__outlet=outlet).count(),
            'sync': 'pull',
            'description': 'Menu items with prices',
            'icon': '🍔',
            'url': 'management:products',
        },
        {
            'name': 'Tables',
            'table': 'tables_table',
            'count': Table.objects.filter(area__outlet=outlet).count(),
            'sync': 'pull',
            'description': 'Restaurant tables & seating',
            'icon': '🪑',
            'url': 'management:tables',
        },
        {
            'name': 'Table Areas',
            'table': 'tables_tablearea',
            'count': TableArea.objects.filter(outlet=outlet).count(),
            'sync': 'pull',
            'description': 'Table zones/sections',
            'icon': '🗺️',
            'url': 'management:table_areas',
        },
        {
            'name': 'Users (Staff)',
            'table': 'core_user',
            'count': User.objects.filter(outlet=outlet).count(),
            'sync': 'pull',
            'description': 'Cashiers, waiters, kitchen staff',
            'icon': '👤',
            'url': 'management:users',
        },
        {
            'name': 'Promotions',
            'table': 'promotions_promotion',
            'count': Promotion.objects.filter(outlet=outlet).count(),
            'sync': 'pull',
            'description': 'Active promotions & discounts',
            'icon': '🎁',
            'url': 'management:promotions',
        },
        {
            'name': 'Vouchers',
            'table': 'promotions_voucher',
            'count': Voucher.objects.filter(promotion__outlet=outlet).count(),
            'sync': 'pull',
            'description': 'Discount vouchers',
            'icon': '🎟️',
            'url': 'management:vouchers',
        },
        {
            'name': 'Terminals',
            'table': 'core_posterminal',
            'count': POSTerminal.objects.filter(store=store_config).count(),
            'sync': 'none',  # Local only (no sync)
            'description': 'Registered POS terminals',
            'icon': '🖥️',
            'url': 'management:terminals',
        },
    ]
    
    # Transaction data (push to HO)
    transaction_data = [
        {
            'name': 'Bills (Transactions)',
            'table': 'pos_bill',
            'count': Bill.objects.filter(outlet=outlet).count(),
            'sync': 'push',
            'description': 'All sales transactions',
            'icon': '🧾',
            'url': 'management:bills',
        },
        {
            'name': 'Payments',
            'table': 'pos_payment',
            'count': Payment.objects.filter(bill__outlet=outlet).count(),
            'sync': 'push',
            'description': 'Payment records',
            'icon': '💳',
            'url': 'management:payments',
        },
        {
            'name': 'Store Sessions',
            'table': 'core_storesession',
            'count': StoreSession.objects.filter(store=store_config).count(),
            'sync': 'push',
            'description': 'Daily business sessions & EOD',
            'icon': '📅',
            'url': 'management:store_sessions',
        },
    ]
    
    context = {
        'store_config': store_config,
        'outlet': outlet,
        'company': company,
        'master_data_summary': master_data_summary,
        'transaction_data': transaction_data,
        'total_master_tables': len(master_data_summary),
        'total_transaction_tables': len(transaction_data),
    }
    
    return render(request, 'management/master_data.html', context)


@manager_required
def categories(request):
    """Categories Management"""
    store_config = StoreConfig.get_current()
    outlet = store_config.outlet
    
    categories_list = Category.objects.filter(
        outlet=outlet
    ).select_related('parent').order_by('sort_order', 'name')
    
    # Calculate counts for template
    active_count = categories_list.filter(is_active=True).count()
    parent_count = categories_list.filter(parent__isnull=True).count()
    
    context = {
        'categories': categories_list,
        'total_count': categories_list.count(),
        'active_count': active_count,
        'parent_count': parent_count,
    }
    
    return render(request, 'management/categories.html', context)


@manager_required
def products(request):
    """Products Management"""
    store_config = StoreConfig.get_current()
    outlet = store_config.outlet
    
    # Get all products
    products_list = Product.objects.filter(
        category__outlet=outlet
    ).select_related('category').prefetch_related('modifiers', 'photos').order_by('category__name', 'name')
    
    # Filter by category
    category_filter = request.GET.get('category', '')
    if category_filter:
        products_list = products_list.filter(category_id=category_filter)
    
    # Search
    search = request.GET.get('search', '')
    if search:
        products_list = products_list.filter(
            Q(name__icontains=search) | Q(sku__icontains=search)
        )
    
    # Filter by active status
    status_filter = request.GET.get('status', 'active')
    if status_filter == 'active':
        products_list = products_list.filter(is_active=True)
    elif status_filter == 'inactive':
        products_list = products_list.filter(is_active=False)
    
    # Get categories for filter dropdown
    categories_list = Category.objects.filter(outlet=outlet).order_by('name')
    
    # Calculate counts
    total_count = products_list.count()
    active_count = Product.objects.filter(category__outlet=outlet, is_active=True).count()
    inactive_count = Product.objects.filter(category__outlet=outlet, is_active=False).count()
    
    # Pagination
    paginator = Paginator(products_list, 20)  # 20 products per page
    page = request.GET.get('page', 1)
    
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)
    
    context = {
        'products': products_page,
        'categories': categories_list,
        'total_count': total_count,
        'active_count': active_count,
        'inactive_count': inactive_count,
        'category_filter': category_filter,
        'search': search,
        'status_filter': status_filter,
        'paginator': paginator,
    }
    
    return render(request, 'management/products.html', context)


@manager_required
def tables_list(request):
    """Tables Management"""
    store_config = StoreConfig.get_current()
    outlet = store_config.outlet
    
    tables = Table.objects.filter(
        area__outlet=outlet
    ).select_related('area').order_by('area__name', 'number')
    
    # Filter by area
    area_filter = request.GET.get('area', '')
    if area_filter:
        tables = tables.filter(area_id=area_filter)
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        tables = tables.filter(status=status_filter)
    
    # Get areas for filter
    areas = TableArea.objects.filter(outlet=outlet).order_by('name')
    
    # Calculate status counts
    available_count = tables.filter(status='available').count()
    occupied_count = tables.filter(status='occupied').count()
    reserved_count = tables.filter(status='reserved').count()
    
    context = {
        'tables': tables,
        'areas': areas,
        'total_count': tables.count(),
        'available_count': available_count,
        'occupied_count': occupied_count,
        'reserved_count': reserved_count,
        'area_filter': area_filter,
        'status_filter': status_filter,
    }
    
    return render(request, 'management/tables_management.html', context)


@manager_required
def users_list(request):
    """Users Management"""
    store_config = StoreConfig.get_current()
    outlet = store_config.outlet
    
    users = User.objects.filter(
        outlet=outlet
    ).order_by('role', 'username')
    
    # Filter by role
    role_filter = request.GET.get('role', '')
    if role_filter:
        users = users.filter(role=role_filter)
    
    # Search
    search = request.GET.get('search', '')
    if search:
        users = users.filter(
            Q(username__icontains=search) | 
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    # Calculate role counts
    admin_count = users.filter(role='admin').count()
    manager_count = users.filter(role='manager').count()
    cashier_count = users.filter(role='cashier').count()
    waiter_count = users.filter(role='waiter').count()
    kitchen_count = users.filter(role='kitchen').count()
    
    context = {
        'users': users,
        'total_count': users.count(),
        'admin_count': admin_count,
        'manager_count': manager_count,
        'cashier_count': cashier_count,
        'waiter_count': waiter_count,
        'kitchen_count': kitchen_count,
        'role_filter': role_filter,
        'search': search,
    }
    
    return render(request, 'management/users.html', context)


@csrf_exempt
@require_POST
@manager_required
def user_set_password(request, user_id):
    """Set/Reset User Password (HTMX)"""
    
    user = get_object_or_404(User, id=user_id)
    new_password = request.POST.get('password', '').strip()
    
    if not new_password:
        return JsonResponse({'error': 'Password cannot be empty'}, status=400)
    
    if len(new_password) < 8:
        return JsonResponse({'error': 'Password must be at least 8 characters'}, status=400)
    
    # Set new password
    user.set_password(new_password)
    user.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Password updated for {user.username}'
    })


@csrf_exempt
@require_POST
@manager_required
def user_set_pin(request, user_id):
    """Set User PIN for POS Login (HTMX)"""
    
    user = get_object_or_404(User, id=user_id)
    new_pin = request.POST.get('pin', '').strip()
    
    if not new_pin:
        return JsonResponse({'error': 'PIN cannot be empty'}, status=400)
    
    if not new_pin.isdigit():
        return JsonResponse({'error': 'PIN must be numeric'}, status=400)
    
    if len(new_pin) != 6:
        return JsonResponse({'error': 'PIN must be exactly 6 digits'}, status=400)
    
    # Set PIN (stored as hashed value for security)
    user.pin = new_pin  # Model will hash it automatically
    user.save()
    
    return JsonResponse({
        'success': True,
        'message': f'PIN set for {user.username}'
    })


@manager_required
def table_areas_list(request):
    """Table Areas Management"""
    store_config = StoreConfig.get_current()
    outlet = store_config.outlet
    
    areas = TableArea.objects.filter(
        outlet=outlet
    ).order_by('sort_order', 'name')
    
    # Count tables per area
    from django.db.models import Count
    areas = areas.annotate(table_count=Count('tables'))
    
    # Search
    search = request.GET.get('search', '')
    if search:
        areas = areas.filter(name__icontains=search)
    
    context = {
        'areas': areas,
        'total_count': areas.count(),
        'search': search,
    }
    
    return render(request, 'management/table_areas.html', context)


@manager_required
def promotions_list(request):
    """Promotions Management"""
    store_config = StoreConfig.get_current()
    outlet = store_config.outlet
    
    promotions = Promotion.objects.filter(
        outlet=outlet
    ).order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        promotions = promotions.filter(is_active=True)
    elif status_filter == 'inactive':
        promotions = promotions.filter(is_active=False)
    
    # Filter by type
    type_filter = request.GET.get('type', '')
    if type_filter:
        promotions = promotions.filter(promo_type=type_filter)
    
    # Search
    search = request.GET.get('search', '')
    if search:
        promotions = promotions.filter(
            Q(name__icontains=search) | Q(code__icontains=search)
        )
    
    # Calculate counts
    active_count = Promotion.objects.filter(outlet=outlet, is_active=True).count()
    inactive_count = Promotion.objects.filter(outlet=outlet, is_active=False).count()
    
    # Check current validity
    now = timezone.now()
    valid_count = Promotion.objects.filter(
        outlet=outlet,
        is_active=True,
        start_date__lte=now,
        end_date__gte=now
    ).count()
    
    context = {
        'promotions': promotions,
        'total_count': promotions.count(),
        'active_count': active_count,
        'inactive_count': inactive_count,
        'valid_count': valid_count,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'search': search,
        'promo_types': Promotion.TYPE_CHOICES,
    }
    
    return render(request, 'management/promotions.html', context)


@manager_required
def vouchers_list(request):
    """Vouchers Management"""
    store_config = StoreConfig.get_current()
    outlet = store_config.outlet
    
    vouchers = Voucher.objects.filter(
        promotion__outlet=outlet
    ).select_related('promotion').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        vouchers = vouchers.filter(is_active=True, is_used=False)
    elif status_filter == 'used':
        vouchers = vouchers.filter(is_used=True)
    elif status_filter == 'inactive':
        vouchers = vouchers.filter(is_active=False)
    
    # Search by code or customer
    search = request.GET.get('search', '')
    if search:
        vouchers = vouchers.filter(
            Q(code__icontains=search) | 
            Q(customer_name__icontains=search) |
            Q(customer_phone__icontains=search)
        )
    
    # Calculate counts
    active_count = Voucher.objects.filter(
        promotion__outlet=outlet,
        is_active=True,
        is_used=False
    ).count()
    used_count = Voucher.objects.filter(
        promotion__outlet=outlet,
        is_used=True
    ).count()
    expired_count = Voucher.objects.filter(
        promotion__outlet=outlet,
        expiry_date__lt=timezone.now(),
        is_used=False
    ).count()
    
    context = {
        'vouchers': vouchers,
        'total_count': vouchers.count(),
        'active_count': active_count,
        'used_count': used_count,
        'expired_count': expired_count,
        'status_filter': status_filter,
        'search': search,
    }
    
    return render(request, 'management/vouchers.html', context)


@manager_required
def bills_list(request):
    """Bills/Transactions List"""
    store_config = StoreConfig.get_current()
    outlet = store_config.outlet
    
    bills = Bill.objects.filter(
        outlet=outlet
    ).select_related('table', 'created_by', 'terminal').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        bills = bills.filter(status=status_filter)
    
    # Filter by date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        bills = bills.filter(created_at__date__gte=date_from)
    if date_to:
        bills = bills.filter(created_at__date__lte=date_to)
    
    # Search by bill number
    search = request.GET.get('search', '')
    if search:
        bills = bills.filter(bill_number__icontains=search)
    
    # Calculate counts and totals (before pagination)
    total_bills = Bill.objects.filter(outlet=outlet).count()
    open_count = Bill.objects.filter(outlet=outlet, status='open').count()
    paid_count = Bill.objects.filter(outlet=outlet, status='paid').count()
    void_count = Bill.objects.filter(outlet=outlet, status='void').count()
    
    total_revenue = Bill.objects.filter(
        outlet=outlet, 
        status='paid'
    ).aggregate(total=Sum('total'))['total'] or Decimal('0')
    
    # Pagination
    paginator = Paginator(bills, 50)  # 50 bills per page
    page = request.GET.get('page', 1)
    
    try:
        bills_page = paginator.page(page)
    except PageNotAnInteger:
        bills_page = paginator.page(1)
    except EmptyPage:
        bills_page = paginator.page(paginator.num_pages)
    
    context = {
        'bills': bills_page,
        'total_count': total_bills,
        'open_count': open_count,
        'paid_count': paid_count,
        'void_count': void_count,
        'total_revenue': total_revenue,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search': search,
    }
    
    return render(request, 'management/bills.html', context)


@manager_required
def payments_list(request):
    """Payments List"""
    store_config = StoreConfig.get_current()
    outlet = store_config.outlet
    
    payments = Payment.objects.filter(
        bill__outlet=outlet
    ).select_related('bill', 'bill__created_by').order_by('-created_at')
    
    # Filter by payment method
    method_filter = request.GET.get('method', '')
    if method_filter:
        payments = payments.filter(method=method_filter)
    
    # Filter by date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        payments = payments.filter(created_at__date__gte=date_from)
    if date_to:
        payments = payments.filter(created_at__date__lte=date_to)
    
    # Search by bill number
    search = request.GET.get('search', '')
    if search:
        payments = payments.filter(bill__bill_number__icontains=search)
    
    # Calculate totals by method (before pagination)
    total_payments = Payment.objects.filter(bill__outlet=outlet).count()
    cash_total = Payment.objects.filter(
        bill__outlet=outlet, method='cash'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    card_total = Payment.objects.filter(
        bill__outlet=outlet, method='card'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    qris_total = Payment.objects.filter(
        bill__outlet=outlet, method='qris'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    total_amount = Payment.objects.filter(
        bill__outlet=outlet
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Pagination
    paginator = Paginator(payments, 50)  # 50 payments per page
    page = request.GET.get('page', 1)
    
    try:
        payments_page = paginator.page(page)
    except PageNotAnInteger:
        payments_page = paginator.page(1)
    except EmptyPage:
        payments_page = paginator.page(paginator.num_pages)
    
    context = {
        'payments': payments_page,
        'total_count': total_payments,
        'cash_total': cash_total,
        'card_total': card_total,
        'qris_total': qris_total,
        'total_amount': total_amount,
        'method_filter': method_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search': search,
    }
    
    return render(request, 'management/payments.html', context)


@manager_required
def store_sessions_list(request):
    """Store Sessions List"""
    store_config = StoreConfig.get_current()
    
    sessions = StoreSession.objects.filter(
        store=store_config
    ).order_by('-opened_at')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'open':
        sessions = sessions.filter(closed_at__isnull=True)
    elif status_filter == 'closed':
        sessions = sessions.filter(closed_at__isnull=False)
    
    # Calculate counts (before pagination)
    total_sessions = StoreSession.objects.filter(store=store_config).count()
    open_sessions = StoreSession.objects.filter(
        store=store_config, closed_at__isnull=True
    ).count()
    closed_sessions = StoreSession.objects.filter(
        store=store_config, closed_at__isnull=False
    ).count()
    
    # Pagination
    paginator = Paginator(sessions, 30)  # 30 sessions per page
    page = request.GET.get('page', 1)
    
    try:
        sessions_page = paginator.page(page)
    except PageNotAnInteger:
        sessions_page = paginator.page(1)
    except EmptyPage:
        sessions_page = paginator.page(paginator.num_pages)
    
    context = {
        'sessions': sessions_page,
        'total_count': total_sessions,
        'open_count': open_sessions,
        'closed_count': closed_sessions,
        'status_filter': status_filter,
    }
    
    return render(request, 'management/store_sessions.html', context)


# ===========================
# REPORTS & ANALYTICS
# ===========================

@manager_required
def reports_dashboard(request):
    """Reports overview dashboard"""
    store_config = StoreConfig.get_current()
    outlet = store_config.outlet
    
    # Quick stats for last 7 days
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    last_week_revenue = Bill.objects.filter(
        outlet=outlet,
        status='paid',
        created_at__date__gte=week_ago
    ).aggregate(total=Sum('total'))['total'] or Decimal('0')
    
    last_week_bills = Bill.objects.filter(
        outlet=outlet,
        status='paid',
        created_at__date__gte=week_ago
    ).count()
    
    context = {
        'last_week_revenue': last_week_revenue,
        'last_week_bills': last_week_bills,
        'avg_transaction': last_week_revenue / last_week_bills if last_week_bills > 0 else 0,
    }
    
    return render(request, 'management/reports/dashboard.html', context)


@manager_required
def sales_report(request):
    """Sales report with period selection"""
    store_config = StoreConfig.get_current()
    outlet = store_config.outlet
    
    # Get date range from request
    period = request.GET.get('period', 'today')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    today = timezone.now().date()
    
    # Calculate date range based on period
    if period == 'today':
        date_from = today
        date_to = today
    elif period == 'yesterday':
        date_from = today - timedelta(days=1)
        date_to = today - timedelta(days=1)
    elif period == 'week':
        date_from = today - timedelta(days=today.weekday())
        date_to = today
    elif period == 'last_week':
        date_from = today - timedelta(days=today.weekday() + 7)
        date_to = today - timedelta(days=today.weekday() + 1)
    elif period == 'month':
        date_from = today.replace(day=1)
        date_to = today
    elif period == 'last_month':
        last_month = today.replace(day=1) - timedelta(days=1)
        date_from = last_month.replace(day=1)
        date_to = last_month
    elif period == 'custom' and start_date and end_date:
        date_from = datetime.strptime(start_date, '%Y-%m-%d').date()
        date_to = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        date_from = today
        date_to = today
    
    # Get bills in date range
    bills = Bill.objects.filter(
        outlet=outlet,
        status='paid',
        created_at__date__gte=date_from,
        created_at__date__lte=date_to
    )
    
    # Calculate metrics
    total_revenue = bills.aggregate(total=Sum('total'))['total'] or Decimal('0')
    total_bills = bills.count()
    avg_bill = total_revenue / total_bills if total_bills > 0 else Decimal('0')
    
    # Subtotals breakdown
    subtotal_sum = bills.aggregate(sum=Sum('subtotal'))['sum'] or Decimal('0')
    discount_sum = bills.aggregate(sum=Sum('discount_amount'))['sum'] or Decimal('0')
    tax_sum = bills.aggregate(sum=Sum('tax_amount'))['sum'] or Decimal('0')
    service_sum = bills.aggregate(sum=Sum('service_charge'))['sum'] or Decimal('0')
    
    # Daily breakdown
    from django.db.models.functions import TruncDate
    daily_sales = bills.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        revenue=Sum('total'),
        count=Count('id')
    ).order_by('date')
    
    # Comparison with previous period
    period_days = (date_to - date_from).days + 1
    prev_start = date_from - timedelta(days=period_days)
    prev_end = date_from - timedelta(days=1)
    
    prev_bills = Bill.objects.filter(
        outlet=outlet,
        status='paid',
        created_at__date__gte=prev_start,
        created_at__date__lte=prev_end
    )
    
    prev_revenue = prev_bills.aggregate(total=Sum('total'))['total'] or Decimal('0')
    revenue_growth = ((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else Decimal('0')
    
    context = {
        'period': period,
        'date_from': date_from,
        'date_to': date_to,
        'total_revenue': total_revenue,
        'total_bills': total_bills,
        'avg_bill': avg_bill,
        'subtotal_sum': subtotal_sum,
        'discount_sum': discount_sum,
        'tax_sum': tax_sum,
        'service_sum': service_sum,
        'daily_sales': list(daily_sales),
        'prev_revenue': prev_revenue,
        'revenue_growth': revenue_growth,
    }
    
    return render(request, 'management/reports/sales.html', context)


@manager_required
def products_report(request):
    """Top products and categories analysis"""
    store_config = StoreConfig.get_current()
    outlet = store_config.outlet
    
    # Get date range
    period = request.GET.get('period', 'week')
    today = timezone.now().date()
    
    if period == 'today':
        date_from = today
    elif period == 'week':
        date_from = today - timedelta(days=7)
    elif period == 'month':
        date_from = today - timedelta(days=30)
    else:
        date_from = today - timedelta(days=7)
    
    # Top products by quantity
    from apps.pos.models import BillItem
    top_products_qty = BillItem.objects.filter(
        bill__outlet=outlet,
        bill__status='paid',
        bill__created_at__date__gte=date_from,
        is_void=False
    ).values(
        'product__name',
        'product__category__name'
    ).annotate(
        total_qty=Sum('quantity'),
        total_revenue=Sum('total')
    ).order_by('-total_qty')[:20]
    
    # Top products by revenue
    top_products_revenue = BillItem.objects.filter(
        bill__outlet=outlet,
        bill__status='paid',
        bill__created_at__date__gte=date_from,
        is_void=False
    ).values(
        'product__name',
        'product__category__name'
    ).annotate(
        total_qty=Sum('quantity'),
        total_revenue=Sum('total')
    ).order_by('-total_revenue')[:20]
    
    # Category performance
    category_performance = BillItem.objects.filter(
        bill__outlet=outlet,
        bill__status='paid',
        bill__created_at__date__gte=date_from,
        is_void=False
    ).values(
        'product__category__name'
    ).annotate(
        total_qty=Sum('quantity'),
        total_revenue=Sum('total'),
        product_count=Count('product', distinct=True)
    ).order_by('-total_revenue')
    
    context = {
        'period': period,
        'date_from': date_from,
        'top_products_qty': list(top_products_qty),
        'top_products_revenue': list(top_products_revenue),
        'category_performance': list(category_performance),
    }
    
    return render(request, 'management/reports/products.html', context)


@manager_required
def cashier_report(request):
    """Cashier performance report"""
    store_config = StoreConfig.get_current()
    outlet = store_config.outlet
    
    # Get date range
    period = request.GET.get('period', 'today')
    today = timezone.now().date()
    
    if period == 'today':
        date_from = today
        date_to = today
    elif period == 'week':
        date_from = today - timedelta(days=7)
        date_to = today
    elif period == 'month':
        date_from = today - timedelta(days=30)
        date_to = today
    else:
        date_from = today
        date_to = today
    
    # Cashier performance
    cashier_stats = Bill.objects.filter(
        outlet=outlet,
        created_at__date__gte=date_from,
        created_at__date__lte=date_to
    ).values(
        'created_by__username',
        'created_by__first_name',
        'created_by__last_name'
    ).annotate(
        total_bills=Count('id'),
        paid_bills=Count('id', filter=Q(status='paid')),
        cancelled_bills=Count('id', filter=Q(status='cancelled')),
        total_revenue=Sum('total', filter=Q(status='paid')),
        avg_bill=Avg('total', filter=Q(status='paid'))
    ).order_by('-total_revenue')
    
    # Void items by cashier
    from apps.pos.models import BillItem
    void_stats = BillItem.objects.filter(
        bill__outlet=outlet,
        bill__created_at__date__gte=date_from,
        bill__created_at__date__lte=date_to,
        is_void=True
    ).values(
        'bill__created_by__username'
    ).annotate(
        void_count=Count('id'),
        void_amount=Sum('total')
    )
    
    void_dict = {item['bill__created_by__username']: item for item in void_stats}
    
    # Merge void stats into cashier stats
    cashier_list = []
    for cashier in cashier_stats:
        username = cashier['created_by__username']
        cashier['void_count'] = void_dict.get(username, {}).get('void_count', 0)
        cashier['void_amount'] = void_dict.get(username, {}).get('void_amount', Decimal('0'))
        cashier_list.append(cashier)
    
    context = {
        'period': period,
        'date_from': date_from,
        'date_to': date_to,
        'cashier_stats': cashier_list,
    }
    
    return render(request, 'management/reports/cashier.html', context)


@manager_required
def payment_report(request):
    """Payment method breakdown"""
    store_config = StoreConfig.get_current()
    outlet = store_config.outlet
    
    # Get date range
    period = request.GET.get('period', 'today')
    today = timezone.now().date()
    
    if period == 'today':
        date_from = today
        date_to = today
    elif period == 'week':
        date_from = today - timedelta(days=7)
        date_to = today
    elif period == 'month':
        date_from = today - timedelta(days=30)
        date_to = today
    else:
        date_from = today
        date_to = today
    
    # Payment method breakdown
    payment_breakdown = Payment.objects.filter(
        bill__outlet=outlet,
        bill__status='paid',
        created_at__date__gte=date_from,
        created_at__date__lte=date_to
    ).values('method').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).order_by('-total')
    
    # Daily payment trends
    from django.db.models.functions import TruncDate
    daily_payments = Payment.objects.filter(
        bill__outlet=outlet,
        bill__status='paid',
        created_at__date__gte=date_from,
        created_at__date__lte=date_to
    ).annotate(
        date=TruncDate('created_at')
    ).values('date', 'method').annotate(
        total=Sum('amount')
    ).order_by('date', 'method')
    
    # Calculate totals
    total_amount = sum(item['total'] for item in payment_breakdown)
    
    context = {
        'period': period,
        'date_from': date_from,
        'date_to': date_to,
        'payment_breakdown': list(payment_breakdown),
        'daily_payments': list(daily_payments),
        'total_amount': total_amount,
    }
    
    return render(request, 'management/reports/payment.html', context)


@manager_required
def void_discount_report(request):
    """Void and discount analysis"""
    store_config = StoreConfig.get_current()
    outlet = store_config.outlet
    
    # Get date range
    period = request.GET.get('period', 'week')
    today = timezone.now().date()
    
    if period == 'today':
        date_from = today
    elif period == 'week':
        date_from = today - timedelta(days=7)
    elif period == 'month':
        date_from = today - timedelta(days=30)
    else:
        date_from = today - timedelta(days=7)
    
    # Void items analysis
    from apps.pos.models import BillItem
    void_items = BillItem.objects.filter(
        bill__outlet=outlet,
        bill__created_at__date__gte=date_from,
        is_void=True
    ).select_related('product', 'bill__created_by')
    
    void_summary = void_items.aggregate(
        count=Count('id'),
        total_amount=Sum('total')
    )
    
    # Void by product
    void_by_product = void_items.values(
        'product__name'
    ).annotate(
        count=Count('id'),
        amount=Sum('total')
    ).order_by('-count')[:10]
    
    # Void by cashier
    void_by_cashier = void_items.values(
        'bill__created_by__username'
    ).annotate(
        count=Count('id'),
        amount=Sum('total')
    ).order_by('-count')
    
    # Discount analysis
    bills_with_discount = Bill.objects.filter(
        outlet=outlet,
        created_at__date__gte=date_from,
        discount_amount__gt=0
    )
    
    discount_summary = bills_with_discount.aggregate(
        count=Count('id'),
        total_discount=Sum('discount_amount')
    )
    
    # Discount by type (if you have discount reason field)
    discount_breakdown = bills_with_discount.values(
        'discount_percent'
    ).annotate(
        count=Count('id'),
        total=Sum('discount_amount')
    ).order_by('-total')
    
    context = {
        'period': period,
        'date_from': date_from,
        'void_summary': void_summary,
        'void_by_product': list(void_by_product),
        'void_by_cashier': list(void_by_cashier),
        'discount_summary': discount_summary,
        'discount_breakdown': list(discount_breakdown),
    }
    
    return render(request, 'management/reports/void_discount.html', context)


@manager_required
def peak_hours_report(request):
    """Peak hours and time-based analysis"""
    store_config = StoreConfig.get_current()
    outlet = store_config.outlet
    
    # Get date range
    period = request.GET.get('period', 'week')
    today = timezone.now().date()
    
    if period == 'today':
        date_from = today
    elif period == 'week':
        date_from = today - timedelta(days=7)
    elif period == 'month':
        date_from = today - timedelta(days=30)
    else:
        date_from = today - timedelta(days=7)
    
    # Hourly sales distribution
    from django.db.models.functions import ExtractHour
    hourly_sales = Bill.objects.filter(
        outlet=outlet,
        status='paid',
        created_at__date__gte=date_from
    ).annotate(
        hour=ExtractHour('created_at')
    ).values('hour').annotate(
        count=Count('id'),
        revenue=Sum('total')
    ).order_by('hour')
    
    # Day of week analysis
    from django.db.models.functions import ExtractWeekDay
    daily_sales = Bill.objects.filter(
        outlet=outlet,
        status='paid',
        created_at__date__gte=date_from
    ).annotate(
        weekday=ExtractWeekDay('created_at')
    ).values('weekday').annotate(
        count=Count('id'),
        revenue=Sum('total')
    ).order_by('weekday')
    
    # Map weekday numbers to names
    weekday_names = {
        1: 'Sunday', 2: 'Monday', 3: 'Tuesday', 4: 'Wednesday',
        5: 'Thursday', 6: 'Friday', 7: 'Saturday'
    }
    
    daily_sales_list = []
    for item in daily_sales:
        item['weekday_name'] = weekday_names.get(item['weekday'], 'Unknown')
        daily_sales_list.append(item)
    
    # Find peak hour
    peak_hour = max(hourly_sales, key=lambda x: x['revenue']) if hourly_sales else None
    
    context = {
        'period': period,
        'date_from': date_from,
        'hourly_sales': list(hourly_sales),
        'daily_sales': daily_sales_list,
        'peak_hour': peak_hour,
    }
    
    return render(request, 'management/reports/peak_hours.html', context)


@manager_required
def export_sales_excel(request):
    """Export sales report to Excel"""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from django.http import HttpResponse
    
    store_config = StoreConfig.get_current()
    outlet = store_config.outlet
    
    # Get date range from request
    period = request.GET.get('period', 'today')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    today = timezone.now().date()
    
    # Calculate date range
    if period == 'today':
        date_from = today
        date_to = today
    elif period == 'week':
        date_from = today - timedelta(days=7)
        date_to = today
    elif period == 'month':
        date_from = today - timedelta(days=30)
        date_to = today
    elif period == 'custom' and start_date and end_date:
        date_from = datetime.strptime(start_date, '%Y-%m-%d').date()
        date_to = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        date_from = today
        date_to = today
    
    # Get bills
    bills = Bill.objects.filter(
        outlet=outlet,
        status='paid',
        created_at__date__gte=date_from,
        created_at__date__lte=date_to
    ).order_by('created_at')
    
    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sales Report"
    
    # Header styling
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    
    # Title
    ws['A1'] = f"Sales Report: {outlet.name}"
    ws['A1'].font = Font(size=14, bold=True)
    ws['A2'] = f"Period: {date_from} to {date_to}"
    
    # Headers
    headers = ['Date', 'Bill Number', 'Table', 'Cashier', 'Subtotal', 'Discount', 'Tax', 'Service', 'Total', 'Payment Method']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')
    
    # Data rows
    row = 5
    for bill in bills:
        payment_methods = ', '.join([p.method for p in bill.payments.all()])
        
        ws.cell(row=row, column=1).value = bill.created_at.strftime('%Y-%m-%d %H:%M')
        ws.cell(row=row, column=2).value = bill.bill_number
        ws.cell(row=row, column=3).value = str(bill.table) if bill.table else '-'
        ws.cell(row=row, column=4).value = bill.created_by.username
        ws.cell(row=row, column=5).value = float(bill.subtotal)
        ws.cell(row=row, column=6).value = float(bill.discount_amount)
        ws.cell(row=row, column=7).value = float(bill.tax_amount)
        ws.cell(row=row, column=8).value = float(bill.service_charge)
        ws.cell(row=row, column=9).value = float(bill.total)
        ws.cell(row=row, column=10).value = payment_methods
        row += 1
    
    # Totals
    total_row = row + 1
    ws.cell(row=total_row, column=4).value = "TOTAL:"
    ws.cell(row=total_row, column=4).font = Font(bold=True)
    
    total_revenue = bills.aggregate(total=Sum('total'))['total'] or Decimal('0')
    ws.cell(row=total_row, column=9).value = float(total_revenue)
    ws.cell(row=total_row, column=9).font = Font(bold=True)
    
    # Adjust column widths
    ws.column_dimensions['A'].width = 18
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 10
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 12
    ws.column_dimensions['G'].width = 12
    ws.column_dimensions['H'].width = 12
    ws.column_dimensions['I'].width = 12
    ws.column_dimensions['J'].width = 20
    
    # Create response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=sales_report_{date_from}_{date_to}.xlsx'
    
    wb.save(response)
    return response


@manager_required
def product_photos(request, product_id):
    """Product photo gallery management"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        # Handle photo upload
        image = request.FILES.get('image')
        caption = request.POST.get('caption', '')
        order = int(request.POST.get('order', 0))
        
        if image:
            # Validate file size (5MB max)
            if image.size > 5 * 1024 * 1024:
                return render(request, 'management/product_photos.html', {
                    'product': product,
                    'photos': product.photos.all(),
                    'error': 'File size must be less than 5MB'
                })
            
            # Create photo
            ProductPhoto.objects.create(
                product=product,
                image=image,
                caption=caption,
                order=order
            )
    
    photos = product.photos.all()
    
    return render(request, 'management/product_photos.html', {
        'product': product,
        'photos': photos,
    })


@manager_required
def product_photo_toggle(request, product_id, photo_id):
    """Toggle photo active status"""
    photo = get_object_or_404(ProductPhoto, id=photo_id, product_id=product_id)
    photo.is_active = not photo.is_active
    photo.save()
    
    from django.shortcuts import redirect
    return redirect('management:product_photos', product_id=product_id)


@manager_required
def product_photo_delete(request, product_id, photo_id):
    """Delete product photo"""
    photo = get_object_or_404(ProductPhoto, id=photo_id, product_id=product_id)
    photo.delete()
    
    from django.shortcuts import redirect
    return redirect('management:product_photos', product_id=product_id)


@manager_required
def product_detail(request, product_id):
    """View Product Detail"""
    store_config = StoreConfig.get_current()
    outlet = store_config.outlet
    
    product = get_object_or_404(
        Product.objects.select_related('category').prefetch_related(
            'modifiers__options', 'photos'
        ),
        id=product_id,
        category__outlet=outlet
    )
    
    context = {
        'product': product,
    }
    
    return render(request, 'management/product_detail.html', context)


@manager_required
def product_edit(request, product_id):
    """Edit Product"""
    store_config = StoreConfig.get_current()
    outlet = store_config.outlet
    
    product = get_object_or_404(
        Product.objects.select_related('category'),
        id=product_id,
        category__outlet=outlet
    )
    
    if request.method == 'POST':
        # Update product
        product.name = request.POST.get('name', product.name)
        product.sku = request.POST.get('sku', product.sku)
        product.description = request.POST.get('description', '')
        product.price = Decimal(request.POST.get('price', product.price))
        product.cost = Decimal(request.POST.get('cost', 0))
        product.stock_quantity = int(request.POST.get('stock_quantity', product.stock_quantity))
        product.low_stock_alert = int(request.POST.get('low_stock_alert', product.low_stock_alert))
        product.printer_target = request.POST.get('printer_target', product.printer_target)
        product.is_active = request.POST.get('is_active') == 'on'
        product.track_stock = request.POST.get('track_stock') == 'on'
        
        # Handle category
        category_id = request.POST.get('category')
        if category_id:
            category = Category.objects.filter(id=category_id, outlet=outlet).first()
            if category:
                product.category = category
        
        # Handle image upload
        if 'image' in request.FILES:
            # Delete old image if exists
            if product.image:
                product.image.delete(save=False)
            product.image = request.FILES['image']
        
        product.save()
        
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.success(request, f'Product "{product.name}" updated successfully!')
        return redirect('management:products')
    
    # GET request - show form
    categories = Category.objects.filter(outlet=outlet).order_by('name')
    
    context = {
        'product': product,
        'categories': categories,
    }
    
    return render(request, 'management/product_edit.html', context)


@manager_required
def import_excel_page(request):
    """Import Excel Page"""
    return render(request, 'management/import_excel.html')


@manager_required
def download_excel_template(request):
    """Download Excel Template for Product Import"""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from django.http import HttpResponse
    
    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Product Import"
    
    # Header styling
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True, size=11)
    header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Headers with new structure
    headers = [
        'Category',
        'Menu Category', 
        'Nama Product',
        'PLU Product',
        'Printer Kitchen',     # Printer target (kitchen/bar/dessert/none)
        'Condiment Groups',    # 🆕 Comma-separated group names (e.g., "Coffee Taste,Size,Ice Level")
        'Price Product',
        'Image Product'
    ]
    
    # Write headers
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment
        cell.border = thin_border
    
    # Example data - NEW FORMAT: Comma-separated group references
    examples = [
        # Hot Americano - references 3 groups
        ['Beverage', 'Hot Coffee', 'Hot Americano', '03835821', 'bar', 'Coffee Taste,Size,Ice Level', 27000, 'avril/images/menus/americano.jpg'],
        
        # Hot Cappuccino - references 3 groups (Coffee Taste is REUSED!)
        ['Beverage', 'Hot Coffee', 'Hot Cappuccino', '03835822', 'bar', 'Coffee Taste,Size,Sugar Level', 33000, 'avril/images/menus/cappuccino.jpg'],
        
        # Ice Latte - references 3 groups (Coffee Taste and Size are REUSED!)
        ['Beverage', 'Ice Coffee', 'Ice Latte', '03835823', 'bar', 'Coffee Taste,Size,Ice Level', 35000, 'avril/images/menus/latte.jpg'],
        
        # Food with Spicy Level
        ['Food', 'Nasi Goreng', 'Nasi Goreng Special', '12345', 'kitchen', 'Spicy Level,Extra Topping', 35000, 'avril/images/menus/nasi_goreng.jpg'],
        
        # Food with multiple groups
        ['Food', 'Mie Goreng', 'Mie Goreng Special', '12346', 'kitchen', 'Spicy Level,Extra Topping', 30000, 'avril/images/menus/mie_goreng.jpg'],
        
        # Product without condiments (empty column is OK)
        ['Beverage', 'Bottled Drinks', 'Mineral Water', '99999', 'none', '', 5000, 'avril/images/menus/water.jpg'],
    ]
    
    # Write example data
    for row_idx, row_data in enumerate(examples, 2):
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.value = value
            cell.border = thin_border
            if col_idx == 4:  # PLU Product - monospace
                cell.font = Font(name='Courier New')
    
    # Set column widths
    ws.column_dimensions['A'].width = 12  # Category
    ws.column_dimensions['B'].width = 15  # Menu Category
    ws.column_dimensions['C'].width = 22  # Nama Product
    ws.column_dimensions['D'].width = 12  # PLU Product
    ws.column_dimensions['E'].width = 18  # Printer Kitchen
    ws.column_dimensions['F'].width = 35  # Condiment Groups (comma-separated)
    ws.column_dimensions['G'].width = 13  # Price Product
    ws.column_dimensions['H'].width = 45  # Image Product
    
    # Add instructions sheet
    ws2 = wb.create_sheet("Instructions")
    ws2['A1'] = "📋 PRODUCT IMPORT TEMPLATE v3.0 - TWO-FILE SYSTEM"
    ws2['A1'].font = Font(size=14, bold=True, color="10b981")
    
    instructions = [
        "",
        "🎯 Column Descriptions:",
        "",
        "1. Category: Main product category (e.g., Beverage, Food)",
        "2. Menu Category: Sub-category for grouping (e.g., Hot Coffee, Ice Coffee)",
        "3. Nama Product: Product name",
        "4. PLU Product: Product PLU/SKU code (unique identifier)",
        "5. Printer Kitchen: Printer target (kitchen/bar/dessert/none) - default: kitchen",
        "6. Condiment Groups: 🆕 COMMA-SEPARATED group names (e.g., Coffee Taste,Size,Ice Level)",
        "7. Price Product: Base product price",
        "8. Image Product: Path to product image",
        "11. Image Product: Path to product image (e.g., avril/images/menus/product.jpg)",
        "",
        "✨ Printer Kitchen Feature:",
        "",
        "🔄 TWO-FILE IMPORT SYSTEM:",
        "",
        "Step 1: Import Condiment Groups FIRST",
        "  • Go to: Master Data → Import Condiment Groups",
        "  • Define all your modifier groups with their options",
        "  • Examples: Coffee Taste (Bold, Fruity), Size (Regular, Large)",
        "",
        "Step 2: Import Products (this file)",
        "  • Products REFERENCE groups by name",
        "  • Use comma-separated group names in 'Condiment Groups' column",
        "  • Example: Coffee Taste,Size,Ice Level",
        "",
        "✨ Condiment Groups Column:",
        "",
        "• Comma-separated list of group names (no spaces after comma)",
        "• Groups must exist (import them first!)",
        "• Leave empty if product has no modifiers",
        "• Examples:",
        "  - Coffee Taste,Size → Product uses 2 groups",
        "  - Spicy Level,Extra Topping → Food with 2 groups",
        "  - (empty) → Product has no modifiers",
        "",
        "🖨️ Printer Kitchen:",
        "",
        "• kitchen: Food items (Nasi Goreng, Mie Goreng, Steak)",
        "• bar: Beverages (Coffee, Juice, Cocktails)",
        "• dessert: Desserts (Cake, Ice Cream, Pudding)",
        "• none: Items that don't need kitchen printing",
        "",
        "📝 Important Notes:",
        "",
        "• One row = One product (much cleaner!)",
        "• Groups are REUSABLE - define once, use everywhere",
        "• Update group once → affects ALL products using it",
        "• Images must be placed in media/products/ directory before import",
        "",
        "💡 Benefits of Two-File System:",
        "",
        "• Cleaner Excel: 1 row per product (vs 10+ rows in old format)",
        "• No duplication: Define 'Coffee Taste' once, use for all coffees",
        "• No typos: Reference exact group names",
        "• Easy updates: Change group options → all products updated",
        "",
        "⚠️ Common Mistakes:",
        "",
        "• Forgot to import groups first → Products won't find them",
        "• Typo in group name → System won't find the group",
        "• Spaces after commas → Use: Coffee Taste,Size (not: Coffee Taste, Size)",
    ]
    
    for idx, instruction in enumerate(instructions, 1):
        ws2[f'A{idx}'] = instruction
        if instruction.startswith('🎯') or instruction.startswith('✨') or instruction.startswith('📝') or instruction.startswith('🔄') or instruction.startswith('💡') or instruction.startswith('🖨️') or instruction.startswith('⚠️'):
            ws2[f'A{idx}'].font = Font(bold=True, size=12, color="10b981")
        elif instruction.startswith('•') or instruction.startswith('Step'):
            ws2[f'A{idx}'].font = Font(size=10)
        else:
            ws2[f'A{idx}'].font = Font(size=10)
    
    ws2.column_dimensions['A'].width = 100
    
    # Create HTTP response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=Product_Import_Template_v3.xlsx'
    
    wb.save(response)
    return response


@manager_required
def download_condiment_groups_template(request):
    """Download Excel Template for Condiment Groups Import"""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from django.http import HttpResponse
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Condiment Groups"
    
    # Header styling
    header_fill = PatternFill(start_color="10b981", end_color="10b981", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True, size=11)
    header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    headers = ['Group Name', 'Option Name', 'Fee', 'Is Required', 'Max Selections']
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment
        cell.border = thin_border
    
    # Example data
    examples = [
        ['Coffee Taste', 'Bold', 0, 'No', 1],
        ['Coffee Taste', 'Fruity', 0, 'No', 1],
        ['Spicy Level', 'No Chili', 0, 'No', 1],
        ['Spicy Level', 'Medium', 1000, 'No', 1],
        ['Spicy Level', 'Hot', 2000, 'No', 1],
        ['Size', 'Regular', 0, 'Yes', 1],
        ['Size', 'Large', 5000, 'Yes', 1],
        ['Sugar Level', 'No Sugar', 0, 'No', 1],
        ['Sugar Level', 'Normal', 0, 'No', 1],
        ['Ice Level', 'Less Ice', 0, 'No', 1],
        ['Ice Level', 'Normal', 0, 'No', 1],
        ['Milk Upgrade', 'Regular Milk', 0, 'No', 1],
        ['Milk Upgrade', 'Oat Milk', 8000, 'No', 1],
        ['Extra Topping', 'Telur', 5000, 'No', 3],
        ['Extra Topping', 'Keju', 8000, 'No', 3],
    ]
    
    for row_idx, row_data in enumerate(examples, 2):
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.value = value
            cell.border = thin_border
            if col_idx in [3, 4, 5]:
                cell.alignment = Alignment(horizontal='center', vertical='center')
    
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 25
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 18
    
    # Instructions sheet
    ws2 = wb.create_sheet(title="Instructions")
    instructions = [
        "",
        "Condiment Groups Import Instructions",
        "",
        "1. Group Name: Modifier group name (Coffee Taste, Spicy Level)",
        "2. Option Name: Option within group (Bold, Medium, Large)",
        "3. Fee: Additional charge (0 = free)",
        "4. Is Required: Yes/No (must customer choose?)",
        "5. Max Selections: How many options can be selected (usually 1)",
        "",
        "Groups are REUSABLE across products!",
        "Import groups FIRST, then products will reference them.",
    ]
    
    for idx, instruction in enumerate(instructions, 1):
        ws2[f'A{idx}'] = instruction
        ws2[f'A{idx}'].font = Font(size=10)
    
    ws2.column_dimensions['A'].width = 100
    
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=Condiment_Groups_Template.xlsx'
    
    wb.save(response)
    return response


@manager_required
def import_condiment_groups(request):
    """Condiment Groups Import Page"""
    from apps.core.models import Modifier
    
    store_config = StoreConfig.get_current()
    outlet = store_config.outlet
    groups_count = Modifier.objects.filter(outlet=outlet).count()
    
    context = {'groups_count': groups_count}
    return render(request, 'management/import_condiment_groups.html', context)


@manager_required
def import_condiment_groups_process(request):
    """Process Condiment Groups Excel Import"""
    from django.contrib import messages
    from django.shortcuts import redirect
    import openpyxl
    from apps.core.models import Modifier, ModifierOption
    
    if request.method != 'POST':
        return redirect('management:import_condiment_groups')
    
    if 'excel_file' not in request.FILES:
        messages.error(request, 'Please select an Excel file')
        return redirect('management:import_condiment_groups')
    
    excel_file = request.FILES['excel_file']
    update_existing = request.POST.get('update_existing') == 'on'
    
    try:
        wb = openpyxl.load_workbook(excel_file)
        sheet = wb.active
        
        store_config = StoreConfig.get_current()
        outlet = store_config.outlet
        
        stats = {'groups': 0, 'options': 0, 'updated': 0, 'errors': []}
        
        headers = [cell.value for cell in sheet[1]]
        col_indices = {}
        for idx, header in enumerate(headers):
            if header:
                col_indices[header.strip()] = idx
        
        required_cols = ['Group Name', 'Option Name', 'Fee']
        missing_cols = [col for col in required_cols if col not in col_indices]
        if missing_cols:
            messages.error(request, f'Missing required columns: {", ".join(missing_cols)}')
            return redirect('management:import_condiment_groups')
        
        processed_groups = {}
        
        for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            if not row or not any(row):
                continue
            
            try:
                group_name = row[col_indices['Group Name']]
                option_name = row[col_indices['Option Name']]
                fee = row[col_indices['Fee']]
                is_required = row[col_indices.get('Is Required', -1)] if 'Is Required' in col_indices else None
                max_selections = row[col_indices.get('Max Selections', -1)] if 'Max Selections' in col_indices else None
                
                if not group_name or not option_name:
                    continue
                
                group_name = str(group_name).strip()
                option_name = str(option_name).strip()
                
                if group_name not in processed_groups:
                    is_req = False
                    if is_required:
                        is_req_str = str(is_required).strip().lower()
                        is_req = is_req_str in ['yes', 'y', 'true', '1']
                    
                    max_sel = 1
                    if max_selections:
                        try:
                            max_sel = int(max_selections)
                        except:
                            max_sel = 1
                    
                    modifier, created = Modifier.objects.get_or_create(
                        name=group_name,
                        outlet=outlet,
                        defaults={'is_required': is_req, 'max_selections': max_sel}
                    )
                    
                    if created:
                        stats['groups'] += 1
                    elif update_existing:
                        modifier.is_required = is_req
                        modifier.max_selections = max_sel
                        modifier.save()
                        stats['updated'] += 1
                    
                    processed_groups[group_name] = modifier
                else:
                    modifier = processed_groups[group_name]
                
                option, opt_created = ModifierOption.objects.get_or_create(
                    modifier=modifier,
                    name=option_name,
                    defaults={'price_adjustment': Decimal(str(fee)) if fee else Decimal('0')}
                )
                
                if opt_created:
                    stats['options'] += 1
                elif update_existing:
                    new_fee = Decimal(str(fee)) if fee else Decimal('0')
                    if option.price_adjustment != new_fee:
                        option.price_adjustment = new_fee
                        option.save()
                        stats['updated'] += 1
                
            except Exception as e:
                stats['errors'].append(f'Row {row_idx}: {str(e)}')
                continue
        
        msg_parts = []
        if stats['groups'] > 0:
            msg_parts.append(f"{stats['groups']} groups created")
        if stats['options'] > 0:
            msg_parts.append(f"{stats['options']} options added")
        if stats['updated'] > 0:
            msg_parts.append(f"{stats['updated']} items updated")
        
        if msg_parts:
            messages.success(request, f'Import successful: {", ".join(msg_parts)}')
        
        if stats['errors']:
            for error in stats['errors'][:5]:
                messages.warning(request, error)
        
        return redirect('management:import_condiment_groups')
        
    except Exception as e:
        messages.error(request, f'Import failed: {str(e)}')
        return redirect('management:import_condiment_groups')


@csrf_exempt
@require_POST
@manager_required
def import_excel_reset(request):
    """Reset all products, categories, and modifiers"""
    from apps.core.models import Modifier, ModifierOption
    
    try:
        store_config = StoreConfig.get_current()
        outlet = store_config.outlet
        
        # Count before deletion
        modifier_count = Modifier.objects.filter(outlet=outlet).count()
        product_count = Product.objects.filter(category__outlet=outlet).count()
        category_count = Category.objects.filter(outlet=outlet).count()
        
        # Delete in correct order to avoid FK constraints
        # 1. Clear M2M relationships first
        for modifier in Modifier.objects.filter(outlet=outlet):
            modifier.products.clear()
        
        # 2. Delete modifier options
        modifier_ids = list(Modifier.objects.filter(outlet=outlet).values_list('id', flat=True))
        ModifierOption.objects.filter(modifier_id__in=modifier_ids).delete()
        
        # 3. Delete modifiers
        Modifier.objects.filter(outlet=outlet).delete()
        
        # 4. Delete products
        Product.objects.filter(category__outlet=outlet).delete()
        
        # 5. Delete categories
        Category.objects.filter(outlet=outlet).delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully deleted {category_count} categories, {product_count} products, and {modifier_count} modifiers'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@manager_required
def import_excel_process(request):
    """Process Excel Import"""
    from django.contrib import messages
    from django.shortcuts import redirect
    import openpyxl
    import os
    from pathlib import Path
    
    if request.method != 'POST':
        return redirect('management:import_excel')
    
    if 'excel_file' not in request.FILES:
        messages.error(request, 'Please select an Excel file')
        return redirect('management:import_excel')
    
    excel_file = request.FILES['excel_file']
    skip_duplicates = request.POST.get('skip_duplicates') == 'on'
    update_existing = request.POST.get('update_existing') == 'on'
    create_modifiers = request.POST.get('create_modifiers') == 'on'
    
    try:
        # Load workbook
        wb = openpyxl.load_workbook(excel_file)
        sheet = wb.active
        
        store_config = StoreConfig.get_current()
        outlet = store_config.outlet
        
        stats = {
            'categories': 0,
            'products': 0,
            'modifiers': 0,
            'skipped': 0,
            'updated': 0,
            'errors': []
        }
        
        # Get header row
        headers = [cell.value for cell in sheet[1]]
        
        # Find column indices
        col_indices = {}
        for idx, header in enumerate(headers):
            if header:
                col_indices[header.strip()] = idx
        
        # Required columns (Printer Kitchen is optional, defaults to 'kitchen')
        required_cols = ['Category', 'Menu Category', 'Nama Product', 'PLU Product', 'Price Product', 'Image Product']
        missing_cols = [col for col in required_cols if col not in col_indices]
        if missing_cols:
            messages.error(request, f'Missing required columns: {", ".join(missing_cols)}')
            return redirect('management:import_excel')
        
        # Track modifiers by (product_id, group_name) to avoid duplicates
        processed_modifiers = {}
        
        # Process rows
        from apps.core.models import Modifier, ModifierOption
        
        for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            if not row or not any(row):
                continue
            
            try:
                # Extract data
                category_name = row[col_indices['Category']]
                menu_category_name = row[col_indices['Menu Category']]
                product_name = row[col_indices['Nama Product']]
                plu_code = str(row[col_indices['PLU Product']]) if row[col_indices['PLU Product']] else ''
                price = row[col_indices['Price Product']]
                image_path = row[col_indices['Image Product']]
                
                # Optional printer kitchen column
                printer_target = row[col_indices.get('Printer Kitchen', -1)] if 'Printer Kitchen' in col_indices else None
                if printer_target:
                    printer_target = str(printer_target).strip().lower()
                    if printer_target not in ['kitchen', 'bar', 'dessert', 'none']:
                        printer_target = 'kitchen'
                else:
                    printer_target = 'kitchen'
                
                # NEW: Condiment Groups (comma-separated references)
                condiment_groups_str = row[col_indices.get('Condiment Groups', -1)] if 'Condiment Groups' in col_indices else None
                
                # BACKWARD COMPATIBILITY: Old format with inline condiments
                condiment_group = row[col_indices.get('Condiment Group', -1)] if 'Condiment Group' in col_indices else None
                condiment_name = row[col_indices.get('Condiment', -1)] if 'Condiment' in col_indices else None
                condiment_plu = row[col_indices.get('PLU Condiment', -1)] if 'PLU Condiment' in col_indices else None
                condiment_fee = row[col_indices.get('Fee Condiment', -1)] if 'Fee Condiment' in col_indices else 0
                
                if not condiment_group and condiment_name:
                    condiment_group = condiment_name.strip()
                
                if not product_name or not price:
                    continue
                
                # Create/Get Category
                category, created = Category.objects.get_or_create(
                    name=category_name,
                    outlet=outlet,
                    defaults={'is_active': True, 'sort_order': 0}
                )
                if created:
                    stats['categories'] += 1
                
                # Check for existing product based on: Category + Menu Category (description) + Product Name + PLU
                existing_product = Product.objects.filter(
                    name=product_name,
                    category=category,
                    description=menu_category_name or '',
                    sku=plu_code
                ).first()
                
                if existing_product:
                    if skip_duplicates and not update_existing:
                        stats['skipped'] += 1
                        # Still create modifiers for skipped products
                        product = existing_product
                    elif update_existing:
                        # Update existing product
                        existing_product.name = product_name
                        existing_product.category = category
                        existing_product.sku = plu_code
                        existing_product.price = Decimal(str(price))
                        existing_product.description = menu_category_name or ''
                        existing_product.printer_target = printer_target
                        
                        # Handle image path
                        if image_path:
                            # Extract filename from path
                            filename = os.path.basename(image_path)
                            existing_product.image = f'products/{filename}'
                        
                        existing_product.save()
                        stats['updated'] += 1
                        product = existing_product
                    else:
                        # Allow duplicate - create new product
                        product = Product.objects.create(
                            name=product_name,
                            category=category,
                            sku=plu_code,
                            price=Decimal(str(price)),
                            description=menu_category_name or '',
                            stock_quantity=100,
                            is_active=True,
                            printer_target=printer_target
                        )
                        
                        # Handle image path
                        if image_path:
                            filename = os.path.basename(image_path)
                            product.image = f'products/{filename}'
                            product.save()
                        
                        stats['products'] += 1
                else:
                    # Create new product
                    product = Product.objects.create(
                        name=product_name,
                        category=category,
                        sku=plu_code,
                        price=Decimal(str(price)),
                        description=menu_category_name or '',
                        stock_quantity=100,
                        is_active=True,
                        printer_target=printer_target
                    )
                    
                    # Handle image path
                    if image_path:
                        # Extract filename from path
                        filename = os.path.basename(image_path)
                        product.image = f'products/{filename}'
                        product.save()
                    
                    stats['products'] += 1
                
                # NEW: Link product to existing condiment groups (comma-separated)
                if condiment_groups_str and str(condiment_groups_str).strip():
                    group_names = [g.strip() for g in str(condiment_groups_str).split(',') if g.strip()]
                    for group_name in group_names:
                        try:
                            # Find existing modifier by name
                            modifier = Modifier.objects.get(name=group_name, outlet=outlet)
                            # Link product to modifier
                            if not modifier.products.filter(id=product.id).exists():
                                modifier.products.add(product)
                                stats['modifiers'] += 1
                        except Modifier.DoesNotExist:
                            # Group not found - add to errors
                            error_msg = f'Row {row_idx}: Condiment group "{group_name}" not found. Import groups first!'
                            stats['errors'].append(error_msg)
                            continue
                
                # BACKWARD COMPATIBILITY: Create modifier if condiment data exists (old format)
                if create_modifiers and condiment_name and condiment_name.strip() and condiment_group and condiment_group.strip():
                    modifier_group_name = condiment_group.strip()
                    modifier_key = modifier_group_name
                    
                    if modifier_key not in processed_modifiers:
                        modifier, mod_created = Modifier.objects.get_or_create(
                            name=modifier_group_name,
                            outlet=outlet,
                            defaults={
                                'is_required': False,
                                'max_selections': 1
                            }
                        )
                        processed_modifiers[modifier_key] = modifier
                    else:
                        modifier = processed_modifiers[modifier_key]
                    
                    # Add product to modifier (many-to-many relationship)
                    if not modifier.products.filter(id=product.id).exists():
                        modifier.products.add(product)
                    
                    # Create modifier option (Note: ModifierOption doesn't have SKU field)
                    option, opt_created = ModifierOption.objects.get_or_create(
                        modifier=modifier,
                        name=condiment_name.strip(),
                        defaults={
                            'price_adjustment': Decimal(str(condiment_fee)) if condiment_fee else Decimal('0')
                        }
                    )
                    
                    # Update price if option already exists but has different fee
                    if not opt_created and condiment_fee is not None:
                        new_fee = Decimal(str(condiment_fee))
                        if option.price_adjustment != new_fee:
                            option.price_adjustment = new_fee
                            option.save()
                    
                    if opt_created:
                        stats['modifiers'] += 1
            
            except Exception as e:
                stats['errors'].append(f'Row {row_idx}: {str(e)}')
                continue
        
        # Success message
        message_parts = []
        if stats['categories'] > 0:
            message_parts.append(f"{stats['categories']} categories created")
        if stats['products'] > 0:
            message_parts.append(f"{stats['products']} products imported")
        if stats['updated'] > 0:
            message_parts.append(f"{stats['updated']} products updated")
        if stats['modifiers'] > 0:
            message_parts.append(f"{stats['modifiers']} modifiers created")
        if stats['skipped'] > 0:
            message_parts.append(f"{stats['skipped']} products skipped")
        
        if message_parts:
            messages.success(request, 'Import completed! ' + ', '.join(message_parts))
        
        if stats['errors']:
            for error in stats['errors'][:10]:  # Show first 10 errors
                messages.warning(request, error)
            if len(stats['errors']) > 10:
                messages.warning(request, f'... and {len(stats["errors"]) - 10} more errors')
        
        # Add instruction for image files
        messages.info(request, f'📁 Remember to copy your image files to: media/products/ directory')
        
        return redirect('management:master_data')
    
    except Exception as e:
        messages.error(request, f'Error processing Excel file: {str(e)}')
        return redirect('management:import_excel')

