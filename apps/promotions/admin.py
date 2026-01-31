from django.contrib import admin
from .models import Promotion, PromotionUsage, PromotionSyncLog


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'promo_type', 'brand', 'is_active', 'start_date', 'end_date']
    list_filter = ['brand', 'promo_type', 'is_active', 'execution_stage']
    search_fields = ['name', 'code']
    readonly_fields = ['compiled_at', 'synced_at']


@admin.register(PromotionUsage)
class PromotionUsageAdmin(admin.ModelAdmin):
    list_display = ['promotion', 'transaction_id', 'discount_amount', 'usage_date', 'used_at']
    list_filter = ['usage_date', 'brand', 'store']
    search_fields = ['promotion__code', 'promotion__name', 'transaction_id']
    readonly_fields = ['used_at']


@admin.register(PromotionSyncLog)
class PromotionSyncLogAdmin(admin.ModelAdmin):
    list_display = ['sync_type', 'sync_status', 'promotions_received', 'promotions_added', 'promotions_updated', 'started_at', 'duration_seconds']
    list_filter = ['sync_status', 'sync_type', 'started_at']
    readonly_fields = ['started_at', 'completed_at', 'duration_seconds']
