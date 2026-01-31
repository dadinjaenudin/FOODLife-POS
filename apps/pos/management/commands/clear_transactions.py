"""
Management command to clear all transaction data for testing
Usage: python manage.py clear_transactions
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.pos.models import Bill, BillItem, Payment, BillLog
from apps.kitchen.models import KitchenOrder
from apps.tables.models import Table


class Command(BaseCommand):
    help = 'Clear all transaction data (Bills, Payments, Kitchen Orders, Logs) for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        # Count existing data
        bills_count = Bill.objects.count()
        items_count = BillItem.objects.count()
        payments_count = Payment.objects.count()
        logs_count = BillLog.objects.count()
        kitchen_orders_count = KitchenOrder.objects.count()

        self.stdout.write(self.style.WARNING('=' * 60))
        self.stdout.write(self.style.WARNING('CLEAR TRANSACTION DATA'))
        self.stdout.write(self.style.WARNING('=' * 60))
        self.stdout.write(f'Bills: {bills_count}')
        self.stdout.write(f'Bill Items: {items_count}')
        self.stdout.write(f'Payments: {payments_count}')
        self.stdout.write(f'Bill Logs: {logs_count}')
        self.stdout.write(f'Kitchen Orders: {kitchen_orders_count}')
        self.stdout.write(self.style.WARNING('=' * 60))

        if bills_count == 0:
            self.stdout.write(self.style.SUCCESS('No transaction data to clear'))
            return

        # Confirmation
        if not options['yes']:
            confirm = input('Are you sure you want to delete ALL transaction data? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Operation cancelled'))
                return

        # Delete in transaction
        try:
            with transaction.atomic():
                # Clear kitchen orders first (FK to bills)
                KitchenOrder.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'✓ Deleted {kitchen_orders_count} kitchen orders'))

                # Clear payments (FK to bills)
                Payment.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'✓ Deleted {payments_count} payments'))

                # Clear bill logs (FK to bills)
                BillLog.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'✓ Deleted {logs_count} bill logs'))

                # Clear bill items (FK to bills)
                BillItem.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'✓ Deleted {items_count} bill items'))

                # Clear bills
                Bill.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'✓ Deleted {bills_count} bills'))

                # Reset table status
                Table.objects.update(status='available')
                self.stdout.write(self.style.SUCCESS('✓ Reset all table status to available'))

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write(self.style.SUCCESS('ALL TRANSACTION DATA CLEARED SUCCESSFULLY'))
            self.stdout.write(self.style.SUCCESS('=' * 60))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error clearing data: {str(e)}'))
            raise
