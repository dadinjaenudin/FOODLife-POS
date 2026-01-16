from django.urls import path
from . import views

app_name = 'pos'

urlpatterns = [
    path('', views.pos_main, name='main'),
    path('products/', views.product_list, name='products'),
    
    # Bill operations
    path('bill/open/', views.open_bill, name='open_bill'),
    path('bill/<int:bill_id>/add-item/', views.add_item, name='add_item'),
    path('bill/<int:bill_id>/hold/', views.hold_bill, name='hold_bill'),
    path('bill/<int:bill_id>/resume/', views.resume_bill, name='resume_bill'),
    path('bill/<int:bill_id>/cancel/', views.cancel_bill, name='cancel_bill'),
    path('bill/<int:bill_id>/send-kitchen/', views.send_to_kitchen, name='send_to_kitchen'),
    
    # Item operations
    path('item/<int:item_id>/void/', views.void_item, name='void_item'),
    path('item/<int:item_id>/update-qty/', views.update_item_qty, name='update_item_qty'),
    
    # Payment
    path('bill/<int:bill_id>/payment/', views.payment_modal, name='payment_modal'),
    path('bill/<int:bill_id>/pay/', views.process_payment, name='process_payment'),
    
    # Split
    path('bill/<int:bill_id>/split/', views.split_bill_modal, name='split_bill_modal'),
    path('bill/<int:bill_id>/split/process/', views.split_bill, name='split_bill'),
    
    # Reprint
    path('bill/<int:bill_id>/reprint-receipt/', views.reprint_receipt, name='reprint_receipt'),
    path('bill/<int:bill_id>/reprint-kitchen/', views.reprint_kitchen, name='reprint_kitchen'),
    
    # Held bills
    path('held/', views.held_bills, name='held_bills'),
    
    # Quick order
    path('quick-order/', views.quick_order_modal, name='quick_order'),
    path('quick-order/create/', views.quick_order_create, name='quick_order_create'),
    
    # Queue display
    path('queue/', views.queue_display, name='queue_display'),
    
    # Modals
    path('select-table/', views.select_table_modal, name='select_table_modal'),
    path('modifier/<int:product_id>/', views.modifier_modal, name='modifier_modal'),
]
