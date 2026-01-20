"""
Management command to configure Edge Server store identity
"""
from django.core.management.base import BaseCommand
from apps.core.models import StoreConfig, Outlet
import uuid


class Command(BaseCommand):
    help = 'Configure Edge Server store identity'

    def add_arguments(self, parser):
        parser.add_argument('--outlet-id', type=str, help='Outlet UUID')
        parser.add_argument('--store-code', type=str, help='Store code (e.g., JKT-001)')
        parser.add_argument('--store-name', type=str, help='Store name')
        parser.add_argument('--interactive', action='store_true', help='Interactive mode')

    def handle(self, *args, **options):
        if options['interactive']:
            self.interactive_setup()
        else:
            self.command_setup(options)

    def interactive_setup(self):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('EDGE SERVER STORE CONFIGURATION'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')

        # Check if already configured
        if StoreConfig.objects.exists():
            config = StoreConfig.objects.first()
            self.stdout.write(self.style.WARNING('⚠️  Store already configured:'))
            self.stdout.write(f'   Company: {config.outlet.company.name}')
            self.stdout.write(f'   Outlet: {config.outlet.name}')
            self.stdout.write(f'   Store: {config.store_name} ({config.store_code})')
            self.stdout.write('')
            
            reconfigure = input('Reconfigure? (yes/no): ')
            if reconfigure.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Aborted.'))
                return
            config.delete()

        # List available outlets
        outlets = Outlet.objects.filter(is_active=True)
        if not outlets.exists():
            self.stdout.write(self.style.ERROR('❌ No active outlets found!'))
            self.stdout.write('   Please create outlet first via admin panel.')
            return

        self.stdout.write(self.style.SUCCESS('Available Outlets:'))
        for idx, outlet in enumerate(outlets, 1):
            self.stdout.write(f'   {idx}. {outlet.name} ({outlet.company.name})')
        self.stdout.write('')

        # Select outlet
        while True:
            try:
                choice = int(input('Select outlet number: '))
                outlet = list(outlets)[choice - 1]
                break
            except (ValueError, IndexError):
                self.stdout.write(self.style.ERROR('Invalid choice, try again.'))

        # Input store details
        store_code = input('Store code (e.g., JKT-001): ').strip()
        store_name = input('Store name (e.g., Senayan City): ').strip()

        # Create configuration
        config = StoreConfig.objects.create(
            outlet=outlet,
            store_code=store_code,
            store_name=store_name,
        )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('✅ STORE CONFIGURED SUCCESSFULLY'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'Company: {config.outlet.company.name}')
        self.stdout.write(f'Outlet: {config.outlet.name}')
        self.stdout.write(f'Store: {config.store_name} ({config.store_code})')
        self.stdout.write('')
        self.stdout.write('You can now register POS terminals at:')
        self.stdout.write('  http://127.0.0.1:8000/setup/terminal/')

    def command_setup(self, options):
        outlet_id = options.get('outlet_id')
        store_code = options.get('store_code')
        store_name = options.get('store_name')

        if not all([outlet_id, store_code, store_name]):
            self.stdout.write(self.style.ERROR('Missing required arguments'))
            self.stdout.write('Use --interactive for guided setup')
            return

        try:
            outlet = Outlet.objects.get(id=outlet_id)
        except Outlet.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Outlet {outlet_id} not found'))
            return

        config = StoreConfig.objects.create(
            outlet=outlet,
            store_code=store_code,
            store_name=store_name,
        )

        self.stdout.write(self.style.SUCCESS(f'Store configured: {config.store_name}'))
