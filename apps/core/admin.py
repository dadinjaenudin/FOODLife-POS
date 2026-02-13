from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Company, User, Brand, Store, StoreBrand, POSTerminal,
    Category, Product, Modifier, ModifierOption, ProductPhoto,
    Member, MemberTransaction,
    MediaGroup, PaymentMethodProfile, DataEntryPrompt,
)
from .models_session import CashierShift, CashDrop


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'timezone', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['code', 'name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'role_scope', 'brand', 'company', 'is_active']
    list_filter = ['role', 'role_scope', 'company', 'brand', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('POS Info', {'fields': ('role', 'role_scope', 'pin', 'company', 'brand')}),
    )


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'company', 'phone', 'tax_rate', 'service_charge', 'is_active']
    list_filter = ['company', 'is_active']
    search_fields = ['code', 'name', 'company__name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['store_code', 'store_name', 'company', 'get_brands', 'is_active', 'configured_at']
    list_filter = ['is_active', 'company']
    search_fields = ['store_code', 'store_name']
    readonly_fields = ['configured_at']
    fieldsets = (
        ('Store Information', {
            'fields': ('company', 'store_code', 'store_name', 'address', 'phone', 'timezone')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Branding', {
            'fields': ('login_image',),
            'description': 'Upload custom login page image (recommended size: 1080x1920 pixels)'
        }),
        ('Status', {
            'fields': ('is_active', 'configured_at')
        }),
    )
    
    def get_brands(self, obj):
        """Show brands in this store"""
        brands = obj.store_brands.filter(is_active=True).select_related('brand')
        return ', '.join([sb.brand.name for sb in brands]) if brands.exists() else '-'
    get_brands.short_description = 'Brands'
    
    def has_add_permission(self, request):
        # Only allow one store config
        return not Store.objects.exists()


@admin.register(StoreBrand)
class StoreBrandAdmin(admin.ModelAdmin):
    list_display = ['store', 'brand', 'ho_store_id', 'is_active', 'created_at']
    list_filter = ['is_active', 'brand']
    search_fields = ['store__store_name', 'brand__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(POSTerminal)
class POSTerminalAdmin(admin.ModelAdmin):
    list_display = ['terminal_code', 'terminal_name', 'device_type', 'ip_address', 'is_online', 'is_active', 'last_heartbeat']
    list_filter = ['device_type', 'is_active', 'store']
    search_fields = ['terminal_code', 'terminal_name', 'ip_address', 'mac_address']
    readonly_fields = ['id', 'registered_at', 'last_heartbeat', 'user_agent']
    
    def is_online(self, obj):
        return '🟢' if obj.is_online else '⚫'
    is_online.short_description = 'Status'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'sort_order', 'is_active']
    list_filter = ['brand', 'is_active']


class ProductPhotoInline(admin.TabularInline):
    model = ProductPhoto
    extra = 1
    fields = ['image', 'caption', 'order', 'is_active']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'category', 'price', 'printer_target', 'is_active']
    list_filter = ['category', 'printer_target', 'is_active']
    search_fields = ['name', 'sku']
    inlines = [ProductPhotoInline]


@admin.register(Modifier)
class ModifierAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'is_required', 'max_selections']


@admin.register(ModifierOption)
class ModifierOptionAdmin(admin.ModelAdmin):
    list_display = ['name', 'modifier', 'price_adjustment', 'is_default']


@admin.register(CashDrop)
class CashDropAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'created_at', 'cashier_shift', 'amount', 'reason', 'created_by', 'approved_by', 'receipt_printed']
    list_filter = ['reason', 'receipt_printed', 'created_at', 'company', 'brand', 'store']
    search_fields = ['receipt_number', 'created_by__username', 'notes']
    readonly_fields = ['id', 'receipt_number', 'created_at', 'printed_at', 'company', 'brand', 'store']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Transaction Info', {
            'fields': ('receipt_number', 'cashier_shift', 'amount', 'reason', 'notes')
        }),
        ('Multi-Tenant', {
            'fields': ('company', 'brand', 'store'),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': ('created_by', 'approved_by', 'created_at')
        }),
        ('Receipt', {
            'fields': ('receipt_printed', 'printed_at')
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('company', 'brand', 'store', 'cashier_shift', 'created_by', 'approved_by')
    
    def has_delete_permission(self, request, obj=None):
        # Only allow superuser to delete cash drops (audit trail)
        return request.user.is_superuser


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['member_code', 'full_name', 'phone', 'tier', 'points', 'total_visits', 'total_spent', 'is_active', 'joined_date']
    list_filter = ['tier', 'is_active', 'company', 'joined_date', 'gender']
    search_fields = ['member_code', 'full_name', 'phone', 'email', 'card_number']
    readonly_fields = ['id', 'member_code', 'total_visits', 'total_spent', 'last_visit', 'created_at', 'updated_at']
    date_hierarchy = 'joined_date'
    
    fieldsets = (
        ('Member Identity', {
            'fields': ('member_code', 'card_number', 'company')
        }),
        ('Personal Information', {
            'fields': ('full_name', 'email', 'phone', 'birth_date', 'gender')
        }),
        ('Address', {
            'fields': ('address', 'city', 'postal_code'),
            'classes': ('collapse',)
        }),
        ('Membership', {
            'fields': ('tier', 'joined_date', 'expire_date', 'is_active')
        }),
        ('Points & Balance', {
            'fields': ('points', 'point_balance')
        }),
        ('Statistics', {
            'fields': ('total_visits', 'total_spent', 'last_visit'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('company', 'created_by')


@admin.register(MemberTransaction)
class MemberTransactionAdmin(admin.ModelAdmin):
    list_display = ['member', 'transaction_type', 'points_change', 'balance_change', 'points_after', 'balance_after', 'created_at', 'bill']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['member__member_code', 'member__full_name', 'reference', 'notes']
    readonly_fields = ['id', 'created_at', 'points_before', 'points_after', 'balance_before', 'balance_after']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Transaction Info', {
            'fields': ('member', 'bill', 'transaction_type')
        }),
        ('Changes', {
            'fields': ('points_change', 'balance_change')
        }),
        ('Before/After', {
            'fields': ('points_before', 'points_after', 'balance_before', 'balance_after'),
            'classes': ('collapse',)
        }),
        ('Additional Info', {
            'fields': ('reference', 'notes', 'created_by', 'created_at')
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('member', 'bill', 'created_by')
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of transaction history
        return request.user.is_superuser


@admin.register(MediaGroup)
class MediaGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'company', 'orafin_group', 'sort_order', 'is_active']
    list_filter = ['company', 'is_active']
    search_fields = ['name', 'code']
    readonly_fields = ['id', 'created_at', 'updated_at']


class DataEntryPromptInline(admin.TabularInline):
    model = DataEntryPrompt
    extra = 1
    fields = ['field_name', 'label', 'field_type', 'min_length', 'max_length', 'placeholder', 'use_scanner', 'is_required', 'sort_order']


@admin.register(PaymentMethodProfile)
class PaymentMethodProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'company', 'brand', 'media_group', 'media_id', 'legacy_method_id', 'sort_order', 'is_active']
    list_filter = ['company', 'brand', 'media_group', 'is_active']
    search_fields = ['name', 'code']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [DataEntryPromptInline]
