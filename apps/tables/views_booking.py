from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from django.db.models import Prefetch
from django.utils import timezone
from decimal import Decimal
import json
import datetime

from .models import Table, TableArea
from .models_booking import (
    Reservation, ReservationConfig, ReservationDeposit,
    ReservationPackage, ReservationLog,
)
from apps.pos.models import Bill, BillLog


def _get_config(request):
    """Get or create ReservationConfig for current store"""
    from apps.core.models import Store
    store = Store.get_current()
    config, _ = ReservationConfig.objects.get_or_create(store=store)
    return config


def _log(reservation, action, user, details=None):
    """Create audit log entry"""
    ReservationLog.objects.create(
        reservation=reservation,
        action=action,
        created_by=user,
        details=details or {},
    )


# =============================================================================
# BOOKING DASHBOARD
# =============================================================================

@login_required
def booking_dashboard(request):
    """Dashboard booking hari ini — HTMX modal atau full page"""
    config = _get_config(request)

    # Date filter
    date_str = request.GET.get('date')
    if date_str:
        try:
            view_date = datetime.date.fromisoformat(date_str)
        except ValueError:
            view_date = timezone.localdate()
    else:
        view_date = timezone.localdate()

    reservations = Reservation.objects.filter(
        brand=request.user.brand,
        reservation_date=view_date,
    ).exclude(status='cancelled').prefetch_related('tables').order_by('time_start')

    # Stats
    total_pax = sum(r.party_size for r in reservations)
    deposit_count = sum(1 for r in reservations if r.deposit_paid > 0)

    context = {
        'reservations': reservations,
        'view_date': view_date,
        'today': timezone.localdate(),
        'total_pax': total_pax,
        'deposit_count': deposit_count,
        'config': config,
    }
    return render(request, 'tables/booking/dashboard.html', context)


# =============================================================================
# BOOKING CRUD
# =============================================================================

@login_required
def booking_create(request):
    """Form buat booking baru — GET=form, POST=create"""
    config = _get_config(request)

    if request.method == 'POST':
        return _process_booking_create(request, config)

    # GET: render form
    areas = TableArea.objects.filter(
        brand=request.user.brand, is_active=True
    ).order_by('sort_order', 'name').prefetch_related(
        Prefetch('tables', queryset=Table.objects.filter(is_active=True).order_by('number'), to_attr='active_tables')
    )

    packages = ReservationPackage.objects.filter(
        brand=request.user.brand, is_active=True
    )

    context = {
        'config': config,
        'areas': areas,
        'packages': packages,
        'today': timezone.localdate().isoformat(),
        'max_date': (timezone.localdate() + datetime.timedelta(days=config.max_advance_days)).isoformat(),
    }
    return render(request, 'tables/booking/create_form.html', context)


def _booking_error(msg):
    """Return 422 error that displays inline inside the booking form"""
    return HttpResponse(
        f'<div class="p-3 bg-red-100 text-red-700 rounded text-sm">{msg}</div>',
        status=422,
        headers={
            'HX-Retarget': '#booking-form-errors',
            'HX-Reswap': 'innerHTML',
        }
    )


