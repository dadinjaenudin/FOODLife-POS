from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.models import Store, User
from apps.core.models_session import StoreSession


class Command(BaseCommand):
    help = 'Quick open store session for testing'

    def handle(self, *args, **options):
        store_config = Store.get_current()
        if not store_config:
            self.stdout.write(self.style.ERROR('No store config found. Run setup first.'))
            return
        
        # Check if session already exists
        existing = StoreSession.get_current(store_config)
        if existing:
            self.stdout.write(self.style.WARNING(f'Session already open: {existing}'))
            self.stdout.write(f'  Business Date: {existing.business_date}')
            self.stdout.write(f'  Status: {existing.status}')
            self.stdout.write(f'  Opened at: {existing.opened_at}')
            return
        
        # Get admin user
        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            admin = User.objects.filter(role='admin').first()
        
        if not admin:
            self.stdout.write(self.style.ERROR('No admin user found'))
            return
        
        # Create new session
        today = timezone.now().date()
        session = StoreSession.objects.create(
            store=store_config,
            business_date=today,
            session_number=1,
            opened_by=admin,
            status='open',
            is_current=True
        )
        
        self.stdout.write(self.style.SUCCESS(f'✅ Session opened successfully!'))
        self.stdout.write(f'  ID: {session.id}')
        self.stdout.write(f'  Business Date: {session.business_date}')
        self.stdout.write(f'  Opened by: {session.opened_by.username}')
        self.stdout.write(f'  Status: {session.status}')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Cashiers can now open their shifts!'))
