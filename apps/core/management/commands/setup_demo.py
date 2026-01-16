from django.core.management.base import BaseCommand
from apps.core.models import User, Outlet, Category, Product


class Command(BaseCommand):
    help = 'Setup demo data for POS'

    def handle(self, *args, **options):
        # Create outlet
        outlet, _ = Outlet.objects.get_or_create(
            name='Demo Resto',
            defaults={
                'address': 'Jl. Demo No. 123, Jakarta',
                'phone': '021-1234567',
                'tax_rate': 11,
                'service_charge': 5,
                'receipt_footer': 'Terima Kasih Atas Kunjungan Anda!'
            }
        )
        self.stdout.write(f'Outlet: {outlet.name}')
        
        # Create admin user
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@demo.com',
                'role': 'admin',
                'outlet': outlet,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            self.stdout.write(f'Admin user created: admin / admin123')
        
        # Create cashier
        cashier, created = User.objects.get_or_create(
            username='kasir',
            defaults={
                'email': 'kasir@demo.com',
                'role': 'cashier',
                'outlet': outlet,
                'pin': '1234',
            }
        )
        if created:
            cashier.set_password('kasir123')
            cashier.save()
            self.stdout.write(f'Cashier created: kasir / kasir123 (PIN: 1234)')
        
        # Create categories
        categories_data = ['Makanan', 'Minuman', 'Snack', 'Dessert']
        categories = {}
        for name in categories_data:
            cat, _ = Category.objects.get_or_create(
                name=name,
                outlet=outlet,
            )
            categories[name] = cat
        self.stdout.write(f'Categories created: {len(categories)}')
        
        # Create products
        products_data = [
            ('Nasi Goreng Spesial', 'Makanan', 28000, 'kitchen'),
            ('Nasi Goreng Ayam', 'Makanan', 25000, 'kitchen'),
            ('Mie Goreng', 'Makanan', 23000, 'kitchen'),
            ('Mie Ayam Bakso', 'Makanan', 22000, 'kitchen'),
            ('Ayam Bakar', 'Makanan', 35000, 'kitchen'),
            ('Ayam Goreng', 'Makanan', 32000, 'kitchen'),
            ('Sate Ayam', 'Makanan', 30000, 'kitchen'),
            ('Es Teh Manis', 'Minuman', 8000, 'bar'),
            ('Es Jeruk', 'Minuman', 10000, 'bar'),
            ('Jus Jeruk', 'Minuman', 15000, 'bar'),
            ('Jus Alpukat', 'Minuman', 18000, 'bar'),
            ('Kopi Hitam', 'Minuman', 10000, 'bar'),
            ('Cappuccino', 'Minuman', 18000, 'bar'),
            ('Kentang Goreng', 'Snack', 18000, 'kitchen'),
            ('Pisang Goreng', 'Snack', 15000, 'kitchen'),
            ('Es Krim Coklat', 'Dessert', 15000, 'dessert'),
            ('Es Krim Vanilla', 'Dessert', 15000, 'dessert'),
            ('Pudding', 'Dessert', 12000, 'dessert'),
        ]
        
        for name, cat_name, price, printer in products_data:
            Product.objects.get_or_create(
                name=name,
                defaults={
                    'sku': name.upper().replace(' ', '_')[:20],
                    'category': categories[cat_name],
                    'price': price,
                    'printer_target': printer,
                }
            )
        self.stdout.write(f'Products created: {len(products_data)}')
        
        # Create table areas and tables
        from apps.tables.models import TableArea, Table
        
        areas_data = [
            ('Indoor', 10),
            ('Outdoor', 6),
            ('VIP', 4),
        ]
        
        for area_name, table_count in areas_data:
            area, _ = TableArea.objects.get_or_create(
                name=area_name,
                outlet=outlet,
            )
            for i in range(1, table_count + 1):
                Table.objects.get_or_create(
                    number=str(i),
                    area=area,
                    defaults={
                        'capacity': 4,
                    }
                )
        
        self.stdout.write(self.style.SUCCESS('Demo data created successfully!'))
        self.stdout.write('')
        self.stdout.write('Login credentials:')
        self.stdout.write('  Admin: admin / admin123')
        self.stdout.write('  Kasir: kasir / kasir123 (PIN: 1234)')
