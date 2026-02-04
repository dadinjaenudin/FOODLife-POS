from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Avg, Count, Q
from decimal import Decimal
import json

from .models import KitchenOrder, PrinterConfig, KitchenPerformance, KitchenStation, StationPrinter


def trigger_client_event(response, event_name, data=None):
    if data:
        response['HX-Trigger'] = json.dumps({event_name: data})
    else:
        response['HX-Trigger'] = event_name
    return response


@login_required
def kds_screen(request, station='kitchen'):
    """Kitchen Display System main screen"""
    # Redirect to URL with station if accessing without station
    if station == 'kitchen' and request.path == '/kitchen/kds/':
        from django.shortcuts import redirect
        return redirect('kitchen:kds_station', station='kitchen')
    
    orders = KitchenOrder.objects.filter(
        bill__brand=request.user.brand,
        station=station,
        status__in=['new', 'preparing']
    ).select_related('bill', 'bill__table').prefetch_related('bill__items')
    
    # Get station config
    station_config = KitchenStation.objects.filter(
        brand=request.user.brand,
        code=station
    ).first()
    
    # Get today's performance metrics with error handling for invalid decimal
    try:
        today_performance = KitchenPerformance.objects.filter(
            brand=request.user.brand,
            station=station,
            date=timezone.now().date()
        ).first()
    except Exception as e:
        print(f"Error loading KitchenPerformance: {e}")
        today_performance = None
    
    print(f"DEBUG KDS: User Brand: {request.user.brand}, Station: {station}, Orders count: {orders.count()}")
    if orders.exists():
        for order in orders:
            print(f"  - Order {order.id}: Bill {order.bill.bill_number}, Status {order.status}")
    
    return render(request, 'kitchen/kds.html', {
        'orders': orders,
        'station': station,
        'station_config': station_config,
        'today_performance': today_performance,
    })


@login_required
def kds_orders(request, station='kitchen'):
    """KDS orders partial - HTMX polling with status filter"""
    status_filter = request.GET.get('status', None)
    
    # Base query
    query = KitchenOrder.objects.filter(
        bill__brand=request.user.brand,
        station=station
    )
    
    # Apply status filter
    if status_filter == 'new':
        query = query.filter(status='new')
    elif status_filter == 'preparing':
        query = query.filter(status='preparing')
    elif status_filter == 'ready':
        query = query.filter(status='ready')
    else:
        # Default: show new and preparing only
        query = query.filter(status__in=['new', 'preparing'])
    
    # Order by priority and time (oldest first for better queue management)
    orders = query.select_related('bill', 'bill__table').prefetch_related('bill__items').order_by(
        '-priority',  # urgent/rush first
        'created_at'  # oldest first
    )
    
    return render(request, 'kitchen/partials/kds_orders.html', {
        'orders': orders,
        'station': station,
        'status_filter': status_filter,
    })


@login_required
@require_http_methods(["POST"])
def kds_start(request, order_id):
    """Start preparing order - HTMX"""
    order = get_object_or_404(KitchenOrder, id=order_id)
    order.status = 'preparing'
    order.started_at = timezone.now()
    order.save()
    
    order.bill.items.filter(
        product__printer_target=order.station,
        status='sent'
    ).update(status='preparing')
    
    response = render(request, 'kitchen/partials/kds_order_card.html', {'order': order})
    return trigger_client_event(response, 'orderStarted')


@login_required
@require_http_methods(["POST"])
def kds_ready(request, order_id):
    """Mark order as ready - HTMX"""
    order = get_object_or_404(KitchenOrder, id=order_id)
    order.status = 'ready'
    order.completed_at = timezone.now()
    order.save()
    
    order.bill.items.filter(
        product__printer_target=order.station,
        status='preparing'
    ).update(status='ready')
    
    # Update performance metrics
    update_kitchen_performance(order)
    
    # Send WebSocket notification
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"pos_{order.bill.Brand.id}",
            {
                'type': 'order_ready',
                'order_id': order.id,
                'table': str(order.bill.table) if order.bill.table else f'#{order.bill.queue_number}',
            }
        )
    except Exception as e:
        print(f"WebSocket error: {e}")
    
    response = HttpResponse()
    response['HX-Trigger'] = 'orderReady'
    return response