def _process_booking_create(request, config):
    """Process booking creation form"""
    import logging
    logger = logging.getLogger('tables.booking')

    from apps.core.models import Store
    store = Store.get_current()

    booking_type = request.POST.get('type', 'standard')
    date_str = request.POST.get('reservation_date', '').strip()
    time_start_str = request.POST.get('time_start', '').strip()

    try:
        duration = int(request.POST.get('duration_minutes') or config.default_slot_duration)
    except (ValueError, TypeError):
        duration = config.default_slot_duration

    try:
        party_size = int(request.POST.get('party_size') or 2)
    except (ValueError, TypeError):
        party_size = 2

    guest_name = request.POST.get('guest_name', '').strip()
    guest_phone = request.POST.get('guest_phone', '').strip()
    guest_email = request.POST.get('guest_email', '').strip()
    table_ids = request.POST.getlist('tables')
    area_id = request.POST.get('table_area') or None

    try:
        minimum_spend = Decimal(request.POST.get('minimum_spend', '0') or '0')
    except Exception:
        minimum_spend = Decimal('0')

    deposit_required = request.POST.get('deposit_required') == 'on'

    try:
        deposit_amount = Decimal(request.POST.get('deposit_amount', '0') or '0')
    except Exception:
        deposit_amount = Decimal('0')

    package_id = request.POST.get('package') or None
    special_requests = request.POST.get('special_requests', '').strip()

    # Validation
    if not guest_name:
        logger.warning('BOOKING_CREATE_FAIL: guest_name empty. POST=%s', dict(request.POST))
        return _booking_error('Nama tamu wajib diisi')
    if not date_str or not time_start_str:
        logger.warning('BOOKING_CREATE_FAIL: date=%r time=%r empty. POST=%s', date_str, time_start_str, dict(request.POST))
        return _booking_error('Tanggal dan jam wajib diisi')

    reservation_date = datetime.date.fromisoformat(date_str)
    time_start = datetime.time.fromisoformat(time_start_str)
    time_end_dt = datetime.datetime.combine(reservation_date, time_start) + datetime.timedelta(minutes=duration)
    time_end = time_end_dt.time()

    # Check table availability (overlap check)
    if table_ids:
        buffer = config.overbooking_buffer
        for tid in table_ids:
            overlap = Reservation.objects.filter(
                tables__id=tid,
                reservation_date=reservation_date,
                status__in=['pending', 'deposit_pending', 'confirmed', 'checked_in'],
            ).exclude(
                time_end__lte=(datetime.datetime.combine(reservation_date, time_start) - datetime.timedelta(minutes=buffer)).time()
            ).exclude(
                time_start__gte=(time_end_dt + datetime.timedelta(minutes=buffer)).time()
            )
            if overlap.exists():
                table = Table.objects.get(id=tid)
                return _booking_error(f'Meja {table.number} sudah di-booking pada waktu tersebut')

    # Determine initial status
    if deposit_required and deposit_amount > 0:
        initial_status = 'deposit_pending'
        deposit_status = 'pending'
    else:
        initial_status = 'confirmed'
        deposit_status = 'none'

    with transaction.atomic():
        reservation = Reservation.objects.create(
            company=request.user.company if hasattr(request.user, 'company') else None,
            brand=request.user.brand,
            store=store,
            type=booking_type,
            status=initial_status,
            reservation_date=reservation_date,
            time_start=time_start,
            time_end=time_end,
            duration_minutes=duration,
            guest_name=guest_name,
            guest_phone=guest_phone,
            guest_email=guest_email,
            party_size=party_size,
            table_area_id=area_id,
            minimum_spend=minimum_spend,
            deposit_required=deposit_required,
            deposit_amount=deposit_amount,
            deposit_status=deposit_status,
            package_id=package_id,
            special_requests=special_requests,
            created_by=request.user,
            confirmed_by=request.user if initial_status == 'confirmed' else None,
        )

        if table_ids:
            reservation.tables.set(table_ids)

        _log(reservation, 'created', request.user, {
            'type': booking_type,
            'date': date_str,
            'time': time_start_str,
            'party_size': party_size,
            'tables': table_ids,
        })

    # If deposit pending, redirect to deposit modal
    if initial_status == 'deposit_pending':
        return HttpResponse(
            status=204,
            headers={
                'HX-Trigger': json.dumps({
                    'bookingCreated': {'id': str(reservation.id), 'needs_deposit': True},
                    'showNotification': {'message': f'Booking {reservation.reservation_code} dibuat. Silakan bayar deposit.', 'type': 'info'},
                })
            }
        )

    return HttpResponse(
        status=204,
        headers={
            'HX-Trigger': json.dumps({
                'bookingCreated': {'id': str(reservation.id), 'needs_deposit': False},
                'showNotification': {'message': f'Booking {reservation.reservation_code} berhasil dikonfirmasi!', 'type': 'success'},
            })
        }
    )


@login_required
def booking_detail(request, reservation_id):
    """Detail booking — HTMX modal"""
    reservation = get_object_or_404(Reservation, id=reservation_id, brand=request.user.brand)
    logs = reservation.logs.select_related('created_by').order_by('-created_at')[:10]
    deposits = reservation.deposits.all()

    context = {
        'reservation': reservation,
        'logs': logs,
        'deposits': deposits,
    }
    return render(request, 'tables/booking/detail_modal.html', context)


