from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
import json

from .models import Table, TableArea, TableGroup
from apps.pos.models import Bill, BillItem


def trigger_client_event(response, event_name, data=None):
    if data:
        response['HX-Trigger'] = json.dumps({event_name: data})
    else:
        response['HX-Trigger'] = event_name
    return response


@login_required
def table_map(request):
    """Table floor plan"""
    areas = TableArea.objects.filter(outlet=request.user.outlet).prefetch_related('tables')
    return render(request, 'tables/floor_plan.html', {'areas': areas})


@login_required
def table_status(request):
    """Table status grid - HTMX partial"""
    tables = Table.objects.filter(
        area__outlet=request.user.outlet
    ).select_related('area')
    
    return render(request, 'tables/partials/table_grid.html', {'tables': tables})


@login_required
def table_grid(request):
    """Table grid partial - HTMX"""
    tables = Table.objects.filter(
        area__outlet=request.user.outlet
    ).select_related('area')
    
    return render(request, 'tables/partials/table_grid.html', {'tables': tables})


@login_required
@require_http_methods(["POST"])
def open_table(request, table_id):
    """Open table and create bill OR resume existing bill - Redirect to POS"""
    table = get_object_or_404(Table, id=table_id)
    
    # Check if table already has an active bill
    existing_bill = table.get_active_bill()
    
    if existing_bill:
        # Resume existing bill
        request.session['active_bill_id'] = existing_bill.id
    else:
        # Create new bill
        guest_count = int(request.POST.get('guest_count', 1))
        
        with transaction.atomic():
            bill = Bill.objects.create(
                outlet=request.user.outlet,
                table=table,
                bill_type='dine_in',
                guest_count=guest_count,
                created_by=request.user,
            )
            
            table.status = 'occupied'
            table.save()
            
            request.session['active_bill_id'] = bill.id
    
    # Redirect to POS after table selection
    from django.shortcuts import redirect
    return redirect('pos:main')


@login_required
@require_http_methods(["POST"])
def close_table(request, table_id):
    """Close table / mark as available - HTMX"""
    table = get_object_or_404(Table, id=table_id)
    table.status = 'available'
    table.save()
    
    response = render(request, 'tables/partials/table_grid.html', {
        'tables': Table.objects.filter(area__outlet=request.user.outlet)
    })
    return trigger_client_event(response, 'tableClosed')


@login_required
@require_http_methods(["POST"])
def move_table(request, bill_id):
    """Move bill to another table - HTMX"""
    bill = get_object_or_404(Bill, id=bill_id, status__in=['open', 'hold'])
    new_table_id = request.POST.get('table_id')
    new_table = get_object_or_404(Table, id=new_table_id)
    
    if bill.table:
        bill.table.status = 'available'
        bill.table.save()
    
    bill.table = new_table
    bill.save()
    
    new_table.status = 'occupied'
    new_table.save()
    
    from apps.pos.models import BillLog
    BillLog.objects.create(
        bill=bill,
        action='move_table',
        user=request.user,
        details={'to_table': new_table.number}
    )
    
    response = render(request, 'tables/partials/table_grid.html', {
        'tables': Table.objects.filter(area__outlet=request.user.outlet)
    })
    return trigger_client_event(response, 'tableMoved')


@login_required
@require_http_methods(["POST"])
def join_tables(request):
    """Join multiple tables into one group"""
    table_ids = request.POST.getlist('table_ids')
    main_table_id = request.POST.get('main_table_id')
    
    if len(table_ids) < 2:
        return HttpResponse('<div class="p-3 bg-yellow-100 text-yellow-700 rounded">Pilih minimal 2 meja</div>')
    
    main_table = get_object_or_404(Table, id=main_table_id)
    
    with transaction.atomic():
        group = TableGroup.objects.create(
            main_table=main_table,
            outlet=request.user.outlet,
            created_by=request.user,
        )
        
        Table.objects.filter(id__in=table_ids).update(
            table_group=group,
            status='occupied'
        )
        
        for table_id in table_ids:
            if str(table_id) != str(main_table_id):
                table = Table.objects.get(id=table_id)
                bill = table.get_active_bill()
                if bill:
                    bill.table = main_table
                    bill.save()
    
    response = render(request, 'tables/partials/table_grid.html', {
        'tables': Table.objects.filter(area__outlet=request.user.outlet)
    })
    return trigger_client_event(response, 'tablesJoined')


@login_required
@require_http_methods(["POST"])
def split_table(request, group_id):
    """Split joined tables back to individual tables"""
    group = get_object_or_404(TableGroup, id=group_id)
    
    main_bill = group.main_table.get_active_bill()
    if main_bill and main_bill.items.filter(is_void=False).exists():
        return HttpResponse(
            '<div class="p-3 bg-yellow-100 text-yellow-700 rounded">Selesaikan bill terlebih dahulu sebelum split meja</div>'
        )
    
    Table.objects.filter(table_group=group).update(
        table_group=None,
        status='available'
    )
    
    group.delete()
    
    response = render(request, 'tables/partials/table_grid.html', {
        'tables': Table.objects.filter(area__outlet=request.user.outlet)
    })
    return trigger_client_event(response, 'tablesSplit')


@login_required
@require_http_methods(["POST"])
def merge_tables(request):
    """Merge multiple table bills - HTMX"""
    table_ids = request.POST.getlist('table_ids')
    
    if len(table_ids) < 2:
        return HttpResponse('<div class="p-3 bg-yellow-100 text-yellow-700 rounded">Pilih minimal 2 meja</div>')
    
    bills = Bill.objects.filter(
        table_id__in=table_ids,
        status__in=['open', 'hold']
    )
    
    if bills.count() < 2:
        return HttpResponse('<div class="p-3 bg-yellow-100 text-yellow-700 rounded">Tidak ada bill untuk digabung</div>')
    
    main_bill = bills.first()
    other_bills = bills.exclude(id=main_bill.id)
    
    with transaction.atomic():
        for bill in other_bills:
            bill.items.update(bill=main_bill)
            bill.status = 'cancelled'
            bill.notes = f"Merged into {main_bill.bill_number}"
            bill.save()
            if bill.table:
                bill.table.status = 'available'
                bill.table.save()
        
        main_bill.calculate_totals()
        
        from apps.pos.models import BillLog
        BillLog.objects.create(
            bill=main_bill,
            action='merge_bill',
            user=request.user,
        )
    
    return render(request, 'pos/partials/bill_panel.html', {'bill': main_bill})


@login_required
def table_qr_codes(request):
    """Generate/view QR codes for all tables"""
    tables = Table.objects.filter(area__outlet=request.user.outlet)
    
    for table in tables:
        if not table.qr_code:
            table.generate_qr_code()
    
    return render(request, 'tables/qr_codes.html', {'tables': tables})


@login_required
@require_http_methods(["POST"])
def generate_qr(request, table_id):
    """Generate QR code for single table - HTMX"""
    table = get_object_or_404(Table, id=table_id)
    table.generate_qr_code()
    
    return HttpResponse(f'<img src="{table.qr_code.url}" class="w-32 h-32" alt="QR {table.number}">')


@login_required
@require_http_methods(["POST"])
def save_table_order(request):
    """Save table display order after drag & drop - AJAX"""
    try:
        data = json.loads(request.body)
        table_orders = data.get('table_orders', [])
        
        with transaction.atomic():
            for item in table_orders:
                table_id = item.get('table_id')
                sort_order = item.get('sort_order')
                
                Table.objects.filter(id=table_id).update(sort_order=sort_order)
        
        return JsonResponse({'success': True, 'message': 'Urutan table berhasil disimpan'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
