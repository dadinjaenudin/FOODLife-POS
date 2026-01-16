from django.urls import path
from . import views

app_name = 'qr_order'

urlpatterns = [
    path('<int:outlet_id>/<int:table_id>/', views.guest_menu, name='menu'),
    path('<int:outlet_id>/<int:table_id>/cart/', views.guest_cart, name='cart'),
    path('<int:outlet_id>/<int:table_id>/add/', views.guest_add_item, name='add_item'),
    path('<int:outlet_id>/<int:table_id>/remove/<int:item_id>/', views.guest_remove_item, name='remove_item'),
    path('<int:outlet_id>/<int:table_id>/submit/', views.guest_submit_order, name='submit'),
    path('<int:outlet_id>/<int:table_id>/status/', views.guest_order_status, name='status'),
]
