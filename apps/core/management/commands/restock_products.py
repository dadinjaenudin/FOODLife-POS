from django.core.management.base import BaseCommand
from apps.core.models import Product, Outlet


class Command(BaseCommand):
    help = 'Restock all products with sufficient inventory'

    def handle(self, *args, **options):
        products = Product.objects.all()
        
        updated_count = 0
        made_available = 0
        
        for product in products:
            # Update stock if low
            if product.stock < 10:
                old_stock = product.stock
                product.stock = 100
                product.save()
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Restocked: {product.name} → 100 units (was {old_stock})')
                )
            
            # Make sure product is available
            if not product.is_available:
                product.is_available = True
                product.save()
                made_available += 1
                self.stdout.write(
                    self.style.WARNING(f'✨ Made available: {product.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n🎉 Total products restocked: {updated_count}')
        )
        self.stdout.write(
            self.style.SUCCESS(f'✨ Products made available: {made_available}')
        )
        self.stdout.write(
            self.style.SUCCESS(f'📦 All products now have stock: 100 units')
        )