@login_required
@require_http_methods(["POST"])
def kds_bump(request, order_id):
    """Bump/serve order - HTMX"""
    order = get_object_or_404(KitchenOrder, id=order_id)
    order.status = 'served'
    order.save()
    
    order.bill.items.filter(
        product__printer_target=order.station,
        status='ready'
    ).update(status='served')
    
    response = HttpResponse()
    response['HX-Trigger'] = 'orderBumped'
    return response


@login_required
def printer_list(request):
    """Printer configuration list"""
    printers = PrinterConfig.objects.filter(brand=request.user.brand)
    return render(request, 'kitchen/printers.html', {'printers': printers})


@login_required
@require_http_methods(["POST"])
def test_printer(request, printer_id):
    """Test printer connection - HTMX"""
    printer = get_object_or_404(PrinterConfig, id=printer_id)
    
    try:
        from .services import get_printer
        p = get_printer(printer)
        if p:
            p.text("=== TEST PRINT ===\n")
            p.text(f"Printer: {printer.name}\n")
            p.text(f"Station: {printer.station}\n")
            p.text(f"Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            p.text("=================\n")
            p.cut()
            p.close()
            return HttpResponse('<div class="p-3 bg-green-100 text-green-700 rounded">Test print berhasil!</div>')
        else:
            return HttpResponse('<div class="p-3 bg-red-100 text-red-700 rounded">Printer tidak ditemukan</div>')
    except Exception as e:
        return HttpResponse(f'<div class="p-3 bg-red-100 text-red-700 rounded">Error: {e}</div>')


@login_required
@require_http_methods(["POST"])
def set_priority(request, order_id):
    """Set order priority - HTMX"""
    order = get_object_or_404(KitchenOrder, id=order_id)
    priority = request.POST.get('priority', 'normal')
    
    if priority in ['normal', 'rush', 'urgent']:
        order.priority = priority
        order.save()
        
        return render(request, 'kitchen/partials/kds_order_card.html', {'order': order})
    
    return HttpResponse(status=400)


@login_required
def performance_metrics(request, station='kitchen'):
    """Get performance metrics for station"""
    from datetime import timedelta
    
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    # Daily metrics for last 7 days
    daily_metrics = KitchenPerformance.objects.filter(
        brand=request.user.brand,
        station=station,
        date__gte=week_ago
    ).order_by('date')
    
    # Current active orders
    active_orders = KitchenOrder.objects.filter(
        bill__brand=request.user.brand,
        station=station,
        status__in=['new', 'preparing']
    )
    
    # Count overdue orders
    overdue_count = sum(1 for order in active_orders if order.is_overdue())
    
    context = {
        'station': station,
        'daily_metrics': daily_metrics,
        'active_orders': active_orders.count(),
        'overdue_count': overdue_count,
    }
    
    return render(request, 'kitchen/partials/performance_metrics.html', context)


def update_kitchen_performance(order):
    """Update kitchen performance metrics after order completion"""
    if order.status != 'ready' or not order.completed_at:
        return
    
    today = timezone.now().date()
    
    # Get or create today's performance record
    perf, created = KitchenPerformance.objects.get_or_create(
        brand=order.bill.brand,
        station=order.station,
        date=today,
        defaults={
            'total_orders': 0,
            'completed_orders': 0,
            'avg_prep_time': 0,
            'overdue_orders': 0,
        }
    )
    
    # Calculate prep time
    prep_time = order.get_elapsed_time()
    
    # Update metrics
    perf.total_orders += 1
    perf.completed_orders += 1
    
    # Update average (running average)
    if perf.completed_orders == 1:
        perf.avg_prep_time = Decimal(str(prep_time))
    else:
        total_time = (perf.avg_prep_time * (perf.completed_orders - 1)) + Decimal(str(prep_time))
        perf.avg_prep_time = total_time / perf.completed_orders
    
    # Track fastest/slowest
    if perf.fastest_time is None or prep_time < perf.fastest_time:
        perf.fastest_time = prep_time
    if perf.slowest_time is None or prep_time > perf.slowest_time:
        perf.slowest_time = prep_time
    
    # Check if overdue
    if order.is_overdue():
        perf.overdue_orders += 1
    
    perf.save()


@login_required
def check_overdue_orders(request, station='kitchen'):
    """Check for overdue orders and return notifications - HTMX polling"""
    orders = KitchenOrder.objects.filter(
        bill__brand=request.user.brand,
        station=station,
        status__in=['new', 'preparing']
    )
    
    notifications = []
    
    for order in orders:
        elapsed_minutes = order.get_elapsed_minutes()
        
        # 10 minute warning
        if elapsed_minutes >= 10 and not order.notified_10min:
            order.notified_10min = True
            order.save()
            notifications.append({
                'type': 'warning',
                'message': f"Order {order.bill.bill_number} has been waiting 10+ minutes"
            })
        
        # Overdue notification
        if order.is_overdue() and not order.notified_overdue:
            order.notified_overdue = True
            order.save()
            notifications.append({
                'type': 'overdue',
                'message': f"Order {order.bill.bill_number} is OVERDUE!"
            })
    
    if notifications:
        return JsonResponse({'notifications': notifications})
    
    return JsonResponse({'notifications': []})


# ============================================================================
# KITCHEN PRINTER MONITORING VIEWS
# ============================================================================

@login_required
def kitchen_dashboard(request):
    """Kitchen Printer System Dashboard - Overview of all metrics"""
    from .models import KitchenTicket, StationPrinter, KitchenTicketLog, PrinterHealthCheck
    from django.db.models import Count, Q, Avg
    from datetime import timedelta
    
    # Get counts
    total_tickets = KitchenTicket.objects.count()
    new_tickets = KitchenTicket.objects.filter(status='new').count()
    printing_tickets = KitchenTicket.objects.filter(status='printing').count()
    printed_tickets = KitchenTicket.objects.filter(status='printed').count()
    failed_tickets = KitchenTicket.objects.filter(status='failed').count()
    
    # Today's stats
    today = timezone.now().date()
    today_tickets = KitchenTicket.objects.filter(created_at__date=today)
    today_total = today_tickets.count()
    today_printed = today_tickets.filter(status='printed').count()
    today_failed = today_tickets.filter(status='failed').count()
    
    # Success rate
    if today_total > 0:
        success_rate = (today_printed / today_total) * 100
    else:
        success_rate = 0
    
    # Printers status
    printers = StationPrinter.objects.all().order_by('station_code', 'priority')
    printer_stats = []
    
    for printer in printers:
        # Get latest health check
        latest_health = printer.health_checks.order_by('-checked_at').first()
        
        success_rate_printer = 0
        if printer.total_prints > 0:
            success_rate_printer = ((printer.total_prints - printer.failed_prints) / printer.total_prints) * 100
        
        printer_stats.append({
            'printer': printer,
            'latest_health': latest_health,
            'success_rate': success_rate_printer
        })
    
    # Recent activity (last 10 tickets)
    recent_tickets = KitchenTicket.objects.select_related('bill').order_by('-created_at')[:10]
    
    # Tickets by station
    tickets_by_station = KitchenTicket.objects.values('printer_target').annotate(
        total=Count('id'),
        new=Count('id', filter=Q(status='new')),
        printed=Count('id', filter=Q(status='printed')),
        failed=Count('id', filter=Q(status='failed'))
    ).order_by('-total')
    
    context = {
        'total_tickets': total_tickets,
        'new_tickets': new_tickets,
        'printing_tickets': printing_tickets,
        'printed_tickets': printed_tickets,
        'failed_tickets': failed_tickets,
        'today_total': today_total,
        'today_printed': today_printed,
        'today_failed': today_failed,
        'success_rate': success_rate,
        'printer_stats': printer_stats,
        'recent_tickets': recent_tickets,
        'tickets_by_station': tickets_by_station,
    }
    
    return render(request, 'kitchen/dashboard.html', context)


@login_required
def kitchen_tickets(request):
    """Kitchen Tickets List - View and manage all tickets"""
    from .models import KitchenTicket
    
    # Filters
    status_filter = request.GET.get('status', '')
    station_filter = request.GET.get('station', '')
    
    tickets = KitchenTicket.objects.select_related('bill').prefetch_related('items__bill_item__product')
    
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    if station_filter:
        tickets = tickets.filter(printer_target=station_filter)
    
    tickets = tickets.order_by('-created_at')[:100]
    
    # Get unique stations for filter
    stations = KitchenTicket.objects.values_list('printer_target', flat=True).distinct()
    
    context = {
        'tickets': tickets,
        'stations': stations,
        'status_filter': status_filter,
        'station_filter': station_filter,
    }
    
    return render(request, 'kitchen/tickets.html', context)


@login_required
def kitchen_printers(request):
    """Printer Status - Monitor printer health and configuration"""
    from .models import StationPrinter, PrinterHealthCheck
    
    printers = StationPrinter.objects.all().order_by('station_code', 'priority')
    
    printer_data = []
    for printer in printers:
        # Get latest health check
        latest_health = printer.health_checks.order_by('-checked_at').first()
        
        # Get recent health checks (last 10)
        recent_checks = printer.health_checks.order_by('-checked_at')[:10]
        
        # Calculate uptime percentage
        if recent_checks.count() > 0:
            online_count = sum(1 for check in recent_checks if check.is_online)
            uptime = (online_count / recent_checks.count()) * 100
        else:
            uptime = 0
        
        printer_data.append({
            'printer': printer,
            'latest_health': latest_health,
            'recent_checks': recent_checks,
            'uptime': uptime,
        })
    
    context = {
        'printer_data': printer_data,
    }
    
    return render(request, 'kitchen/printers.html', context)


@login_required
def kitchen_logs(request):
    """Audit Logs - View all ticket state changes"""
    from .models import KitchenTicketLog
    
    # Filters
    action_filter = request.GET.get('action', '')
    ticket_id = request.GET.get('ticket_id', '')
    
    logs = KitchenTicketLog.objects.select_related('ticket', 'ticket__bill')
    
    if action_filter:
        logs = logs.filter(action=action_filter)
    if ticket_id:
        logs = logs.filter(ticket_id=ticket_id)
    
    logs = logs.order_by('-timestamp')[:200]
    
    # Get unique actions for filter
    actions = KitchenTicketLog.objects.values_list('action', flat=True).distinct()
    
    context = {
        'logs': logs,
        'actions': actions,
        'action_filter': action_filter,
        'ticket_id': ticket_id,
    }
    
    return render(request, 'kitchen/logs.html', context)


@login_required
def kitchen_ticket_detail(request, ticket_id):
    """Ticket Detail - View ticket details and history"""
    from .models import KitchenTicket, KitchenTicketLog
    
    ticket = get_object_or_404(
        KitchenTicket.objects.select_related('bill').prefetch_related('items__bill_item__product'),
        id=ticket_id
    )
    
    # Get logs for this ticket
    logs = KitchenTicketLog.objects.filter(ticket=ticket).order_by('-timestamp')
    
    context = {
        'ticket': ticket,
        'logs': logs,
    }
    
    return render(request, 'kitchen/ticket_detail.html', context)


# ============================================================================
# STATION PRINTER CRUD
# ============================================================================

@login_required
def printer_list_manage(request):
    """Station Printer Management - List all printers with CRUD"""
    from apps.core.models import Brand
    
    # Filter by brand if user has brand assigned
    if hasattr(request.user, 'brand') and request.user.brand:
        printers = StationPrinter.objects.filter(brand=request.user.brand)
    else:
        printers = StationPrinter.objects.all()
    
    printers = printers.select_related('brand').order_by('station_code', 'priority')
    
    # Get brands for dropdown
    brands = Brand.objects.all()
    
    context = {
        'printers': printers,
        'brands': brands,
    }
    
    return render(request, 'kitchen/printer_manage.html', context)


@login_required
def printer_create(request):
    """Create new station printer"""
    from apps.core.models import Brand
    from .models import PrinterBrand
    
    if request.method == 'POST':
        try:
            brand_id = request.POST.get('brand')
            brand = get_object_or_404(Brand, id=brand_id)
            
            printer = StationPrinter.objects.create(
                brand=brand,
                station_code=request.POST.get('station_code').lower().strip(),
                printer_name=request.POST.get('printer_name'),
                printer_ip=request.POST.get('printer_ip'),
                printer_port=int(request.POST.get('printer_port', 9100)),
                priority=int(request.POST.get('priority', 1)),
                is_active=request.POST.get('is_active') == 'on',
                paper_width_mm=int(request.POST.get('paper_width_mm', 80)),
                chars_per_line=int(request.POST.get('chars_per_line', 32)),
                printer_brand=request.POST.get('printer_brand', 'HRPT'),
                printer_type=request.POST.get('printer_type', 'network'),
                timeout_seconds=int(request.POST.get('timeout_seconds', 5)),
            )
            
            messages.success(request, f'✓ Printer "{printer.printer_name}" berhasil ditambahkan!')
            return redirect('kitchen:printer_manage')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('kitchen:printer_manage')
    
    # GET request - show form
    brands = Brand.objects.all()
    printer_brands = PrinterBrand.objects.filter(is_active=True).order_by('name')
    
    context = {
        'brands': brands,
        'printer_brands': printer_brands,
    }
    return render(request, 'kitchen/printer_form.html', context)


@login_required
def printer_edit(request, printer_id):
    """Edit station printer"""
    from apps.core.models import Brand
    from .models import PrinterBrand
    
    printer = get_object_or_404(StationPrinter, id=printer_id)
    
    if request.method == 'POST':
        try:
            brand_id = request.POST.get('brand')
            printer.brand = get_object_or_404(Brand, id=brand_id)
            printer.station_code = request.POST.get('station_code').lower().strip()
            printer.printer_name = request.POST.get('printer_name')
            printer.printer_ip = request.POST.get('printer_ip')
            printer.printer_port = int(request.POST.get('printer_port', 9100))
            printer.priority = int(request.POST.get('priority', 1))
            printer.is_active = request.POST.get('is_active') == 'on'
            printer.paper_width_mm = int(request.POST.get('paper_width_mm', 80))
            printer.chars_per_line = int(request.POST.get('chars_per_line', 32))
            printer.printer_brand = request.POST.get('printer_brand', 'HRPT')
            printer.printer_type = request.POST.get('printer_type', 'network')
            printer.timeout_seconds = int(request.POST.get('timeout_seconds', 5))
            printer.save()
            
            messages.success(request, f'✓ Printer "{printer.printer_name}" berhasil diupdate!')
            return redirect('kitchen:printer_manage')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    # GET request - show form
    brands = Brand.objects.all()
    printer_brands = PrinterBrand.objects.filter(is_active=True).order_by('name')
    
    context = {
        'printer': printer,
        'brands': brands,
        'printer_brands': printer_brands,
    }
    return render(request, 'kitchen/printer_form.html', context)


@login_required
def printer_delete(request, printer_id):
    """Delete station printer"""
    printer = get_object_or_404(StationPrinter, id=printer_id)
    
    if request.method == 'POST':
        printer_name = printer.printer_name
        printer.delete()
        messages.success(request, f'✓ Printer "{printer_name}" berhasil dihapus!')
        return redirect('kitchen:printer_manage')
    
    context = {
        'printer': printer,
    }
    return render(request, 'kitchen/printer_delete_confirm.html', context)


@login_required
def printer_toggle_active(request, printer_id):
    """Toggle printer active status (AJAX)"""
    printer = get_object_or_404(StationPrinter, id=printer_id)
    printer.is_active = not printer.is_active
    printer.save()
    
    return JsonResponse({
        'success': True,
        'is_active': printer.is_active,
        'message': f'Printer {"activated" if printer.is_active else "deactivated"}'
    })


@require_http_methods(["POST"])
def printer_test_print(request, printer_id):
    """Test printer connection and send test print using python-escpos"""
    from datetime import datetime
    from .printer_helper import NetworkPrinterHelper
    
    printer = get_object_or_404(StationPrinter, id=printer_id)
    
    try:
        # Initialize network printer helper
        helper = NetworkPrinterHelper(
            ip=str(printer.printer_ip),
            port=printer.printer_port,
            timeout=5
        )
        
        # Send test print
        success = helper.print_test()
        
        if success:
            # Update printer stats
            printer.last_print_at = datetime.now()
            printer.total_prints += 1
            printer.save()
            
            return JsonResponse({
                'success': True,
                'message': f'✓ Test print sent successfully to {printer.printer_name}'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f'Failed to print to {printer.printer_name}'
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        })


@require_http_methods(["POST"])
def printer_setup_defaults(request):
    """Setup default station printers (kitchen, bar, dessert)"""
    from apps.core.models import Brand
    
    try:
        # Get first available brand
        brand = Brand.objects.first()
        if not brand:
            return JsonResponse({
                'success': False,
                'message': 'No Brand found. Please create a Brand first in the system.'
            })
        
        printers_data = [
            {
                'brand': brand,
                'station_code': 'kitchen',
                'printer_name': 'Main Kitchen Printer',
                'printer_ip': '192.168.1.100',
                'printer_port': 9100,
                'priority': 1,
                'is_active': True,
                'paper_width_mm': 80,
                'chars_per_line': 32,
                'printer_brand': 'HRPT',
                'printer_type': 'network',
                'timeout_seconds': 5,
            },
            {
                'brand': brand,
                'station_code': 'bar',
                'printer_name': 'Bar Station Printer',
                'printer_ip': '192.168.1.101',
                'printer_port': 9100,
                'priority': 1,
                'is_active': True,
                'paper_width_mm': 80,
                'chars_per_line': 32,
                'printer_brand': 'HRPT',
                'printer_type': 'network',
                'timeout_seconds': 5,
            },
            {
                'brand': brand,
                'station_code': 'dessert',
                'printer_name': 'Dessert Station Printer',
                'printer_ip': '192.168.1.102',
                'printer_port': 9100,
                'priority': 1,
                'is_active': True,
                'paper_width_mm': 80,
                'chars_per_line': 32,
                'printer_brand': 'HRPT',
                'printer_type': 'network',
                'timeout_seconds': 5,
            },
        ]
        
        created_count = 0
        existing_count = 0
        
        for printer_data in printers_data:
            printer, created = StationPrinter.objects.get_or_create(
                brand=printer_data['brand'],
                station_code=printer_data['station_code'],
                defaults=printer_data
            )
            if created:
                created_count += 1
            else:
                existing_count += 1
        
        if created_count > 0:
            message = f'✓ Successfully created {created_count} default printer(s)'
            if existing_count > 0:
                message += f' ({existing_count} already existed)'
        else:
            message = 'All default printers already exist'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'created': created_count,
            'existing': existing_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        })


