"""
Report utilities for cashier performance and transaction analysis
"""
from django.db.models import Sum, Count, Q, F, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from .models import Bill, BillItem, Payment


def get_cashier_summary(user, start_date=None, end_date=None):
    """
    Get comprehensive summary of cashier performance
    
    Args:
        user: User object (cashier)
        start_date: Start datetime (default: today 00:00)
        end_date: End datetime (default: now)
    
    Returns:
        dict with cashier performance metrics
    """
    if not start_date:
        start_date = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if not end_date:
        end_date = timezone.now()
    
    # Bills created by cashier
    bills_created = Bill.objects.filter(
        created_by=user,
        created_at__gte=start_date,
        created_at__lte=end_date
    )
    
    # Bills closed/paid by cashier
    bills_closed = Bill.objects.filter(
        closed_by=user,
        closed_at__gte=start_date,
        closed_at__lte=end_date,
        status='paid'
    )
    
    # Items added by cashier
    items_added = BillItem.objects.filter(
        created_by=user,
        created_at__gte=start_date,
        created_at__lte=end_date,
        is_void=False
    )
    
    # Items voided by cashier
    items_voided = BillItem.objects.filter(
        void_by=user,
        created_at__gte=start_date,
        created_at__lte=end_date,
        is_void=True
    )
    
    # Payments processed by cashier
    payments = Payment.objects.filter(
        created_by=user,
        created_at__gte=start_date,
        created_at__lte=end_date
    )
    
    # Payment breakdown by method
    payment_methods = payments.values('method').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    return {
        'user': user,
        'period': {
            'start': start_date,
            'end': end_date,
        },
        'bills_created': {
            'count': bills_created.count(),
            'total_amount': bills_created.aggregate(Sum('total'))['total__sum'] or Decimal('0'),
            'by_type': bills_created.values('bill_type').annotate(count=Count('id')),
        },
        'bills_closed': {
            'count': bills_closed.count(),
            'total_amount': bills_closed.aggregate(Sum('total'))['total__sum'] or Decimal('0'),
            'average_bill': bills_closed.aggregate(Avg('total'))['total__avg'] or Decimal('0'),
        },
        'items': {
            'added_count': items_added.count(),
            'added_total': items_added.aggregate(Sum('total'))['total__sum'] or Decimal('0'),
            'voided_count': items_voided.count(),
            'voided_total': items_voided.aggregate(Sum('total'))['total__sum'] or Decimal('0'),
        },
        'payments': {
            'total_amount': payments.aggregate(Sum('amount'))['amount__sum'] or Decimal('0'),
            'total_count': payments.count(),
            'by_method': list(payment_methods),
        },
    }


def get_all_cashiers_summary(Brand=None, start_date=None, end_date=None):
    """
    Get summary for all cashiers in Brand
    
    Args:
        Brand: Brand object (if None, all brands)
        start_date: Start datetime
        end_date: End datetime
    
    Returns:
        list of dicts with cashier summaries
    """
    from apps.core.models import User
    
    if not start_date:
        start_date = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if not end_date:
        end_date = timezone.now()
    
    # Get all cashiers who processed bills in period
    cashier_ids = set()
    
    bills_query = Bill.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date
    )
    if Brand:
        bills_query = bills_query.filter(Brand=Brand)
    
    cashier_ids.update(bills_query.values_list('created_by_id', flat=True))
    cashier_ids.update(bills_query.values_list('closed_by_id', flat=True).exclude(closed_by_id=None))
    
    cashiers = User.objects.filter(id__in=cashier_ids)
    
    summaries = []
    for cashier in cashiers:
        summary = get_cashier_summary(cashier, start_date, end_date)
        summaries.append(summary)
    
    # Sort by total payments processed
    summaries.sort(key=lambda x: x['payments']['total_amount'], reverse=True)
    
    return summaries


def get_cashier_shift_report(user, shift_start=None):
    """
    Get shift report for a cashier (from shift start to now)
    
    Args:
        user: User object (cashier)
        shift_start: Shift start datetime (default: today 00:00)
    
    Returns:
        dict with shift performance
    """
    if not shift_start:
        shift_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    return get_cashier_summary(user, shift_start, timezone.now())


def get_terminal_cashier_report(terminal, start_date=None, end_date=None):
    """
    Get report for all cashiers who used a specific terminal
    
    Args:
        terminal: POSTerminal object
        start_date: Start datetime
        end_date: End datetime
    
    Returns:
        dict with terminal usage by cashiers
    """
    if not start_date:
        start_date = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if not end_date:
        end_date = timezone.now()
    
    bills = Bill.objects.filter(
        terminal=terminal,
        created_at__gte=start_date,
        created_at__lte=end_date
    )
    
    # Group by cashier
    cashier_stats = bills.values('created_by__username').annotate(
        bill_count=Count('id'),
        total_amount=Sum('total'),
        paid_count=Count('id', filter=Q(status='paid'))
    ).order_by('-total_amount')
    
    return {
        'terminal': terminal,
        'period': {
            'start': start_date,
            'end': end_date,
        },
        'total_bills': bills.count(),
        'total_amount': bills.aggregate(Sum('total'))['total__sum'] or Decimal('0'),
        'cashier_stats': list(cashier_stats),
    }
