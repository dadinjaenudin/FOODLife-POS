from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Avg, Count, Q
from decimal import Decimal
import json

from .models import KitchenOrder, PrinterConfig, KitchenPerformance, KitchenStation


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
        bill__outlet=request.user.outlet,
        station=station,
        status__in=['new', 'preparing']
    ).select_related('bill', 'bill__table').prefetch_related('bill__items')
    
    # Get station config
    station_config = KitchenStation.objects.filter(
        outlet=request.user.outlet,
        code=station
    ).first()
    
    # Get today's performance metrics with error handling for invalid decimal
    try:
        today_performance = KitchenPerformance.objects.filter(
            outlet=request.user.outlet,
            station=station,
            date=timezone.now().date()
        ).first()
    except Exception as e:
        print(f"Error loading KitchenPerformance: {e}")
        today_performance = None
    
    print(f"DEBUG KDS: User outlet: {request.user.outlet}, Station: {station}, Orders count: {orders.count()}")
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
    """KDS orders partial - HTMX polling"""
    orders = KitchenOrder.objects.filter(
        bill__outlet=request.user.outlet,
        station=station,
        status__in=['new', 'preparing']
    ).select_related('bill', 'bill__table').prefetch_related('bill__items')
    
    return render(request, 'kitchen/partials/kds_orders.html', {
        'orders': orders,
        'station': station,
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
            f"pos_{order.bill.outlet.id}",
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
    printers = PrinterConfig.objects.filter(outlet=request.user.outlet)
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
        outlet=request.user.outlet,
        station=station,
        date__gte=week_ago
    ).order_by('date')
    
    # Current active orders
    active_orders = KitchenOrder.objects.filter(
        bill__outlet=request.user.outlet,
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
        outlet=order.bill.outlet,
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
        bill__outlet=request.user.outlet,
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
