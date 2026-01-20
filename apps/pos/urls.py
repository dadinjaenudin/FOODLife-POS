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
    path('bill/<int:bill_id>/hold-modal/', views.hold_modal, name='hold_modal'),
    path('bill/<int:bill_id>/resume/', views.resume_bill, name='resume_bill'),
    path('bill/<int:bill_id>/cancel/', views.cancel_bill, name='cancel_bill'),
    path('bill/<int:bill_id>/confirm-void/', views.confirm_void_modal, name='confirm_void_modal'),
    path('bill/<int:bill_id>/send-kitchen/', views.send_to_kitchen, name='send_to_kitchen'),
    
    # Item operations
    path('item/<int:item_id>/confirm-remove/', views.confirm_remove_item, name='confirm_remove_item'),
    path('item/<int:item_id>/void/', views.void_item, name='void_item'),
    path('item/<int:item_id>/update-qty/', views.update_item_qty, name='update_item_qty'),
    
    # Payment
    path('bill/<int:bill_id>/payment/', views.payment_modal, name='payment_modal'),
    path('bill/<int:bill_id>/pay/', views.process_payment, name='process_payment'),
    
    # Bill Management - Split, Merge, Move, Transfer
    path('bill/<int:bill_id>/split/', views.split_bill_modal, name='split_bill_modal'),
    path('bill/<int:bill_id>/split/process/', views.split_bill, name='split_bill'),
    path('bill/<int:bill_id>/merge/', views.merge_bills_modal, name='merge_bills_modal'),
    path('bills/merge/process/', views.merge_bills, name='merge_bills'),
    path('bill/<int:bill_id>/move-table/', views.move_table_modal, name='move_table_modal'),
    path('bill/<int:bill_id>/move-table/process/', views.move_table, name='move_table'),
    path('bill/<int:bill_id>/transfer/', views.transfer_bill_modal, name='transfer_bill_modal'),
    path('bill/<int:bill_id>/transfer/process/', views.transfer_bill, name='transfer_bill'),
    
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
    
    # Session & Shift Management
    path('session/open/', views.session_open, name='session_open'),
    path('shift/open-form/', views.shift_open_form, name='shift_open_form'),
    path('shift/open/', views.shift_open, name='shift_open'),
    path('shift/close-form/', views.shift_close_form, name='shift_close_form'),
    path('shift/close/', views.shift_close, name='shift_close'),
    path('shift/history/', views.shift_history, name='shift_history'),
    path('shift/my-dashboard/', views.shift_my_dashboard, name='shift_my_dashboard'),
    path('shift/<uuid:shift_id>/print-reconciliation/', views.shift_print_reconciliation, name='shift_print_reconciliation'),
    path('shift/<uuid:shift_id>/print-interim/', views.shift_print_interim, name='shift_print_interim'),
    path('shift/status/', views.shift_status, name='shift_status'),
    
    # Modals
    path('modifier/<int:product_id>/', views.modifier_modal, name='modifier_modal'),
]
