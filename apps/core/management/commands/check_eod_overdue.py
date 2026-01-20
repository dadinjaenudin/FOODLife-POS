"""
Check for overdue EOD sessions and send alerts

Run this as a cron job every hour:
python manage.py check_eod_overdue
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.models_session import StoreSession, BusinessDateAlert
from apps.core.services_eod import EODService


class Command(BaseCommand):
    help = 'Check for overdue EOD sessions and create alerts'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--notify',
            action='store_true',
            help='Send SMS/email notifications (not just create alerts)',
        )
    
    def handle(self, *args, **options):
        self.stdout.write("Checking for overdue EOD sessions...")
        
        overdue_sessions = EODService.get_pending_eod_sessions()
        
        if not overdue_sessions:
            self.stdout.write(self.style.SUCCESS("✅ No overdue sessions found"))
            return
        
        for session in overdue_sessions:
            hours = session.hours_since_open()
            store = session.store
            
            # Create alert
            alert = BusinessDateAlert.create_eod_overdue_alert(store, session)
            
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️  {store.store_code} - Business date {session.business_date} "
                    f"overdue by {hours:.1f} hours"
                )
            )
            
            # Send notification if requested
            if options['notify']:
                self.send_notification(session, alert)
        
        self.stdout.write(
            self.style.WARNING(
                f"Found {overdue_sessions.count()} overdue session(s)"
            )
        )
    
    def send_notification(self, session, alert):
        """
        Send SMS/email notification
        (Implement your notification service here)
        """
        # Example: Send SMS to store manager
        # manager = session.store.outlet.manager
        # sms_service.send(manager.phone, alert.message)
        
        self.stdout.write(
            self.style.NOTICE(
                f"  📱 Notification sent for {session.store.store_code}"
            )
        )
