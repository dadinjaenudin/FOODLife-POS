from django.contrib import admin
from .models import Promotion, Voucher, BillPromotion


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ['name', 'promo_type', 'outlet', 'is_active', 'start_date', 'end_date']
    list_filter = ['outlet', 'promo_type', 'is_active']
    search_fields = ['name', 'code']


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = ['code', 'promotion', 'status', 'customer_name', 'created_at']
    list_filter = ['status', 'promotion']
    search_fields = ['code', 'customer_name', 'customer_phone']


@admin.register(BillPromotion)
class BillPromotionAdmin(admin.ModelAdmin):
    list_display = ['bill', 'promotion', 'discount_amount', 'applied_at']
