from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Outlet, Category, Product, Modifier, ModifierOption


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'outlet', 'is_active']
    list_filter = ['role', 'outlet', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('POS Info', {'fields': ('role', 'pin', 'outlet')}),
    )


@admin.register(Outlet)
class OutletAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'tax_rate', 'service_charge']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'outlet', 'sort_order', 'is_active']
    list_filter = ['outlet', 'is_active']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'category', 'price', 'printer_target', 'is_active']
    list_filter = ['category', 'printer_target', 'is_active']
    search_fields = ['name', 'sku']


@admin.register(Modifier)
class ModifierAdmin(admin.ModelAdmin):
    list_display = ['name', 'outlet', 'is_required', 'max_selections']


@admin.register(ModifierOption)
class ModifierOptionAdmin(admin.ModelAdmin):
    list_display = ['name', 'modifier', 'price_adjustment', 'is_default']
