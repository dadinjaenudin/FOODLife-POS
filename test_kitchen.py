"""
Quick test script to check kitchen orders
Run with: python test_kitchen.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_fnb.settings')
os.environ['USE_SQLITE'] = 'True'
os.environ['USE_LOCMEM_CACHE'] = 'True'
os.environ['USE_INMEMORY_CHANNEL'] = 'True'
os.environ['DEBUG'] = 'True'

django.setup()

from apps.kitchen.models import KitchenOrder
from apps.pos.models import Bill

# Check existing bills
bills = Bill.objects.filter(status='open')
print(f"Found {bills.count()} open bills")

# Check kitchen orders
orders = KitchenOrder.objects.all()
print(f"Found {orders.count()} kitchen orders")

for order in orders:
    print(f"  - {order.bill.bill_number} ({order.station}): {order.status}")