# =============================================================================
# DEPOSIT PAYMENT
# =============================================================================

@login_required
def booking_deposit_form(request, reservation_id):
    """Deposit payment form — HTMX modal with full payment profile support"""
    reservation = get_object_or_404(
        Reservation, id=reservation_id, brand=request.user.brand,
        status='deposit_pending'
    )

    from apps.core.models import PaymentMethodProfile, EFTTerminal
    from django.db.models import Q
    company = request.user.company if hasattr(request.user, 'company') else None
    payment_profiles = PaymentMethodProfile.objects.filter(
        company=company, is_active=True,
    ).filter(
        Q(brand=request.user.brand) | Q(brand__isnull=True)
    ).prefetch_related('prompts').order_by('sort_order', 'name')

    # Build profiles list with prompts data for template
    profiles_list = []
    for p in payment_profiles:
        prompts = list(
            p.prompts.order_by('sort_order').values(
                'field_name', 'label', 'field_type', 'min_length', 'max_length',
                'placeholder', 'use_scanner', 'is_required',
            )
        )
        non_amount_prompts = [pr for pr in prompts if pr['field_type'] != 'amount']
        profiles_list.append({
            'id': str(p.id),
            'name': p.name,
            'code': p.code,
            'color': p.color or '#6b7280',
            'method_id': p.legacy_method_id or p.code,
            'allow_change': p.allow_change,
            'prompts': non_amount_prompts,
            'has_scanner': any(pr['field_type'] == 'scanner' for pr in non_amount_prompts),
        })

    # Load EFT terminals
    eft_terminals = []
    if company:
        eft_terminals = list(
            EFTTerminal.objects.filter(company=company, is_active=True)
            .order_by('sort_order', 'code')
            .values('code', 'name')
        )

    context = {
        'reservation': reservation,
        'payment_profiles': payment_profiles,
        'profiles_list': profiles_list,
        'profiles_json': json.dumps(profiles_list),
        'eft_terminals': eft_terminals,
    }
    return render(request, 'tables/booking/deposit_modal.html', context)


@login_required
@require_http_methods(["POST"])
def booking_deposit_pay(request, reservation_id):
    """Process deposit payment — supports single and split (multi) payments"""
    reservation = get_object_or_404(
        Reservation, id=reservation_id, brand=request.user.brand,
        status='deposit_pending'
    )

    # Parse split payments (payments[0][method], payments[0][amount], etc.)
    split_payments = []
    i = 0
    while True:
        key = f'payments[{i}][method]'
        if key not in request.POST:
            break
        try:
            sp_amount = Decimal(
                str(request.POST.get(f'payments[{i}][amount]', '0')).replace(',', '').strip() or '0'
            )
        except Exception:
            sp_amount = Decimal('0')
        sp_prompt_raw = request.POST.get(f'payments[{i}][prompt_data]', '{}')
        sp_metadata = {}
        try:
            sp_metadata = json.loads(sp_prompt_raw) if sp_prompt_raw else {}
        except (json.JSONDecodeError, TypeError):
            pass
        split_payments.append({
            'method': request.POST.get(f'payments[{i}][method]', 'cash'),
            'amount': sp_amount,
            'profile_id': request.POST.get(f'payments[{i}][profile_id]') or None,
            'metadata': sp_metadata,
        })
        i += 1

    # If no split payments, use the single payment fields
    if not split_payments:
        amount_raw = str(request.POST.get('amount', '0')).replace(',', '').strip()
        amount = Decimal(amount_raw) if amount_raw else Decimal('0')
        payment_method = request.POST.get('payment_method', 'cash')
        profile_id = request.POST.get('payment_profile') or None
        prompt_data_raw = request.POST.get('prompt_data', '{}')
        payment_metadata = {}
        try:
            payment_metadata = json.loads(prompt_data_raw) if prompt_data_raw else {}
        except (json.JSONDecodeError, TypeError):
            pass

        if amount <= 0:
            return HttpResponse(
                '<div class="p-3 bg-red-100 text-red-700 rounded text-sm">Jumlah deposit harus lebih dari 0</div>',
                status=400,
            )
        split_payments = [{
            'method': payment_method,
            'amount': amount,
            'profile_id': profile_id,
            'metadata': payment_metadata,
        }]

    total_amount = sum(sp['amount'] for sp in split_payments)
    if total_amount <= 0:
        return HttpResponse(
            '<div class="p-3 bg-red-100 text-red-700 rounded text-sm">Jumlah deposit harus lebih dari 0</div>',
            status=400,
        )

    with transaction.atomic():
        deposit_ids = []
        for sp in split_payments:
            if sp['amount'] <= 0:
                continue
            dep = ReservationDeposit.objects.create(
                reservation=reservation,
                amount=sp['amount'],
                payment_method=sp['method'],
                payment_profile_id=sp['profile_id'],
                payment_metadata=sp['metadata'],
                status='paid',
                created_by=request.user,
            )
            deposit_ids.append(str(dep.id))

        reservation.deposit_paid = reservation.deposits.filter(status='paid').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
        reservation.deposit_status = 'paid' if reservation.deposit_paid >= reservation.deposit_amount else 'partial'
        reservation.status = 'confirmed'
        reservation.confirmed_by = request.user
        reservation.save()

        _log(reservation, 'deposit_paid', request.user, {
            'total_amount': str(total_amount),
            'split_count': len(deposit_ids),
            'deposit_ids': deposit_ids,
        })

    return HttpResponse(
        status=204,
        headers={
            'HX-Trigger': json.dumps({
                'depositPaid': {'id': str(reservation.id)},
                'showNotification': {'message': f'Deposit Rp {total_amount:,.0f} berhasil! Booking {reservation.reservation_code} dikonfirmasi.', 'type': 'success'},
            })
        }
    )


