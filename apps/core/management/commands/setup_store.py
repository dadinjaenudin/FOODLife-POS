"""
Management command to configure Edge Server store identity
"""
from django.core.management.base import BaseCommand
from apps.core.models import Store, Brand
import uuid


class Command(BaseCommand):
    help = 'Configure Edge Server store identity'

    def add_arguments(self, parser):
        parser.add_argument('--Brand-id', type=str, help='Brand UUID')
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
        if Store.objects.exists():
            config = Store.objects.first()
            self.stdout.write(self.style.WARNING('⚠️  Store already configured:'))
            self.stdout.write(f'   Company: {config.Brand.company.name}')
            self.stdout.write(f'   Brand: {config.Brand.name}')
            self.stdout.write(f'   Store: {config.store_name} ({config.store_code})')
            self.stdout.write('')
            
            reconfigure = input('Reconfigure? (yes/no): ')
            if reconfigure.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Aborted.'))
                return
            config.delete()

        # List available brands
        brands = Brand.objects.filter(is_active=True)
        if not brands.exists():
            self.stdout.write(self.style.ERROR('❌ No active brands found!'))
            self.stdout.write('   Please create Brand first via admin panel.')
            return

        self.stdout.write(self.style.SUCCESS('Available brands:'))
        for idx, Brand in enumerate(brands, 1):
            self.stdout.write(f'   {idx}. {Brand.name} ({Brand.company.name})')
        self.stdout.write('')

        # Select Brand
        while True:
            try:
                choice = int(input('Select Brand number: '))
                Brand = list(brands)[choice - 1]
                break
            except (ValueError, IndexError):
                self.stdout.write(self.style.ERROR('Invalid choice, try again.'))

        # Input store details
        store_code = input('Store code (e.g., JKT-001): ').strip()
        store_name = input('Store name (e.g., Senayan City): ').strip()

        # Create configuration
        config = Store.objects.create(
            Brand=Brand,
            store_code=store_code,
            store_name=store_name,
        )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('✅ STORE CONFIGURED SUCCESSFULLY'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'Company: {config.Brand.company.name}')
        self.stdout.write(f'Brand: {config.Brand.name}')
        self.stdout.write(f'Store: {config.store_name} ({config.store_code})')
        self.stdout.write('')
        self.stdout.write('You can now register POS terminals at:')
        self.stdout.write('  http://127.0.0.1:8000/setup/terminal/')

    def command_setup(self, options):
        brand_id = options.get('brand_id')
        store_code = options.get('store_code')
        store_name = options.get('store_name')

        if not all([brand_id, store_code, store_name]):
            self.stdout.write(self.style.ERROR('Missing required arguments'))
            self.stdout.write('Use --interactive for guided setup')
            return

        try:
            Brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Brand {brand_id} not found'))
            return

        config = Store.objects.create(
            Brand=Brand,
            store_code=store_code,
            store_name=store_name,
        )

        self.stdout.write(self.style.SUCCESS(f'Store configured: {config.store_name}'))
