"""
Test data generator for Recommendation Engine
Creates sample orders to demonstrate recommendation algorithms
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random

from apps.core.models import Product, Category, User
from apps.pos.models import Bill, BillItem
from apps.tables.models import Table


class Command(BaseCommand):
    help = 'Generate test data for recommendation engine'
    
    def handle(self, *args, **kwargs):
        self.stdout.write('Generating recommendation test data...')
        
        # Get first outlet's data
        table = Table.objects.first()
        if not table:
            self.stdout.write(self.style.ERROR('No tables found. Run setup_demo first.'))
            return
        
        outlet = table.area.outlet
        creator = User.objects.filter(role__in=['admin', 'manager', 'cashier']).first()
        
        if not creator:
            self.stdout.write(self.style.ERROR('No user found. Run setup_demo first.'))
            return
        
        # Get products
        products = list(Product.objects.filter(category__outlet=outlet, is_active=True))
        
        if len(products) < 5:
            self.stdout.write(self.style.ERROR('Need at least 5 products. Run setup_demo first.'))
            return
        
        self.stdout.write(f'Found {len(products)} products')
        
        # Define product combinations that are frequently bought together
        # This simulates real customer behavior
        combos = [
            # Combo 1: Nasi Goreng + Es Teh
            [0, 1],
            # Combo 2: Ayam Bakar + Juice
            [2, 3],
            # Combo 3: Nasi Goreng + Juice + Dessert
            [0, 3, 4],
            # Single items
            [1],
            [2],
            # Combo 4: Random pair
            [1, 4],
        ]
        
        # Generate 60 bills over last 60 days
        now = timezone.now()
        bills_created = 0
        
        for day in range(60):
            # Create 1-3 bills per day
            bills_per_day = random.randint(1, 3)
            
            for _ in range(bills_per_day):
                bill_date = now - timedelta(days=day, hours=random.randint(0, 23))
                
                # Create bill
                bill = Bill.objects.create(
                    outlet=outlet,
                    table=table,
                    created_by=creator,
                    status='paid',
                )
                # Update created_at manually
                bill.created_at = bill_date
                bill.save()
                
                # Choose a combo or random products
                if random.random() < 0.7:  # 70% use predefined combos
                    combo = random.choice(combos)
                    selected_products = [products[i % len(products)] for i in combo]
                else:  # 30% random selection
                    selected_products = random.sample(products, random.randint(1, 3))
                
                # Add items to bill
                for product in selected_products:
                    quantity = random.randint(1, 2)
                    BillItem.objects.create(
                        bill=bill,
                        product=product,
                        quantity=quantity,
                        unit_price=product.price,
                        created_by=creator,
                    )
                
                # Update bill total
                bill.calculate_totals()
                
                bills_created += 1
        
        # Create more recent orders to simulate trending
        # Last 7 days should have more of specific products
        trending_products = products[:2]  # First 2 products are "trending"
        
        for day in range(7):
            bills_per_day = random.randint(3, 5)  # More orders recently
            
            for _ in range(bills_per_day):
                bill_date = now - timedelta(days=day, hours=random.randint(0, 23))
                
                bill = Bill.objects.create(
                    outlet=outlet,
                    table=table,
                    created_by=creator,
                    status='paid',
                )
                # Update created_at manually
                bill.created_at = bill_date
                bill.save()
                
                # 60% chance to include a trending product
                if random.random() < 0.6:
                    trending = random.choice(trending_products)
                    quantity = random.randint(1, 3)
                    BillItem.objects.create(
                        bill=bill,
                        product=trending,
                        quantity=quantity,
                        unit_price=trending.price,
                        created_by=creator,
                    )
                
                # Add 1-2 more random items
                for product in random.sample(products, random.randint(1, 2)):
                    quantity = random.randint(1, 2)
                    BillItem.objects.create(
                        bill=bill,
                        product=product,
                        quantity=quantity,
                        unit_price=product.price,
                        created_by=creator,
                    )
                
                bill.calculate_totals()
                
                bills_created += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'✅ Successfully created {bills_created} bills with recommendation patterns'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'   - Products: {len(products)}'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'   - Trending items: {[p.name for p in trending_products]}'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'   - Date range: {(now - timedelta(days=60)).date()} to {now.date()}'
        ))
        self.stdout.write('')
        self.stdout.write('Now test the recommendation engine by:')
        self.stdout.write('1. Opening QR Order menu - see Popular Items & Trending')
        self.stdout.write('2. Adding items to cart - see Cart Recommendations')
        self.stdout.write('3. Opening product detail - see Frequently Bought Together')
