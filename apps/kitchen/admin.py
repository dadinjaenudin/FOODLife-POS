from django.contrib import admin
from .models import KitchenOrder, PrinterConfig, KitchenStation, KitchenPerformance


@admin.register(KitchenOrder)
class KitchenOrderAdmin(admin.ModelAdmin):
    list_display = ['bill', 'station', 'status', 'priority', 'created_at', 'get_elapsed_minutes', 'is_overdue']
    list_filter = ['station', 'status', 'priority', 'created_at']
    readonly_fields = ['created_at', 'started_at', 'completed_at']
    
    def get_elapsed_minutes(self, obj):
        return f"{obj.get_elapsed_minutes()} min"
    get_elapsed_minutes.short_description = 'Elapsed'


@admin.register(KitchenStation)
class KitchenStationAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'outlet', 'target_prep_time', 'warning_threshold', 'is_active']
    list_filter = ['outlet', 'is_active']
    search_fields = ['name', 'code']


@admin.register(KitchenPerformance)
class KitchenPerformanceAdmin(admin.ModelAdmin):
    list_display = ['station', 'date', 'completed_orders', 'total_orders', 'get_avg_prep_minutes', 'overdue_orders']
    list_filter = ['station', 'date', 'outlet']
    readonly_fields = ['updated_at']
    
    def get_avg_prep_minutes(self, obj):
        return f"{obj.get_avg_prep_minutes():.1f} min"
    get_avg_prep_minutes.short_description = 'Avg Prep Time'


@admin.register(PrinterConfig)
class PrinterConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'outlet', 'station', 'connection_type', 'is_active']
    list_filter = ['outlet', 'station', 'is_active']
