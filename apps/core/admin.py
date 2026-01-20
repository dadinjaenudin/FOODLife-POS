from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Company, User, Outlet, StoreConfig, POSTerminal, Category, Product, Modifier, ModifierOption, ProductPhoto


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'timezone', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['code', 'name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'outlet', 'company', 'is_active']
    list_filter = ['role', 'company', 'outlet', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('POS Info', {'fields': ('role', 'pin', 'company', 'outlet')}),
    )


@admin.register(Outlet)
class OutletAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'company', 'phone', 'tax_rate', 'service_charge', 'is_active']
    list_filter = ['company', 'is_active']
    search_fields = ['code', 'name', 'company__name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(StoreConfig)
class StoreConfigAdmin(admin.ModelAdmin):
    list_display = ['store_code', 'store_name', 'outlet', 'is_active', 'configured_at']
    readonly_fields = ['configured_at']
    fieldsets = (
        ('Store Information', {
            'fields': ('outlet', 'store_code', 'store_name', 'address', 'phone', 'timezone')
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
    
    def has_add_permission(self, request):
        # Only allow one store config
        return not StoreConfig.objects.exists()


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
    list_display = ['name', 'outlet', 'sort_order', 'is_active']
    list_filter = ['outlet', 'is_active']


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
    list_display = ['name', 'outlet', 'is_required', 'max_selections']


@admin.register(ModifierOption)
class ModifierOptionAdmin(admin.ModelAdmin):
    list_display = ['name', 'modifier', 'price_adjustment', 'is_default']
