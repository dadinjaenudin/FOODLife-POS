from django.contrib import admin
from .models import Bill, BillItem, Payment, BillLog


class BillItemInline(admin.TabularInline):
    model = BillItem
    extra = 0
    readonly_fields = ['created_at', 'created_by']


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ['created_at', 'created_by']


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ['bill_number', 'outlet', 'table', 'bill_type', 'status', 'total', 'created_at']
    list_filter = ['outlet', 'status', 'bill_type', 'created_at']
    search_fields = ['bill_number', 'customer_name', 'customer_phone']
    inlines = [BillItemInline, PaymentInline]
    readonly_fields = ['bill_number', 'created_at', 'created_by']


@admin.register(BillLog)
class BillLogAdmin(admin.ModelAdmin):
    list_display = ['bill', 'action', 'user', 'created_at']
    list_filter = ['action', 'created_at']
