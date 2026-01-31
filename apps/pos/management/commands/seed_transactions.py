"""
Management command to seed sample transaction data for testing
Usage: python manage.py seed_transactions
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import random
from datetime import timedelta

from apps.core.models import User, Brand, Product
from apps.pos.models import Bill, BillItem, Payment
from apps.tables.models import Table
from apps.kitchen.services import create_kitchen_order
from collections import defaultdict


class Command(BaseCommand):
    help = 'Seed sample transaction data for testing POS & KDS'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of bills to create (default: 10)',
        )

    def handle(self, *args, **options):
        count = options['count']

        self.stdout.write(self.style.WARNING('=' * 60))
        self.stdout.write(self.style.WARNING('SEED TRANSACTION DATA'))
        self.stdout.write(self.style.WARNING('=' * 60))

        try:
            # Get required data
            Brand = Brand.objects.first()
            if not Brand:
                self.stdout.write(self.style.ERROR('No Brand found. Run setup_demo first.'))
                return

            users = list(User.objects.filter(Brand=Brand))
            if not users:
                self.stdout.write(self.style.ERROR('No users found. Run setup_demo first.'))
                return

            tables = list(Table.objects.filter(area__brand=Brand))
            products = list(Product.objects.filter(is_active=True))

            if not products:
                self.stdout.write(self.style.ERROR('No products found. Run setup_demo first.'))
                return

            # Create bills
            bills_created = 0
            items_created = 0
            kitchen_orders_created = 0

            for i in range(count):
                with transaction.atomic():
                    # Randomize bill scenario
                    scenario = random.choice(['dine_in', 'dine_in_paid', 'takeaway', 'hold'])
                    user = random.choice(users)

                    # Create bill
                    bill = Bill.objects.create(
                        Brand=Brand,
                        bill_number=f'SEED-{timezone.now().strftime("%Y%m%d")}-{i+1:04d}',
                        bill_type='dine_in' if scenario in ['dine_in', 'dine_in_paid', 'hold'] else 'takeaway',
                        status='paid' if scenario == 'dine_in_paid' else ('hold' if scenario == 'hold' else 'open'),
                        guest_count=random.randint(1, 6),
                        created_by=user,
                    )

                    # Assign table for dine-in
                    if scenario in ['dine_in', 'dine_in_paid'] and tables:
                        table = random.choice(tables)
                        bill.table = table
                        table.status = 'occupied'
                        table.save()
                        bill.save()

                    # Add random items (2-5 items)
                    num_items = random.randint(2, 5)
                    selected_products = random.sample(products, min(num_items, len(products)))

                    for product in selected_products:
                        quantity = random.randint(1, 3)
                        item = BillItem.objects.create(
                            bill=bill,
                            product=product,
                            quantity=quantity,
                            unit_price=product.price,
                            status='sent' if scenario != 'hold' else 'pending',
                            created_by=user
                        )
                        items_created += 1

                    # Calculate totals
                    bill.calculate_totals()

                    # Send to kitchen if not hold
                    if scenario != 'hold':
                        grouped = defaultdict(list)
                        for item in bill.items.filter(status='sent'):
                            grouped[item.product.printer_target].append(item)

                        for station, station_items in grouped.items():
                            if station != 'none':
                                create_kitchen_order(bill, station, station_items)
                                kitchen_orders_created += 1

                    # Add payment if paid
                    if scenario == 'dine_in_paid':
                        Payment.objects.create(
                            bill=bill,
                            method='cash',
                            amount=bill.total,
                            created_by=user,
                        )
                        if bill.table:
                            bill.table.status = 'available'
                            bill.table.save()

                    bills_created += 1

                    # Status indicator
                    status_icon = '💰' if scenario == 'dine_in_paid' else '⏸️' if scenario == 'hold' else '🍽️'
                    self.stdout.write(f'{status_icon} Bill {i+1}/{count}: {bill.bill_number} ({bill.items.count()} items)')

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write(self.style.SUCCESS('TRANSACTION DATA SEEDED SUCCESSFULLY'))
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write(self.style.SUCCESS(f'Bills created: {bills_created}'))
            self.stdout.write(self.style.SUCCESS(f'Items created: {items_created}'))
            self.stdout.write(self.style.SUCCESS(f'Kitchen orders created: {kitchen_orders_created}'))
            self.stdout.write('')
            self.stdout.write('Scenarios created:')
            self.stdout.write(f'  🍽️  Dine-in (open): Random')
            self.stdout.write(f'  💰 Dine-in (paid): Random')
            self.stdout.write(f'  🥡 Take Away: Random')
            self.stdout.write(f'  ⏸️  Hold: Random')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error seeding data: {str(e)}'))
            raise
