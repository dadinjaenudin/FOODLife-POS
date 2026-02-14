from django.contrib import admin
from .models import TableArea, Table, TableGroup
from .models_booking import (
    ReservationConfig, ReservationPackage, Reservation,
    ReservationDeposit, ReservationLog,
)


@admin.register(TableArea)
class TableAreaAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'sort_order']
    list_filter = ['brand']


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['number', 'area', 'capacity', 'status']
    list_filter = ['area', 'status']


@admin.register(TableGroup)
class TableGroupAdmin(admin.ModelAdmin):
    list_display = ['main_table', 'brand', 'created_at']


@admin.register(ReservationConfig)
class ReservationConfigAdmin(admin.ModelAdmin):
    list_display = ['store', 'is_booking_enabled', 'require_deposit', 'default_deposit_type']
    list_filter = ['is_booking_enabled', 'require_deposit']


@admin.register(ReservationPackage)
class ReservationPackageAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'min_pax', 'max_pax', 'price_per_pax', 'is_active']
    list_filter = ['brand', 'is_active']


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['reservation_code', 'guest_name', 'type', 'status', 'reservation_date', 'time_start', 'party_size', 'deposit_status']
    list_filter = ['status', 'type', 'reservation_date', 'brand']
    search_fields = ['reservation_code', 'guest_name', 'guest_phone']
    readonly_fields = ['reservation_code', 'created_at', 'updated_at']


@admin.register(ReservationDeposit)
class ReservationDepositAdmin(admin.ModelAdmin):
    list_display = ['reservation', 'amount', 'payment_method', 'status', 'paid_at']
    list_filter = ['status', 'payment_method']


@admin.register(ReservationLog)
class ReservationLogAdmin(admin.ModelAdmin):
    list_display = ['reservation', 'action', 'created_by', 'created_at']
    list_filter = ['action']
    readonly_fields = ['created_at']
