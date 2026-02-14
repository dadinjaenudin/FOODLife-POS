from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Prefetch
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
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
@ensure_csrf_cookie
def table_map(request):
    """Table floor plan"""
    from django.db.models import Count, Q

    areas = TableArea.objects.filter(
        brand=request.user.brand,
        is_active=True
    ).order_by('sort_order', 'name').prefetch_related(
        Prefetch('tables', queryset=Table.objects.filter(is_active=True).order_by('number'), to_attr='active_tables')
    )

    # Remove any potential duplicates at Python level
    seen_ids = set()
    unique_areas = []
    for area in areas:
        if area.id not in seen_ids:
            seen_ids.add(area.id)
            tables = getattr(area, 'active_tables', [])
            area.table_count = len(tables)
            unique_areas.append(area)

    # Set default bill display values on ALL tables first (ensures valid JSON in template)
    for area in unique_areas:
        for table in getattr(area, 'active_tables', []):
            table.bill_number_display = ''
            table.bill_total_display = 0
            table.bill_created_at_iso = ''
            table.bill_guest_count = 0
            table.bill_items_count = 0
            table.bill_status_display = ''
            table.rsv_code = ''
            table.rsv_guest = ''
            table.rsv_time = ''
            table.rsv_pax = 0
            table.rsv_status = ''
            table.rsv_id = ''

    # Enrich tables with today's reservation data
    try:
        from django.utils import timezone as tz
        from .models_booking import Reservation
        today = tz.localdate()
        today_reservations = Reservation.objects.filter(
            brand=request.user.brand,
            reservation_date=today,
            status__in=['confirmed', 'deposit_pending', 'checked_in'],
        ).prefetch_related('tables')

        table_reservation_map = {}
        for rsv in today_reservations:
            for t in rsv.tables.all():
                table_reservation_map[str(t.id)] = {
                    'code': rsv.reservation_code,
                    'guest': rsv.guest_name,
                    'time': rsv.time_start.strftime('%H:%M') if rsv.time_start else '',
                    'pax': rsv.party_size,
                    'status': rsv.status,
                    'id': str(rsv.id),
                }

        for area in unique_areas:
            for table in getattr(area, 'active_tables', []):
                rsv_info = table_reservation_map.get(str(table.id))
                if rsv_info:
                    table.rsv_code = rsv_info['code']
                    table.rsv_guest = rsv_info['guest']
                    table.rsv_time = rsv_info['time']
                    table.rsv_pax = rsv_info['pax']
                    table.rsv_status = rsv_info['status']
                    table.rsv_id = rsv_info['id']
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f'Error enriching floor plan reservation data: {e}')

    # Enrich tables that have active bills
    try:
        all_table_ids = [t.id for area in unique_areas for t in getattr(area, 'active_tables', [])]
        if all_table_ids:
            active_bills = Bill.objects.filter(
                table_id__in=all_table_ids,
                status__in=['open', 'hold']
            ).annotate(
                active_items_count=Count('items', filter=Q(items__is_void=False))
            ).select_related('table')

            for bill in active_bills:
                # Find and enrich the matching table object
                for area in unique_areas:
                    for table in getattr(area, 'active_tables', []):
                        if str(table.id) == str(bill.table_id):
                            table.bill_number_display = bill.bill_number or ''
                            table.bill_total_display = float(bill.total or 0)
                            table.bill_created_at_iso = bill.created_at.isoformat() if bill.created_at else ''
                            table.bill_guest_count = bill.guest_count or 0
                            table.bill_items_count = bill.active_items_count
                            table.bill_status_display = bill.status or ''
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f'Error enriching floor plan bill data: {e}')

    return render(request, 'tables/floor_plan.html', {'areas': unique_areas})


@login_required
@require_http_methods(["POST"])
def update_table_position(request):
    """Update table position (pos_x, pos_y) - AJAX"""
    try:
        data = json.loads(request.body)
        table_id = data.get('table_id')
        pos_x = data.get('pos_x')
        pos_y = data.get('pos_y')

        if not table_id:
            return JsonResponse({'success': False, 'error': 'table_id is required'}, status=400)

        table = get_object_or_404(Table, id=table_id, area__brand=request.user.brand)

        table.pos_x = max(0, int(pos_x)) if pos_x is not None else 0
        table.pos_y = max(0, int(pos_y)) if pos_y is not None else 0
        table.save(update_fields=['pos_x', 'pos_y'])

        return JsonResponse({'success': True})
    except (ValueError, TypeError) as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=400)
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=500)


@login_required
def table_status(request):
    """Table status grid - HTMX partial"""
    tables = Table.objects.filter(
        area__brand=request.user.brand
    ).select_related('area')
    
    return render(request, 'tables/partials/table_grid.html', {'tables': tables})


@login_required
def table_grid(request):
    """Table grid partial - HTMX"""
    tables = Table.objects.filter(
        area__brand=request.user.brand
    ).select_related('area')
    
    return render(request, 'tables/partials/table_grid.html', {'tables': tables})