# =============================================================================
# DEPOSIT QRIS ENDPOINTS
# =============================================================================

@login_required
@require_http_methods(["POST"])
def booking_deposit_qris_create(request, reservation_id):
    """Create QRIS transaction for deposit payment"""
    import logging
    import time as _time
    qris_logger = logging.getLogger('pos.qris')

    reservation = get_object_or_404(
        Reservation, id=reservation_id, brand=request.user.brand,
        status='deposit_pending'
    )

    from apps.pos.models import QRISTransaction
    from apps.pos.payment_gateway import get_payment_gateway, _audit_log

    try:
        amount = Decimal(str(request.POST.get('amount', '0')).replace(',', '').strip())
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid amount'}, status=400)

    if amount <= 0:
        return JsonResponse({'success': False, 'error': 'Amount must be positive'}, status=400)

    # Cancel any existing pending QRIS for this reservation
    old_pending = list(
        QRISTransaction.objects.filter(
            bill__isnull=True,
            amount=reservation.deposit_amount,
            status='pending',
            created_by=request.user,
        ).values_list('transaction_id', flat=True)
    )
    QRISTransaction.objects.filter(
        bill__isnull=True,
        amount=reservation.deposit_amount,
        status='pending',
        created_by=request.user,
    ).update(status='cancelled')

    t0 = _time.monotonic()
    gateway = get_payment_gateway()
    result = gateway.create_qris_transaction(None, amount, user=request.user)

    if not result.success:
        elapsed_ms = (_time.monotonic() - t0) * 1000
        qris_logger.error('DEPOSIT_QRIS_CREATE_ERROR reservation=%s error=%s', reservation_id, result.error_message)
        return JsonResponse({'success': False, 'error': result.error_message}, status=500)

    # Generate QR code image
    qr_image = None
    try:
        import qrcode as qrlib
        import io as _io
        import base64 as _b64
        qr = qrlib.QRCode(version=1, error_correction=qrlib.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(result.qr_string)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = _io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        qr_image = 'data:image/png;base64,' + _b64.b64encode(buf.read()).decode()
    except Exception as e:
        qris_logger.warning('DEPOSIT_QRIS_QR_IMAGE_ERROR txn_id=%s error=%s', result.transaction_id, str(e))

    elapsed_ms = (_time.monotonic() - t0) * 1000
    qris_logger.info(
        'DEPOSIT_QRIS_CREATE_OK reservation=%s txn_id=%s amount=%s elapsed=%.0fms',
        reservation_id, result.transaction_id, amount, elapsed_ms,
    )

    return JsonResponse({
        'success': True,
        'transaction_id': result.transaction_id,
        'qr_string': result.qr_string,
        'qr_image': qr_image,
        'expires_at': result.expires_at.isoformat() if result.expires_at else None,
        'amount': float(amount),
    })


@login_required
def booking_deposit_qris_status(request, reservation_id, transaction_id):
    """Poll QRIS transaction status for deposit payment"""
    from apps.pos.payment_gateway import get_payment_gateway

    get_object_or_404(Reservation, id=reservation_id, brand=request.user.brand)
    gateway = get_payment_gateway()
    result = gateway.check_status(transaction_id)

    return JsonResponse({
        'status': result.status,
        'transaction_id': result.transaction_id,
        'paid_at': result.paid_at.isoformat() if result.paid_at else None,
    })


@login_required
@require_http_methods(["POST"])
def booking_deposit_qris_cancel(request, reservation_id, transaction_id):
    """Cancel a pending QRIS transaction for deposit"""
    from apps.pos.payment_gateway import get_payment_gateway

    get_object_or_404(Reservation, id=reservation_id, brand=request.user.brand)
    gateway = get_payment_gateway()
    success = gateway.cancel_transaction(transaction_id)

    return JsonResponse({'success': success})


@login_required
@require_http_methods(["POST"])
def booking_deposit_qris_simulate(request, reservation_id, transaction_id):
    """DEV ONLY: Simulate QRIS payment for deposit"""
    from apps.pos.payment_gateway import get_payment_gateway

    get_object_or_404(Reservation, id=reservation_id, brand=request.user.brand)
    gateway = get_payment_gateway()
    success = gateway.simulate_payment(transaction_id)

    return JsonResponse({'success': success})


# =============================================================================
# CHECK-IN
# =============================================================================

@login_required
@require_http_methods(["POST"])
def booking_checkin(request, reservation_id):
    """Check-in tamu — create bill & update table status"""
    reservation = get_object_or_404(
        Reservation, id=reservation_id, brand=request.user.brand,
        status='confirmed'
    )

    actual_pax = int(request.POST.get('actual_pax', reservation.party_size))
    table = reservation.tables.first()

    if not table:
        return HttpResponse(
            '<div class="p-3 bg-red-100 text-red-700 rounded text-sm">Tidak ada meja yang di-assign ke booking ini</div>',
            status=400
        )

    # Check if table is currently occupied
    existing_bill = table.get_active_bill()
    if existing_bill:
        return HttpResponse(
            f'<div class="p-3 bg-red-100 text-red-700 rounded text-sm">Meja {table.number} masih dipakai (Bill {existing_bill.bill_number}). Selesaikan atau pindahkan dulu.</div>',
            status=400
        )

    with transaction.atomic():
        # Create bill
        bill = Bill.objects.create(
            brand=request.user.brand,
            store=reservation.store,
            company=reservation.company,
            table=table,
            bill_type='dine_in',
            guest_count=actual_pax,
            customer_name=reservation.guest_name,
            customer_phone=reservation.guest_phone,
            created_by=request.user,
        )

        # Update table status
        for t in reservation.tables.all():
            t.status = 'occupied'
            t.save(update_fields=['status'])

        # Update reservation
        reservation.status = 'checked_in'
        reservation.bill = bill
        reservation.save()

        # Log
        BillLog.objects.create(
            bill=bill, action='open', user=request.user,
            details={'reservation': reservation.reservation_code, 'pax': actual_pax}
        )
        _log(reservation, 'checked_in', request.user, {
            'bill_id': bill.id,
            'bill_number': bill.bill_number,
            'actual_pax': actual_pax,
        })

    # Set active bill in session and redirect to POS
    request.session['active_bill_id'] = bill.id
    request.session.modified = True

    return HttpResponse(
        status=204,
        headers={
            'HX-Trigger': json.dumps({
                'checkedIn': {'id': str(reservation.id), 'bill_id': bill.id},
                'showNotification': {'message': f'{reservation.guest_name} checked in! Bill {bill.bill_number} dibuat.', 'type': 'success'},
            }),
            'HX-Redirect': '/pos/',
        }
    )


# =============================================================================
# CANCEL & NO-SHOW
# =============================================================================

@login_required
def booking_cancel_form(request, reservation_id):
    """Cancel confirmation modal"""
    reservation = get_object_or_404(
        Reservation, id=reservation_id, brand=request.user.brand,
    )
    if not reservation.can_cancel():
        return HttpResponse(
            '<div class="p-3 bg-red-100 text-red-700 rounded text-sm">Booking ini tidak bisa dibatalkan</div>',
            status=400
        )

    refund_amount = reservation.get_refund_amount()
    forfeited = reservation.deposit_paid - refund_amount

    context = {
        'reservation': reservation,
        'refund_amount': refund_amount,
        'forfeited': forfeited,
    }
    return render(request, 'tables/booking/cancel_modal.html', context)


@login_required
@require_http_methods(["POST"])
def booking_cancel(request, reservation_id):
    """Process cancellation"""
    reservation = get_object_or_404(
        Reservation, id=reservation_id, brand=request.user.brand,
    )
    if not reservation.can_cancel():
        return HttpResponse('<div class="p-3 bg-red-100 text-red-700 rounded text-sm">Booking tidak bisa dibatalkan</div>', status=400)

    reason = request.POST.get('reason', '').strip()
    refund_amount = reservation.get_refund_amount()
    forfeited = reservation.deposit_paid - refund_amount

    with transaction.atomic():
        # Update deposits
        if reservation.deposit_paid > 0:
            for dep in reservation.deposits.filter(status='paid'):
                if refund_amount > 0:
                    dep.status = 'refunded'
                    dep.refund_amount = min(refund_amount, dep.amount)
                    dep.refund_reason = reason
                    dep.refunded_at = timezone.now()
                    refund_amount -= dep.refund_amount
                else:
                    dep.status = 'forfeited'
                dep.save()

        # Release tables
        for t in reservation.tables.all():
            if t.status == 'reserved':
                t.status = 'available'
                t.save(update_fields=['status'])

        reservation.status = 'cancelled'
        reservation.cancelled_at = timezone.now()
        reservation.cancellation_reason = reason
        reservation.save()

        _log(reservation, 'cancelled', request.user, {
            'reason': reason,
            'refund': str(reservation.get_refund_amount()),
            'forfeited': str(forfeited),
        })

    return HttpResponse(
        status=204,
        headers={
            'HX-Trigger': json.dumps({
                'bookingCancelled': {'id': str(reservation.id)},
                'showNotification': {'message': f'Booking {reservation.reservation_code} dibatalkan.', 'type': 'warning'},
            })
        }
    )


@login_required
@require_http_methods(["POST"])
def booking_noshow(request, reservation_id):
    """Mark as no-show"""
    reservation = get_object_or_404(
        Reservation, id=reservation_id, brand=request.user.brand,
        status='confirmed'
    )

    with transaction.atomic():
        # Forfeit all deposits
        reservation.deposits.filter(status='paid').update(status='forfeited')

        # Release tables
        for t in reservation.tables.all():
            if t.status == 'reserved':
                t.status = 'available'
                t.save(update_fields=['status'])

        reservation.status = 'no_show'
        reservation.noshow_at = timezone.now()
        reservation.deposit_status = 'forfeited' if reservation.deposit_paid > 0 else 'none'
        reservation.save()

        _log(reservation, 'no_show', request.user, {
            'deposit_forfeited': str(reservation.deposit_paid),
        })

    return HttpResponse(
        status=204,
        headers={
            'HX-Trigger': json.dumps({
                'bookingNoShow': {'id': str(reservation.id)},
                'showNotification': {'message': f'{reservation.guest_name} ditandai No-Show. Meja dibebaskan.', 'type': 'warning'},
            })
        }
    )


# =============================================================================
# TABLE AVAILABILITY API (for form AJAX)
# =============================================================================

@login_required
def available_tables(request):
    """Get available tables for a given date/time — JSON API"""
    date_str = request.GET.get('date')
    time_str = request.GET.get('time')
    duration = int(request.GET.get('duration', 120))

    if not date_str or not time_str:
        return JsonResponse({'tables': []})

    res_date = datetime.date.fromisoformat(date_str)
    res_time = datetime.time.fromisoformat(time_str)
    end_dt = datetime.datetime.combine(res_date, res_time) + datetime.timedelta(minutes=duration)

    config = _get_config(request)
    buffer = config.overbooking_buffer

    # Get all booked table IDs for that time slot
    booked_table_ids = set()
    booked_reservations = Reservation.objects.filter(
        brand=request.user.brand,
        reservation_date=res_date,
        status__in=['pending', 'deposit_pending', 'confirmed', 'checked_in'],
    ).prefetch_related('tables')

    for r in booked_reservations:
        r_start = datetime.datetime.combine(res_date, r.time_start) - datetime.timedelta(minutes=buffer)
        r_end = datetime.datetime.combine(res_date, r.time_end) + datetime.timedelta(minutes=buffer)
        req_start = datetime.datetime.combine(res_date, res_time)
        req_end = end_dt

        if req_start < r_end and req_end > r_start:
            for t in r.tables.all():
                booked_table_ids.add(str(t.id))

    # All tables
    tables = Table.objects.filter(
        area__brand=request.user.brand, is_active=True
    ).select_related('area').order_by('area__sort_order', 'number')

    result = []
    for t in tables:
        result.append({
            'id': str(t.id),
            'number': t.number,
            'area': t.area.name,
            'capacity': t.capacity,
            'available': str(t.id) not in booked_table_ids,
        })

    return JsonResponse({'tables': result})


# =============================================================================
# PRINT DEPOSIT RECEIPT
# =============================================================================

@login_required
def booking_deposit_print_preview(request, reservation_id):
    """Browser print preview for deposit receipt"""
    reservation = get_object_or_404(
        Reservation, id=reservation_id, brand=request.user.brand
    )
    deposits = reservation.deposits.filter(status='paid').select_related('payment_profile')

    context = {
        'reservation': reservation,
        'deposits': deposits,
    }
    return render(request, 'tables/booking/deposit_receipt.html', context)


@login_required
def booking_deposit_data(request, reservation_id):
    """Return deposit receipt data as JSON for local printer"""
    reservation = get_object_or_404(
        Reservation, id=reservation_id, brand=request.user.brand
    )
    deposits = reservation.deposits.filter(status='paid').select_related('payment_profile')

    if not deposits.exists():
        return JsonResponse({'success': False, 'error': 'No deposit found'}, status=404)

    tables_list = [t.number for t in reservation.tables.all()]

    data = {
        'outlet_name': reservation.brand.name if reservation.brand else '',
        'outlet_address': getattr(reservation.brand, 'address', '') or '',
        'outlet_phone': getattr(reservation.brand, 'phone', '') or '',
        'bill_number': f'DP-{reservation.reservation_code}',
        'date': reservation.created_at.strftime('%d/%m/%Y %H:%M') if reservation.created_at else '',
        'cashier': reservation.created_by.get_full_name() if reservation.created_by else '',
        'customer_name': reservation.guest_name,
        'table': ', '.join(tables_list) if tables_list else None,
        'items': [{
            'name': f'Deposit Reservasi {reservation.reservation_code}',
            'qty': 1,
            'price': float(reservation.deposit_paid),
            'subtotal': float(reservation.deposit_paid),
        }],
        'payments': [
            {
                'method': dep.payment_profile.name if dep.payment_profile else dep.get_payment_method_display() if hasattr(dep, 'get_payment_method_display') else dep.payment_method.title(),
                'amount': float(dep.amount),
            }
            for dep in deposits
        ],
        'subtotal': float(reservation.deposit_paid),
        'discount': 0,
        'tax': 0,
        'service': 0,
        'total': float(reservation.deposit_paid),
        'footer': f'Booking: {reservation.reservation_code}\n'
                  f'Tanggal: {reservation.reservation_date.strftime("%d/%m/%Y")}\n'
                  f'Jam: {reservation.time_start.strftime("%H:%M")}\n'
                  f'Tamu: {reservation.guest_name} ({reservation.party_size} pax)\n'
                  f'Terima Kasih!',
    }
    return JsonResponse(data)
