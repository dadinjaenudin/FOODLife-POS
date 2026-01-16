from django.contrib import admin
from .models import KitchenOrder, PrinterConfig


@admin.register(KitchenOrder)
class KitchenOrderAdmin(admin.ModelAdmin):
    list_display = ['bill', 'station', 'status', 'created_at']
    list_filter = ['station', 'status', 'created_at']


@admin.register(PrinterConfig)
class PrinterConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'outlet', 'station', 'connection_type', 'is_active']
    list_filter = ['outlet', 'station', 'is_active']
