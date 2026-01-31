"""
Queue Number Utility Functions
Auto-increment daily queue numbers for takeaway orders
"""
from django.db import models
from django.utils import timezone


def generate_queue_number(brand):
    """
    Generate next queue number for today
    Auto-increment, reset daily at 00:00
    
    Args:
        brand: Brand instance
    
    Returns:
        int: Next queue number (1, 2, 3, ...)
    
    Example:
        >>> brand = Brand.objects.get(code='AVRIL')
        >>> queue = generate_queue_number(brand)
        >>> print(queue)  # 1 (if first order today)
    """
    from apps.pos.models import Bill
    
    # Use local timezone date (Jakarta time)
    today = timezone.localtime(timezone.now()).date()
    
    last_queue = Bill.objects.filter(
        brand=brand,
        bill_type='takeaway',
        created_at__date=today,
        queue_number__isnull=False
    ).aggregate(max_queue=models.Max('queue_number'))
    
    max_queue = last_queue['max_queue'] or 0
    return max_queue + 1


def get_active_queues(brand, limit=10):
    """
    Get active queue numbers waiting to be served
    
    Args:
        brand: Brand instance
        limit: Maximum number of queues to return
    
    Returns:
        QuerySet: Bills with status='paid' (not completed yet)
    
    Example:
        >>> active = get_active_queues(brand, limit=5)
        >>> for bill in active:
        ...     print(f"Queue #{bill.queue_number} - {bill.customer_name}")
    """
    from apps.pos.models import Bill
    
    # Use local timezone date (Jakarta time)
    today = timezone.localtime(timezone.now()).date()
    
    return Bill.objects.filter(
        brand=brand,
        bill_type='takeaway',
        created_at__date=today,
        status='paid',  # Paid but not completed
        queue_number__isnull=False
    ).order_by('queue_number')[:limit]


def get_serving_queues(brand, limit=3, minutes=5):
    """
    Get recently completed queues (now serving)
    Only shows orders completed within the last X minutes
    
    Args:
        brand: Brand instance
        limit: Maximum number of queues to return
        minutes: Only show orders completed within last X minutes (default: 5)
    
    Returns:
        QuerySet: Recently completed bills within time window
    
    Example:
        >>> serving = get_serving_queues(brand, limit=3, minutes=5)
        >>> for bill in serving:
        ...     print(f"Queue #{bill.queue_number} - Ready!")
    """
    from apps.pos.models import Bill
    from datetime import timedelta
    
    # Use local timezone date (Jakarta time)
    today = timezone.localtime(timezone.now()).date()
    now = timezone.now()
    
    # Only show orders completed in the last X minutes
    time_threshold = now - timedelta(minutes=minutes)
    
    return Bill.objects.filter(
        brand=brand,
        bill_type='takeaway',
        created_at__date=today,
        status='completed',
        queue_number__isnull=False,
        completed_at__gte=time_threshold  # Only recently completed
    ).order_by('-completed_at')[:limit]


def get_queue_statistics(brand):
    """
    Get queue statistics for today
    
    Args:
        brand: Brand instance
    
    Returns:
        dict: Statistics including avg wait time, total orders, etc.
    
    Example:
        >>> stats = get_queue_statistics(brand)
        >>> print(f"Average wait: {stats['avg_wait_minutes']} min")
        >>> print(f"Total orders: {stats['total_orders']}")
    """
    from apps.pos.models import Bill
    
    # Use local timezone date (Jakarta time)
    today = timezone.localtime(timezone.now()).date()
    
    completed_orders = Bill.objects.filter(
        brand=brand,
        bill_type='takeaway',
        created_at__date=today,
        status='completed',
        queue_number__isnull=False,
        completed_at__isnull=False
    )
    
    # Calculate average wait time
    wait_times = []
    for order in completed_orders:
        if order.completed_at and order.created_at:
            wait_seconds = (order.completed_at - order.created_at).total_seconds()
            wait_times.append(wait_seconds)
    
    avg_wait_seconds = sum(wait_times) / len(wait_times) if wait_times else 0
    avg_wait_minutes = int(avg_wait_seconds / 60)
    
    # Total orders today
    total_orders = Bill.objects.filter(
        brand=brand,
        bill_type='takeaway',
        created_at__date=today,
        queue_number__isnull=False
    ).count()
    
    # Active queues
    active_count = Bill.objects.filter(
        brand=brand,
        bill_type='takeaway',
        created_at__date=today,
        status='paid',
        queue_number__isnull=False
    ).count()
    
    return {
        'avg_wait_minutes': avg_wait_minutes,
        'avg_wait_seconds': int(avg_wait_seconds),
        'total_orders': total_orders,
        'completed_orders': completed_orders.count(),
        'active_orders': active_count,
        'completion_rate': (completed_orders.count() / total_orders * 100) if total_orders > 0 else 0,
    }