# ============================================================================
# PRINTER BRANDS CRUD
# ============================================================================

@login_required
def brand_list(request):
    """List all printer brands"""
    from .models import PrinterBrand
    
    brands = PrinterBrand.objects.all().order_by('name')
    
    # Count printers using each brand
    for brand in brands:
        brand.printer_count = StationPrinter.objects.filter(printer_brand=brand.code).count()
    
    context = {
        'brands': brands,
    }
    
    return render(request, 'kitchen/brand_list.html', context)


@login_required
def brand_create(request):
    """Create new printer brand"""
    from .models import PrinterBrand
    
    if request.method == 'POST':
        try:
            brand = PrinterBrand.objects.create(
                code=request.POST.get('code').upper().strip(),
                name=request.POST.get('name').strip(),
                profile_class=request.POST.get('profile_class').strip(),
                description=request.POST.get('description', '').strip(),
                is_active=request.POST.get('is_active') == 'on',
            )
            
            messages.success(request, f'✓ Printer brand "{brand.name}" berhasil ditambahkan!')
            return redirect('kitchen:brand_list')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('kitchen:brand_list')
    
    # GET request - show form
    context = {}
    return render(request, 'kitchen/brand_form.html', context)


@login_required
def brand_edit(request, brand_id):
    """Edit printer brand"""
    from .models import PrinterBrand
    
    brand = get_object_or_404(PrinterBrand, id=brand_id)
    
    if request.method == 'POST':
        try:
            brand.code = request.POST.get('code').upper().strip()
            brand.name = request.POST.get('name').strip()
            brand.profile_class = request.POST.get('profile_class').strip()
            brand.description = request.POST.get('description', '').strip()
            brand.is_active = request.POST.get('is_active') == 'on'
            brand.save()
            
            messages.success(request, f'✓ Printer brand "{brand.name}" berhasil diupdate!')
            return redirect('kitchen:brand_list')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    # GET request - show form
    context = {
        'brand': brand,
    }
    return render(request, 'kitchen/brand_form.html', context)


