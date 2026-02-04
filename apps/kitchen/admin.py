from django.contrib import admin
from .models import (
    KitchenOrder, PrinterConfig, KitchenStation, KitchenPerformance,
    KitchenTicket, KitchenTicketItem, StationPrinter,
    KitchenTicketLog, PrinterHealthCheck
)


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
    list_display = ['name', 'code', 'brand', 'target_prep_time', 'warning_threshold', 'is_active']
    list_filter = ['brand', 'is_active']
    search_fields = ['name', 'code']


@admin.register(KitchenPerformance)
class KitchenPerformanceAdmin(admin.ModelAdmin):
    list_display = ['station', 'date', 'completed_orders', 'total_orders', 'get_avg_prep_minutes', 'overdue_orders']
    list_filter = ['station', 'date', 'brand']
    readonly_fields = ['updated_at']
    
    def get_avg_prep_minutes(self, obj):
        return f"{obj.get_avg_prep_minutes():.1f} min"
    get_avg_prep_minutes.short_description = 'Avg Prep Time'


@admin.register(PrinterConfig)
class PrinterConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'station', 'connection_type', 'is_active']
    list_filter = ['brand', 'station', 'is_active']


# ============================================================================
# KITCHEN PRINTER SERVICE ADMIN
# ============================================================================

class KitchenTicketItemInline(admin.TabularInline):
    model = KitchenTicketItem
    extra = 0
    readonly_fields = ['bill_item', 'quantity']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(KitchenTicket)
class KitchenTicketAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'bill', 'printer_target', 'status', 'print_attempts', 
        'printer_ip', 'created_at', 'printed_at', 'is_reprint'
    ]
    list_filter = ['status', 'printer_target', 'is_reprint', 'created_at']
    search_fields = ['bill__bill_number', 'printer_ip']
    readonly_fields = [
        'created_at', 'printed_at', 'last_error_at', 'print_attempts',
        'error_message', 'original_ticket'
    ]
    inlines = [KitchenTicketItemInline]
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('bill', 'printer_target', 'status')
        }),
        ('Print Details', {
            'fields': ('printer_ip', 'print_attempts', 'max_retries', 'is_reprint', 'original_ticket')
        }),
        ('Error Tracking', {
            'fields': ('error_message', 'last_error_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'printed_at')
        }),
    )
    
    actions = ['mark_as_new', 'mark_as_failed']
    
    def mark_as_new(self, request, queryset):
        """Reset tickets to NEW status for retry"""
        count = queryset.filter(status__in=['failed', 'printed']).update(
            status='new',
            error_message='',
            printer_ip=None
        )
        self.message_user(request, f"{count} ticket(s) marked as NEW for reprint")
    mark_as_new.short_description = "🔄 Reset to NEW (Reprint)"
    
    def mark_as_failed(self, request, queryset):
        """Mark tickets as failed"""
        count = queryset.update(status='failed')
        self.message_user(request, f"{count} ticket(s) marked as FAILED")
    mark_as_failed.short_description = "❌ Mark as FAILED"


@admin.register(StationPrinter)
class StationPrinterAdmin(admin.ModelAdmin):
    list_display = [
        'station_code', 'printer_name', 'printer_ip', 'printer_port',
        'priority', 'is_active', 'get_success_rate', 'total_prints', 'failed_prints'
    ]
    list_filter = ['brand', 'station_code', 'is_active', 'priority']
    search_fields = ['station_code', 'printer_name', 'printer_ip']
    readonly_fields = [
        'last_print_at', 'last_error_at', 'last_error_message',
        'total_prints', 'failed_prints', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Station & Printer Info', {
            'fields': ('brand', 'station_code', 'printer_name')
        }),
        ('Network Configuration', {
            'fields': ('printer_ip', 'printer_port', 'is_active', 'priority')
        }),
        ('Printer Specifications', {
            'fields': ('paper_width_mm', 'chars_per_line')
        }),
        ('Statistics', {
            'fields': ('total_prints', 'failed_prints', 'last_print_at'),
            'classes': ('collapse',)
        }),
        ('Error Tracking', {
            'fields': ('last_error_at', 'last_error_message'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_success_rate(self, obj):
        rate = obj.get_success_rate()
        color = 'green' if rate >= 95 else 'orange' if rate >= 80 else 'red'
        return f"<span style='color: {color}; font-weight: bold;'>{rate:.1f}%</span>"
    get_success_rate.short_description = 'Success Rate'
    get_success_rate.allow_tags = True
    
    actions = ['run_health_check']
    
    def run_health_check(self, request, queryset):
        """Run health check on selected printers"""
        from .models import PrinterHealthCheck
        
        checked_count = 0
        online_count = 0
        
        for printer in queryset.filter(is_active=True):
            health = PrinterHealthCheck.check_printer(printer)
            checked_count += 1
            if health.is_online:
                online_count += 1
        
        self.message_user(
            request, 
            f"Checked {checked_count} printer(s). {online_count} online, {checked_count - online_count} offline."
        )
    run_health_check.short_description = "🔍 Run Health Check"


@admin.register(KitchenTicketLog)
class KitchenTicketLogAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'ticket', 'action', 'actor', 'old_status', 'new_status', 
        'printer_ip', 'duration_ms', 'timestamp'
    ]
    list_filter = ['action', 'old_status', 'new_status', 'timestamp']
    search_fields = ['ticket__id', 'ticket__bill__bill_number', 'actor', 'error_message']
    readonly_fields = [
        'ticket', 'timestamp', 'old_status', 'new_status', 'action', 'actor',
        'printer_ip', 'error_code', 'error_message', 'duration_ms', 'metadata'
    ]
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('ticket', 'timestamp', 'action', 'actor')
        }),
        ('State Change', {
            'fields': ('old_status', 'new_status')
        }),
        ('Technical Details', {
            'fields': ('printer_ip', 'duration_ms')
        }),
        ('Error Info', {
            'fields': ('error_code', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Additional Context', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Prevent manual creation - logs are auto-generated only"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion - audit logs must be immutable"""
        return False


@admin.register(PrinterHealthCheck)
class PrinterHealthCheckAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'printer', 'checked_at', 'get_status', 'response_time_ms',
        'paper_status', 'get_health_indicator'
    ]
    list_filter = ['is_online', 'paper_status', 'checked_at', 'printer__station_code']
    search_fields = ['printer__printer_name', 'printer__printer_ip', 'error_message']
    readonly_fields = [
        'printer', 'checked_at', 'is_online', 'response_time_ms',
        'paper_status', 'error_code', 'error_message',
        'temperature_ok', 'cutter_ok'
    ]
    
    fieldsets = (
        ('Check Info', {
            'fields': ('printer', 'checked_at')
        }),
        ('Connection Status', {
            'fields': ('is_online', 'response_time_ms')
        }),
        ('Printer Status', {
            'fields': ('paper_status', 'temperature_ok', 'cutter_ok')
        }),
        ('Error Details', {
            'fields': ('error_code', 'error_message'),
            'classes': ('collapse',)
        }),
    )
    
    def get_status(self, obj):
        if obj.is_online:
            return "✅ Online"
        return "❌ Offline"
    get_status.short_description = 'Status'
    
    def get_health_indicator(self, obj):
        if obj.is_healthy():
            return "🟢 Healthy"
        elif obj.is_online:
            return "🟡 Issues"
        return "🔴 Down"
    get_health_indicator.short_description = 'Health'
    
    def has_add_permission(self, request):
        """Prevent manual creation - health checks are auto-generated"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion of old health check records for cleanup"""
        return request.user.is_superuser
