from django.urls import path
from . import views

app_name = 'tables'

urlpatterns = [
    path('', views.table_map, name='floor_plan'),
    path('status/', views.table_status, name='status'),
    path('grid/', views.table_grid, name='grid'),
    
    path('<int:table_id>/open/', views.open_table, name='open_table'),
    path('<int:table_id>/close/', views.close_table, name='close_table'),
    path('<int:table_id>/clean/', views.clean_table, name='clean_table'),
    path('bill/<int:bill_id>/move/', views.move_table, name='move_table'),
    path('save-order/', views.save_table_order, name='save_table_order'),
    
    path('join/', views.join_tables, name='join_tables'),
    path('group/<int:group_id>/split/', views.split_table, name='split_table'),
    path('merge/', views.merge_tables, name='merge_tables'),
    
    path('qr-codes/', views.table_qr_codes, name='qr_codes'),
    path('<int:table_id>/generate-qr/', views.generate_qr, name='generate_qr'),
]
