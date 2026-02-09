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
    path('terminals/create/', views.terminal_create, name='terminal_create'),
    path('terminals/<uuid:terminal_id>/', views.terminal_detail, name='terminal_detail'),
    path('terminals/<uuid:terminal_id>/edit/', views.terminal_edit, name='terminal_edit'),
    path('terminals/<uuid:terminal_id>/duplicate/', views.terminal_duplicate, name='terminal_duplicate'),
    path('terminals/<uuid:terminal_id>/deactivate/', views.terminal_deactivate, name='terminal_deactivate'),
    path('terminals/<uuid:terminal_id>/reactivate/', views.terminal_reactivate, name='terminal_reactivate'),
    path('terminals/<uuid:terminal_id>/delete/', views.terminal_delete, name='terminal_delete'),
    
    # Customer Display Config
    path('display-configs/', views.display_config_list, name='display_config_list'),
    path('display-configs/create/', views.display_config_create, name='display_config_create'),
    path('display-configs/<int:config_id>/edit/', views.display_config_edit, name='display_config_edit'),
    path('display-configs/<int:config_id>/delete/', views.display_config_delete, name='display_config_delete'),
    path('display-configs/<int:config_id>/toggle/', views.display_config_toggle, name='display_config_toggle'),
    
    # Receipt Templates
    path('receipt-templates/', views.receipt_template_list, name='receipt_template_list'),
    path('receipt-templates/create/', views.receipt_template_create, name='receipt_template_create'),
    path('receipt-templates/<int:template_id>/edit/', views.receipt_template_edit, name='receipt_template_edit'),
    path('receipt-templates/<int:template_id>/duplicate/', views.receipt_template_duplicate, name='receipt_template_duplicate'),
    path('receipt-templates/<int:template_id>/delete/', views.receipt_template_delete, name='receipt_template_delete'),
    path('receipt-templates/<int:template_id>/toggle/', views.receipt_template_toggle, name='receipt_template_toggle'),
    
    # Settings
    path('settings/', views.settings, name='settings'),
    path('settings/update/', views.settings_update, name='settings_update'),
    
    # Customer Display Slideshow
    path('customer-display/slides/', views.customer_display_slides, name='customer_display_slides'),
    path('customer-display/slides/upload/', views.customer_display_slide_upload, name='customer_display_slide_upload'),
    path('customer-display/slides/<int:slide_id>/update/', views.customer_display_slide_update, name='customer_display_slide_update'),
    path('customer-display/slides/<int:slide_id>/delete/', views.customer_display_slide_delete, name='customer_display_slide_delete'),
    path('customer-display/slides/<int:slide_id>/toggle/', views.customer_display_slide_toggle, name='customer_display_slide_toggle'),
    
    # Master Data
    path('master-data/', views.master_data, name='master_data'),
    path('master-data/sync-from-ho/', views.sync_from_ho, name='sync_from_ho'),
    path('sync-product-images/', views.sync_product_images, name='sync_product_images'),
    path('configure-bucket-policy/', views.configure_bucket_policy, name='configure_bucket_policy'),
    path('master-data/import-excel/', views.import_excel_page, name='import_excel'),
    path('master-data/import-excel/template/', views.download_excel_template, name='download_excel_template'),
    path('master-data/import-excel/reset/', views.import_excel_reset, name='import_excel_reset'),
    path('master-data/import-excel/process/', views.import_excel_process, name='import_excel_process'),
    path('master-data/import-condiment-groups/', views.import_condiment_groups, name='import_condiment_groups'),
    path('master-data/import-condiment-groups/template/', views.download_condiment_groups_template, name='download_condiment_groups_template'),
    path('master-data/import-condiment-groups/process/', views.import_condiment_groups_process, name='import_condiment_groups_process'),
    path('master-data/brands/', views.brands_list, name='brands'),
    path('master-data/categories/', views.categories, name='categories'),
    path('master-data/products/', views.products, name='products'),
    path('master-data/products/<uuid:product_id>/', views.product_detail, name='product_detail'),
    path('master-data/products/<uuid:product_id>/edit/', views.product_edit, name='product_edit'),
    path('master-data/products/set-stock-default/', views.products_set_stock_default, name='products_set_stock_default'),
    path('master-data/products/<uuid:product_id>/photos/', views.product_photos, name='product_photos'),
    path('master-data/products/<uuid:product_id>/photos/<uuid:photo_id>/toggle/', views.product_photo_toggle, name='product_photo_toggle'),
    path('master-data/products/<uuid:product_id>/photos/<uuid:photo_id>/delete/', views.product_photo_delete, name='product_photo_delete'),
    path('master-data/tables/', views.tables_list, name='tables'),
    path('master-data/table-areas/', views.table_areas_list, name='table_areas'),
    path('master-data/users/', views.users_list, name='users'),
    path('master-data/users/create/', views.user_create, name='user_create'),
    path('master-data/users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('master-data/users/<int:user_id>/delete/', views.user_delete, name='user_delete'),
    path('master-data/users/<int:user_id>/set-password/', views.user_set_password, name='user_set_password'),
    path('master-data/users/<int:user_id>/set-pin/', views.user_set_pin, name='user_set_pin'),
    path('master-data/promotions/', views.promotions_list, name='promotions'),
    path('master-data/promotions/<uuid:promotion_id>/', views.promotion_detail, name='promotion_detail'),
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
    
    # Session Management
    path('session/', views.session_management, name='session_open_form'),
    path('session/close/', views.session_close, name='session_close'),
]
