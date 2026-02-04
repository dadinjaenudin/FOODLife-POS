#!/usr/bin/env python
"""Show kitchen printer system status"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_fnb.settings')
django.setup()

from apps.kitchen.models import *

print('\n' + '='*50)
print('    KITCHEN PRINTER SYSTEM STATUS')
print('='*50 + '\n')

print('📊 Database Tables:')
print(f'   ✓ StationPrinter: {StationPrinter.objects.count()} printers')
print(f'   ✓ KitchenTicket: {KitchenTicket.objects.count()} tickets')
print(f'   ✓ KitchenTicketItem: {KitchenTicketItem.objects.count()} items')
print(f'   ✓ KitchenTicketLog: {KitchenTicketLog.objects.count()} logs')

print(f'\n📍 Printer Configuration:')
for p in StationPrinter.objects.all():
    status = '🟢' if p.is_active else '🔴'
    print(f'   {status} {p.station_code.upper()}: {p.printer_ip}:{p.printer_port} (priority {p.priority})')

print(f'\n🎫 Recent Tickets:')
if KitchenTicket.objects.count() > 0:
    for t in KitchenTicket.objects.all()[:5]:
        print(f'   #{t.id}: {t.printer_target.upper()} - {t.status.upper()} ({t.items.count()} items)')
else:
    print('   (No tickets yet)')

print(f'\n✅ System Status: READY FOR TESTING')
print('\nNext: Test dari POS dengan click "Send to Kitchen"')
print('URL: http://localhost:8001/pos/')
print()