@login_required
@require_http_methods(["POST"])
def open_table(request, table_id):
    """Open table and create bill OR resume existing bill - Redirect to POS"""
    import logging
    from django.shortcuts import redirect
    from django.contrib import messages
    logger = logging.getLogger(__name__)
    
    table = get_object_or_404(Table, id=table_id)
    logger.info(f"Open table {table.number} (ID: {table.id}, Status: {table.status})")
    
    # Check if there's already an active bill in session
    active_bill_id = request.session.get('active_bill_id')
    if active_bill_id:
        try:
            active_bill = Bill.objects.get(id=active_bill_id, status__in=['open', 'hold'])
            # If user clicks a different table while having active bill, warn them
            if active_bill.table and active_bill.table.id != table.id:
                messages.warning(
                    request, 
                    f'You already have an active bill for {active_bill.table.number} ({active_bill.bill_number}). '
                    f'Complete or hold that bill first before opening {table.number}.'
                )
                logger.warning(f"User tried to open {table.number} while having active bill for {active_bill.table.number}")
                # Keep the existing active bill
                return redirect('pos:main')
        except Bill.DoesNotExist:
            # Active bill from session no longer exists, clear it
            request.session.pop('active_bill_id', None)
            logger.info("Active bill from session no longer exists, cleared")
    
    # Check if table already has an active bill
    existing_bill = table.get_active_bill()
    logger.info(f"Existing bill: {existing_bill}")
    
    if existing_bill:
        # Resume existing bill
        request.session['active_bill_id'] = existing_bill.id
        request.session.modified = True
        logger.info(f"Resumed existing bill {existing_bill.id}, session set")
    else:
        # Check if table is marked occupied but has no active bill (orphaned state)
        if table.status == 'occupied':
            # Reset to available since there's no active bill
            table.status = 'available'
            table.save()
            logger.warning(f"Table {table.number} was occupied but no active bill, reset to available")
        
        # Create new bill
        guest_count = int(request.POST.get('guest_count', 1))
        
        with transaction.atomic():
            bill = Bill.objects.create(
                brand=request.user.brand,
                table=table,
                bill_type='dine_in',
                guest_count=guest_count,
                created_by=request.user,
            )
            
            table.status = 'occupied'
            table.save()
            
            request.session['active_bill_id'] = bill.id
            request.session.modified = True
            logger.info(f"Created new bill {bill.id} for table {table.number}, session set")
    
    logger.info(f"Session active_bill_id: {request.session.get('active_bill_id')}")
    
    # Redirect to POS after table selection
    return redirect('pos:main')


@login_required
@require_http_methods(["POST"])
def clean_table(request, table_id):
    """Clean table / mark as available - HTMX"""
    table = get_object_or_404(Table, id=table_id)
    table.status = 'available'
    table.save()
    
    # Render full floor plan with all context
    areas = TableArea.objects.filter(brand=request.user.brand, is_active=True).distinct().prefetch_related('tables')
    response = render(request, 'tables/floor_plan.html', {'areas': areas})
    return trigger_client_event(response, 'tableCleaned')


@login_required
@require_http_methods(["POST"])
def close_table(request, table_id):
    """Close table / mark as available - HTMX"""
    table = get_object_or_404(Table, id=table_id)
    table.status = 'available'
    table.save()
    
    response = render(request, 'tables/partials/table_grid.html', {
        'tables': Table.objects.filter(area__brand=request.user.brand)
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
        'tables': Table.objects.filter(area__brand=request.user.brand)
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
            brand=request.user.brand,
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
        'tables': Table.objects.filter(area__brand=request.user.brand)
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
        'tables': Table.objects.filter(area__brand=request.user.brand)
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
    tables = Table.objects.filter(area__brand=request.user.brand)
    
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


@login_required
@require_http_methods(["POST"])
def join_tables(request):
    """Join multiple tables - merge bills and link tables"""
    try:
        data = json.loads(request.body)
        table_ids = data.get('table_ids', [])
        
        if len(table_ids) < 2:
            return JsonResponse({'success': False, 'error': 'Select at least 2 tables'}, status=400)
        
        with transaction.atomic():
            # Get all tables
            tables = Table.objects.filter(
                id__in=table_ids,
                status='occupied'
            ).select_related('area')
            
            if tables.count() != len(table_ids):
                return JsonResponse({'success': False, 'error': 'Some tables are not available'}, status=400)
            
            # Get all bills for these tables
            bills = Bill.objects.filter(
                table__in=tables,
                status='open'
            )
            
            if not bills.exists():
                return JsonResponse({
                    'success': False, 
                    'error': 'Please open at least one table and add items before joining tables'
                }, status=400)
            
            # Use first table with a bill as primary
            primary_bill = bills.first()
            primary_table = primary_bill.table
            
            # Create or update table group
            table_group, created = TableGroup.objects.get_or_create(
                main_table=primary_table,
                defaults={
                    'created_by': request.user,
                    'brand': request.user.brand
                }
            )
            
            # Link all tables to this group
            tables.update(table_group=table_group)
            
            # Merge all other bills into primary bill
            other_bills = bills.exclude(id=primary_bill.id)
            
            for bill in other_bills:
                # Move all items to primary bill
                items = bill.items.filter(is_void=False)
                items.update(bill=primary_bill)
                
                # Mark old bill as merged
                bill.status = 'merged'
                bill.notes = f"Merged into bill {primary_bill.bill_number}"
                bill.save()
            
            # Recalculate primary bill totals
            primary_bill.calculate_totals()
            
            # Update all tables status to occupied
            tables.update(status='occupied')
            
            return JsonResponse({
                'success': True,
                'message': f'{tables.count()} tables joined successfully',
                'primary_bill_id': primary_bill.id,
                'primary_table_id': primary_table.id,
                'redirect_url': f'/pos/?bill_id={primary_bill.id}'
            })
    
    except Exception as e:
        import logging
        logging.error(f"Error joining tables: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

