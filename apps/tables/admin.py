from django.contrib import admin
from .models import TableArea, Table, TableGroup


@admin.register(TableArea)
class TableAreaAdmin(admin.ModelAdmin):
    list_display = ['name', 'outlet', 'sort_order']
    list_filter = ['outlet']


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['number', 'area', 'capacity', 'status']
    list_filter = ['area', 'status']


@admin.register(TableGroup)
class TableGroupAdmin(admin.ModelAdmin):
    list_display = ['main_table', 'outlet', 'created_at']
