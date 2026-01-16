from django.urls import path
from . import views

app_name = 'kitchen'

urlpatterns = [
    path('kds/', views.kds_screen, name='kds'),
    path('kds/<str:station>/', views.kds_screen, name='kds_station'),
    path('kds/<str:station>/orders/', views.kds_orders, name='kds_orders'),
    path('order/<int:order_id>/start/', views.kds_start, name='kds_start'),
    path('order/<int:order_id>/ready/', views.kds_ready, name='kds_ready'),
    path('order/<int:order_id>/bump/', views.kds_bump, name='kds_bump'),
    
    path('printers/', views.printer_list, name='printer_list'),
    path('printers/test/<int:printer_id>/', views.test_printer, name='test_printer'),
]
