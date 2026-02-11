from django.contrib import admin
from .models import Bill, BillItem, Payment, BillLog, StoreProductStock
from .models_refund import BillRefund, BillRefundItem, RefundPaymentReversal


class BillItemInline(admin.TabularInline):
    model = BillItem
    extra = 0
    readonly_fields = ['created_at', 'created_by']


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ['created_at', 'created_by']


class BillRefundItemInline(admin.TabularInline):
    model = BillRefundItem
    extra = 0
    readonly_fields = ['original_quantity', 'unit_price', 'refund_amount']


class RefundPaymentReversalInline(admin.TabularInline):
    model = RefundPaymentReversal
    extra = 0
    readonly_fields = ['processed_at', 'processed_by']


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ['bill_number', 'brand', 'table', 'bill_type', 'status', 'total', 'created_at']
    list_filter = ['brand', 'status', 'bill_type', 'created_at']
    search_fields = ['bill_number', 'customer_name', 'customer_phone']
    inlines = [BillItemInline, PaymentInline]
    readonly_fields = ['bill_number', 'created_at', 'created_by']


@admin.register(BillLog)
class BillLogAdmin(admin.ModelAdmin):
    list_display = ['bill', 'action', 'user', 'created_at']
    list_filter = ['action', 'created_at']


@admin.register(BillRefund)
class BillRefundAdmin(admin.ModelAdmin):
    list_display = ['refund_number', 'original_bill', 'refund_type', 'reason', 'status', 'refund_total', 'requested_at']
    list_filter = ['status', 'refund_type', 'reason', 'requested_at']
    search_fields = ['refund_number', 'original_bill__bill_number']
    inlines = [BillRefundItemInline, RefundPaymentReversalInline]
    readonly_fields = ['refund_number', 'requested_at', 'requested_by', 'approved_at', 'completed_at']
    
    fieldsets = (
        ('Refund Information', {
            'fields': ('refund_number', 'original_bill', 'refund_type', 'reason', 'reason_notes', 'status')
        }),
        ('Financial', {
            'fields': ('original_total', 'refund_subtotal', 'refund_tax', 'refund_service_charge', 'refund_total')
        }),
        ('Approval', {
            'fields': ('requested_by', 'requested_at', 'approved_by', 'approval_pin', 'approval_notes', 'approved_at')
        }),
        ('Completion', {
            'fields': ('completed_by', 'completed_at', 'original_payments', 'refund_payments')
        }),
    )


@admin.register(StoreProductStock)
class StoreProductStockAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'product_sku', 'brand', 'daily_stock', 'sold_qty', 'get_remaining', 'is_active', 'last_reset_date']
    list_filter = ['brand', 'is_active', 'last_reset_date']
    search_fields = ['product_name', 'product_sku']
    readonly_fields = ['product_id', 'created_at', 'updated_at']

    def get_remaining(self, obj):
        return obj.remaining_stock
    get_remaining.short_description = 'Remaining'
