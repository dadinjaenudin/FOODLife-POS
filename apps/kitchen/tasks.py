from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import KitchenTicket, KitchenTicketLog


@shared_task
def purge_kitchen_logs_and_tickets():
    """Purge old kitchen logs and tickets based on retention settings."""
    retention_logs = getattr(settings, 'KITCHEN_LOG_RETENTION_DAYS', 30)
    retention_tickets = getattr(settings, 'KITCHEN_TICKET_RETENTION_DAYS', 30)

    cutoff_logs = timezone.now() - timedelta(days=int(retention_logs))
    cutoff_tickets = timezone.now() - timedelta(days=int(retention_tickets))

    logs_qs = KitchenTicketLog.objects.filter(timestamp__lt=cutoff_logs)
    logs_deleted = logs_qs.count()
    logs_qs.delete()

    tickets_qs = KitchenTicket.objects.filter(
        created_at__lt=cutoff_tickets,
        status__in=['printed', 'failed']
    )
    tickets_deleted = tickets_qs.count()
    tickets_qs.delete()

    return {
        'logs_deleted': logs_deleted,
        'tickets_deleted': tickets_deleted,
        'cutoff_logs': cutoff_logs.isoformat(),
        'cutoff_tickets': cutoff_tickets.isoformat(),
    }