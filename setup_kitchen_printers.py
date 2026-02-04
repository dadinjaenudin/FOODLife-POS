#!/usr/bin/env python
"""
Setup script for kitchen printer system
Creates StationPrinter entries for testing
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_fnb.settings')
django.setup()

from apps.kitchen.models import StationPrinter
from apps.core.models import Brand

def setup_printers():
    """Create sample printer configurations"""
    
    # Get the first brand (assuming at least one exists)
    try:
        brand = Brand.objects.first()
        if not brand:
            print("ERROR: No brands found in database. Please create a brand first.")
            return
    except Exception as e:
        print(f"ERROR: Could not get brand: {e}")
        return
    
    print(f"Using brand: {brand.name} (ID: {brand.id})\n")
    
    printers = [
        {
            'brand': brand,
            'station_code': 'kitchen',
            'printer_name': 'Main Kitchen Printer',
            'printer_ip': '192.168.1.101',
            'printer_port': 9100,
            'priority': 1,
            'is_active': True,
        },
        {
            'brand': brand,
            'station_code': 'bar',
            'printer_name': 'Bar Station Printer',
            'printer_ip': '192.168.1.102',
            'printer_port': 9100,
            'priority': 1,
            'is_active': True,
        },
        {
            'brand': brand,
            'station_code': 'dessert',
            'printer_name': 'Dessert Station Printer',
            'printer_ip': '192.168.1.103',
            'printer_port': 9100,
            'priority': 1,
            'is_active': True,
        },
        {
            'brand': brand,
            'station_code': 'kitchen',
            'printer_name': 'Kitchen Backup Printer',
            'printer_ip': '192.168.1.111',
            'printer_port': 9100,
            'priority': 2,  # Backup printer
            'is_active': True,
        },
    ]
    
    created = 0
    updated = 0
    
    for printer_data in printers:
        printer, is_created = StationPrinter.objects.update_or_create(
            brand=printer_data['brand'],
            station_code=printer_data['station_code'],
            printer_ip=printer_data['printer_ip'],
            defaults=printer_data
        )
        
        if is_created:
            created += 1
            print(f"✓ Created: {printer.printer_name} ({printer.station_code}) → {printer.printer_ip}:{printer.printer_port}")
        else:
            updated += 1
            print(f"⟳ Updated: {printer.printer_name} ({printer.station_code}) → {printer.printer_ip}:{printer.printer_port}")
    
    print(f"\nSummary:")
    print(f"  Created: {created}")
    print(f"  Updated: {updated}")
    print(f"  Total:   {StationPrinter.objects.count()}")

if __name__ == '__main__':
    print("Setting up kitchen printers...\n")
    setup_printers()
