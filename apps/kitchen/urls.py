from django.urls import path
from . import views

app_name = 'kitchen'

urlpatterns = [
    # Kitchen Display System (KDS)
    path('kds/', views.kds_screen, name='kds'),
    path('kds/orders/', views.kds_orders, name='kds_orders_default'),
    path('kds/<str:station>/', views.kds_screen, name='kds_station'),
    path('kds/<str:station>/orders/', views.kds_orders, name='kds_orders'),
    path('order/<int:order_id>/start/', views.kds_start, name='kds_start'),
    path('order/<int:order_id>/ready/', views.kds_ready, name='kds_ready'),
    path('order/<int:order_id>/bump/', views.kds_bump, name='kds_bump'),
    path('order/<int:order_id>/priority/', views.set_priority, name='set_priority'),
    
    # Performance & Monitoring (Legacy KDS)
    path('performance/<str:station>/', views.performance_metrics, name='performance_metrics'),
    path('overdue/<str:station>/', views.check_overdue_orders, name='check_overdue'),
    
    path('printers/', views.printer_list, name='printer_list'),
    path('printers/test/<int:printer_id>/', views.test_printer, name='test_printer'),
    
    # Kitchen Printer System Monitoring
    path('dashboard/', views.kitchen_dashboard, name='dashboard'),
    path('tickets/', views.kitchen_tickets, name='tickets'),
    path('tickets/clear/', views.kitchen_tickets_clear_all, name='tickets_clear_all'),
    path('tickets/<int:ticket_id>/', views.kitchen_ticket_detail, name='ticket_detail'),
    path('tickets/<int:ticket_id>/reprint/', views.ticket_reprint, name='ticket_reprint'),
    path('printer-status/', views.kitchen_printers, name='printers'),
    path('logs/', views.kitchen_logs, name='logs'),
    path('logs/purge/', views.kitchen_logs_purge, name='logs_purge'),
    path('logs/clear/', views.kitchen_logs_clear_all, name='logs_clear_all'),
    
    # Station Printer CRUD
    path('printers/manage/', views.printer_list_manage, name='printer_manage'),
    path('printers/create/', views.printer_create, name='printer_create'),
    path('printers/<int:printer_id>/edit/', views.printer_edit, name='printer_edit'),
    path('printers/<int:printer_id>/delete/', views.printer_delete, name='printer_delete'),
    path('printers/<int:printer_id>/toggle/', views.printer_toggle_active, name='printer_toggle'),
    path('printers/<int:printer_id>/test/', views.printer_test_print, name='printer_test'),
    path('printers/setup-defaults/', views.printer_setup_defaults, name='printer_setup_defaults'),
    
    # Printer Brands CRUD
    path('brands/', views.brand_list, name='brand_list'),
    path('brands/create/', views.brand_create, name='brand_create'),
    path('brands/<int:brand_id>/edit/', views.brand_edit, name='brand_edit'),
    path('brands/<int:brand_id>/delete/', views.brand_delete, name='brand_delete'),
    path('brands/<int:brand_id>/toggle/', views.brand_toggle_active, name='brand_toggle'),
]
