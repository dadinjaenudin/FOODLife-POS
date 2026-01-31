"""
Data migration script to populate company_id and brand_id in Bill and BillItem

Run after migration 0003_add_company_denormalization.py

Purpose:
- Populate Bill.company_id from Bill.brand.company_id
- Populate BillItem.company_id and BillItem.brand_id from Bill

This ensures data consistency for denormalized fields.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.pos.models import Bill, BillItem


class Command(BaseCommand):
    help = 'Populate company_id in Bill and BillItem tables (denormalization)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without committing',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be saved\n'))
        
        # Populate Bill.company_id
        self.stdout.write('📊 Populating Bill.company_id...')
        bills_to_update = Bill.objects.filter(company__isnull=True).select_related('brand__company')
        
        bill_count = 0
        for bill in bills_to_update:
            bill.company = bill.brand.company
            if not dry_run:
                bill.save(update_fields=['company'])
            bill_count += 1
            
            if bill_count % 1000 == 0:
                self.stdout.write(f'  Processed {bill_count} bills...')
        
        self.stdout.write(self.style.SUCCESS(f'✅ Updated {bill_count} bills'))
        
        # Populate BillItem.company_id and BillItem.brand_id
        self.stdout.write('\n📊 Populating BillItem.company_id and brand_id...')
        items_to_update = BillItem.objects.filter(company__isnull=True).select_related('bill__company', 'bill__brand')
        
        item_count = 0
        for item in items_to_update:
            item.company = item.bill.company
            item.brand = item.bill.brand
            if not dry_run:
                item.save(update_fields=['company', 'brand'])
            item_count += 1
            
            if item_count % 5000 == 0:
                self.stdout.write(f'  Processed {item_count} items...')
        
        self.stdout.write(self.style.SUCCESS(f'✅ Updated {item_count} bill items'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY RUN COMPLETE - No changes saved'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ ALL DENORMALIZATION COMPLETE'))
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write('SUMMARY:')
        self.stdout.write(f'  Bills updated: {bill_count}')
        self.stdout.write(f'  Bill items updated: {item_count}')
        self.stdout.write('='*60)
