from django.core.management.base import BaseCommand
from apps.kitchen.models import StationPrinter
from apps.core.models import Brand


class Command(BaseCommand):
    help = 'Setup default station printers (kitchen, bar, dessert)'

    def handle(self, *args, **options):
        # Get first available brand
        brand = Brand.objects.first()
        if not brand:
            self.stdout.write(self.style.ERROR(
                'No Brand found in database. Please create a Brand first.'
            ))
            return
        
        printers = [
            {
                'brand': brand,
                'station_code': 'kitchen',
                'printer_name': 'Main Kitchen Printer',
                'printer_ip': '192.168.1.100',
                'printer_port': 9100,
                'priority': 1,
                'is_active': True,
                'paper_width_mm': 80,
                'chars_per_line': 32,
                'printer_brand': 'HRPT',
                'printer_type': 'network',
                'timeout_seconds': 5,
            },
            {
                'brand': brand,
                'station_code': 'bar',
                'printer_name': 'Bar Station Printer',
                'printer_ip': '192.168.1.101',
                'printer_port': 9100,
                'priority': 1,
                'is_active': True,
                'paper_width_mm': 80,
                'chars_per_line': 32,
                'printer_brand': 'HRPT',
                'printer_type': 'network',
                'timeout_seconds': 5,
            },
            {
                'brand': brand,
                'station_code': 'dessert',
                'printer_name': 'Dessert Station Printer',
                'printer_ip': '192.168.1.102',
                'printer_port': 9100,
                'priority': 1,
                'is_active': True,
                'paper_width_mm': 80,
                'chars_per_line': 32,
                'printer_brand': 'HRPT',
                'printer_type': 'network',
                'timeout_seconds': 5,
            },
        ]
        
        created_count = 0
        for printer_data in printers:
            printer, created = StationPrinter.objects.get_or_create(
                brand=printer_data['brand'],
                station_code=printer_data['station_code'],
                defaults=printer_data
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f"Created printer: {printer.station_code} ({printer.printer_ip})"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"Printer already exists: {printer.station_code}"
                ))
        
        if created_count > 0:
            self.stdout.write(self.style.SUCCESS(
                f"\nSuccessfully created {created_count} default printer(s)."
            ))
        else:
            self.stdout.write(self.style.WARNING(
                "\nNo new printers created (all already exist)."
            ))
