"""
Example views for cashier reporting
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from .reports import (
    get_cashier_summary,
    get_all_cashiers_summary,
    get_cashier_shift_report,
    get_terminal_cashier_report
)


@login_required
def cashier_shift_report(request):
    """
    Current shift report for logged-in cashier
    """
    # Get shift start from request or default to today 00:00
    shift_start_str = request.GET.get('shift_start')
    if shift_start_str:
        shift_start = datetime.fromisoformat(shift_start_str)
    else:
        shift_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    summary = get_cashier_shift_report(request.user, shift_start)
    
    return render(request, 'pos/reports/cashier_shift.html', {
        'summary': summary,
    })


@login_required
def cashier_daily_report(request):
    """
    Daily report for specific cashier
    """
    user_id = request.GET.get('user_id')
    date_str = request.GET.get('date')
    
    if user_id:
        from apps.core.models import User
        user = User.objects.get(id=user_id)
    else:
        user = request.user
    
    if date_str:
        report_date = datetime.fromisoformat(date_str)
    else:
        report_date = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    start_date = report_date
    end_date = start_date + timedelta(days=1)
    
    summary = get_cashier_summary(user, start_date, end_date)
    
    if request.headers.get('HX-Request'):
        return render(request, 'pos/reports/partials/cashier_summary.html', {
            'summary': summary,
        })
    
    return render(request, 'pos/reports/cashier_daily.html', {
        'summary': summary,
        'user': user,
        'date': report_date,
    })


@login_required
def brand_cashiers_report(request):
    """
    Compare all cashiers in Brand
    """
    date_str = request.GET.get('date')
    
    if date_str:
        report_date = datetime.fromisoformat(date_str)
    else:
        report_date = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    start_date = report_date
    end_date = start_date + timedelta(days=1)
    
    summaries = get_all_cashiers_summary(
        Brand=request.user.Brand,
        start_date=start_date,
        end_date=end_date
    )
    
    return render(request, 'pos/reports/brand_cashiers.html', {
        'summaries': summaries,
        'date': report_date,
    })


@login_required
def terminal_usage_report(request):
    """
    Terminal usage by cashiers
    """
    terminal_id = request.GET.get('terminal_id')
    date_str = request.GET.get('date')
    
    if not terminal_id:
        return JsonResponse({'error': 'terminal_id required'}, status=400)
    
    from apps.core.models import POSTerminal
    terminal = POSTerminal.objects.get(id=terminal_id)
    
    if date_str:
        report_date = datetime.fromisoformat(date_str)
    else:
        report_date = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    start_date = report_date
    end_date = start_date + timedelta(days=1)
    
    report = get_terminal_cashier_report(terminal, start_date, end_date)
    
    return render(request, 'pos/reports/terminal_usage.html', {
        'report': report,
        'date': report_date,
    })


@login_required
def cashier_summary_api(request):
    """
    JSON API for cashier summary (for HTMX or charts)
    """
    user_id = request.GET.get('user_id')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    from apps.core.models import User
    user = User.objects.get(id=user_id) if user_id else request.user
    
    start_date = datetime.fromisoformat(start_date_str) if start_date_str else None
    end_date = datetime.fromisoformat(end_date_str) if end_date_str else None
    
    summary = get_cashier_summary(user, start_date, end_date)
    
    # Convert to JSON-serializable format
    return JsonResponse({
        'user': {
            'id': str(user.id),
            'username': user.username,
            'name': f"{user.first_name} {user.last_name}",
        },
        'period': {
            'start': summary['period']['start'].isoformat(),
            'end': summary['period']['end'].isoformat(),
        },
        'bills_created': {
            'count': summary['bills_created']['count'],
            'total_amount': str(summary['bills_created']['total_amount']),
        },
        'bills_closed': {
            'count': summary['bills_closed']['count'],
            'total_amount': str(summary['bills_closed']['total_amount']),
            'average_bill': str(summary['bills_closed']['average_bill']),
        },
        'items': {
            'added_count': summary['items']['added_count'],
            'added_total': str(summary['items']['added_total']),
            'voided_count': summary['items']['voided_count'],
            'voided_total': str(summary['items']['voided_total']),
        },
        'payments': {
            'total_amount': str(summary['payments']['total_amount']),
            'total_count': summary['payments']['total_count'],
            'by_method': [
                {
                    'method': p['method'],
                    'total': str(p['total']),
                    'count': p['count'],
                }
                for p in summary['payments']['by_method']
            ],
        },
    })