@login_required
def brand_delete(request, brand_id):
    """Delete printer brand"""
    from .models import PrinterBrand
    
    brand = get_object_or_404(PrinterBrand, id=brand_id)
    
    # Check if brand is in use
    printer_count = StationPrinter.objects.filter(printer_brand=brand.code).count()
    
    if request.method == 'POST':
        if printer_count > 0:
            messages.error(request, f'Cannot delete "{brand.name}" - {printer_count} printer(s) are using this brand!')
            return redirect('kitchen:brand_list')
        
        brand_name = brand.name
        brand.delete()
        messages.success(request, f'✓ Printer brand "{brand_name}" berhasil dihapus!')
        return redirect('kitchen:brand_list')
    
    context = {
        'brand': brand,
        'printer_count': printer_count,
    }
    return render(request, 'kitchen/brand_delete_confirm.html', context)


@login_required
def brand_toggle_active(request, brand_id):
    """Toggle brand active status (AJAX)"""
    from .models import PrinterBrand
    
    brand = get_object_or_404(PrinterBrand, id=brand_id)
    brand.is_active = not brand.is_active
    brand.save()
    
    return JsonResponse({
        'success': True,
        'is_active': brand.is_active,
        'message': f'Brand {"activated" if brand.is_active else "deactivated"}'
    })
