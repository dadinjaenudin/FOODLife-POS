from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import json

from .models import KitchenOrder, PrinterConfig


def trigger_client_event(response, event_name, data=None):
    if data:
        response['HX-Trigger'] = json.dumps({event_name: data})
    else:
        response['HX-Trigger'] = event_name
    return response


@login_required
def kds_screen(request, station='kitchen'):
    """Kitchen Display System main screen"""
    orders = KitchenOrder.objects.filter(
        bill__outlet=request.user.outlet,
        station=station,
        status__in=['new', 'preparing']
    ).select_related('bill', 'bill__table').prefetch_related('bill__items')
    
    return render(request, 'kitchen/kds.html', {
        'orders': orders,
        'station': station,
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
