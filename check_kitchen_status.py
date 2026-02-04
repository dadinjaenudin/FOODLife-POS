#!/usr/bin/env python
"""Check kitchen printer system status"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_fnb.settings')
django.setup()

from apps.kitchen.models import *
from apps.pos.models import *
from apps.core.models import Product

print('=== Kitchen Printer System Status ===\n')

print(f'StationPrinters: {StationPrinter.objects.count()}')
for p in StationPrinter.objects.all():
    print(f'  - {p}')

print(f'\nKitchenTickets: {KitchenTicket.objects.count()}')
print(f'Bills in system: {Bill.objects.count()}')

print(f'\nProducts with printer_target:')
targets = Product.objects.exclude(printer_target__in=['', 'none']).values_list('printer_target', flat=True).distinct()
for pt in targets[:5]:
    count = Product.objects.filter(printer_target=pt).count()
    print(f'  - {pt}: {count} products')
