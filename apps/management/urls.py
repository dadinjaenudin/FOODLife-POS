"""
Management Interface URLs
"""
from django.urls import path
from . import views

app_name = 'management'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('dashboard/refresh/', views.dashboard_refresh, name='dashboard_refresh'),
    
    # Terminals
    path('terminals/', views.terminals_list, name='terminals'),
    path('terminals/<uuid:terminal_id>/', views.terminal_detail, name='terminal_detail'),
    path('terminals/<uuid:terminal_id>/deactivate/', views.terminal_deactivate, name='terminal_deactivate'),
    path('terminals/<uuid:terminal_id>/reactivate/', views.terminal_reactivate, name='terminal_reactivate'),
    
    # Settings
    path('settings/', views.settings, name='settings'),
    path('settings/update/', views.settings_update, name='settings_update'),
    
    # Master Data
    path('master-data/', views.master_data, name='master_data'),
    path('master-data/import-excel/', views.import_excel_page, name='import_excel'),
    path('master-data/import-excel/template/', views.download_excel_template, name='download_excel_template'),
    path('master-data/import-excel/reset/', views.import_excel_reset, name='import_excel_reset'),
    path('master-data/import-excel/process/', views.import_excel_process, name='import_excel_process'),
    path('master-data/import-condiment-groups/', views.import_condiment_groups, name='import_condiment_groups'),
    path('master-data/import-condiment-groups/template/', views.download_condiment_groups_template, name='download_condiment_groups_template'),
    path('master-data/import-condiment-groups/process/', views.import_condiment_groups_process, name='import_condiment_groups_process'),
    path('master-data/categories/', views.categories, name='categories'),
    path('master-data/products/', views.products, name='products'),
    path('master-data/products/<int:product_id>/', views.product_detail, name='product_detail'),
    path('master-data/products/<int:product_id>/edit/', views.product_edit, name='product_edit'),
    path('master-data/products/<int:product_id>/photos/', views.product_photos, name='product_photos'),
    path('master-data/products/<int:product_id>/photos/<int:photo_id>/toggle/', views.product_photo_toggle, name='product_photo_toggle'),
    path('master-data/products/<int:product_id>/photos/<int:photo_id>/delete/', views.product_photo_delete, name='product_photo_delete'),
    path('master-data/tables/', views.tables_list, name='tables'),
    path('master-data/table-areas/', views.table_areas_list, name='table_areas'),
    path('master-data/users/', views.users_list, name='users'),
    path('master-data/users/<int:user_id>/set-password/', views.user_set_password, name='user_set_password'),
    path('master-data/users/<int:user_id>/set-pin/', views.user_set_pin, name='user_set_pin'),
    path('master-data/promotions/', views.promotions_list, name='promotions'),
    path('master-data/vouchers/', views.vouchers_list, name='vouchers'),
    
    # Transaction Data
    path('transactions/bills/', views.bills_list, name='bills'),
    path('transactions/payments/', views.payments_list, name='payments'),
    path('transactions/sessions/', views.store_sessions_list, name='store_sessions'),
    
    # Reports & Analytics
    path('reports/', views.reports_dashboard, name='reports'),
    path('reports/sales/', views.sales_report, name='sales_report'),
    path('reports/products/', views.products_report, name='products_report'),
    path('reports/cashier/', views.cashier_report, name='cashier_report'),
    path('reports/payment/', views.payment_report, name='payment_report'),
    path('reports/void-discount/', views.void_discount_report, name='void_discount_report'),
    path('reports/peak-hours/', views.peak_hours_report, name='peak_hours_report'),
    path('reports/export/sales-excel/', views.export_sales_excel, name='export_sales_excel'),
]
