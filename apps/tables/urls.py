from django.urls import path
from . import views
from . import views_booking

app_name = 'tables'

urlpatterns = [
    path('', views.table_map, name='floor_plan'),
    path('status/', views.table_status, name='status'),
    path('grid/', views.table_grid, name='grid'),
    path('position/update/', views.update_table_position, name='update_table_position'),

    path('<uuid:table_id>/open/', views.open_table, name='open_table'),
    path('<uuid:table_id>/close/', views.close_table, name='close_table'),
    path('<uuid:table_id>/clean/', views.clean_table, name='clean_table'),
    path('bill/<uuid:bill_id>/move/', views.move_table, name='move_table'),
    path('save-order/', views.save_table_order, name='save_table_order'),

    path('join/', views.join_tables, name='join_tables'),
    path('group/<uuid:group_id>/split/', views.split_table, name='split_table'),
    path('merge/', views.merge_tables, name='merge_tables'),

    path('qr-codes/', views.table_qr_codes, name='qr_codes'),
    path('<uuid:table_id>/generate-qr/', views.generate_qr, name='generate_qr'),

    # ===== BOOKING =====
    path('booking/', views_booking.booking_dashboard, name='booking_dashboard'),
    path('booking/create/', views_booking.booking_create, name='booking_create'),
    path('booking/<uuid:reservation_id>/', views_booking.booking_detail, name='booking_detail'),
    path('booking/<uuid:reservation_id>/deposit/', views_booking.booking_deposit_form, name='booking_deposit_form'),
    path('booking/<uuid:reservation_id>/deposit/pay/', views_booking.booking_deposit_pay, name='booking_deposit_pay'),
    path('booking/<uuid:reservation_id>/deposit/qris/create/', views_booking.booking_deposit_qris_create, name='booking_deposit_qris_create'),
    path('booking/<uuid:reservation_id>/deposit/qris/<str:transaction_id>/status/', views_booking.booking_deposit_qris_status, name='booking_deposit_qris_status'),
    path('booking/<uuid:reservation_id>/deposit/qris/<str:transaction_id>/cancel/', views_booking.booking_deposit_qris_cancel, name='booking_deposit_qris_cancel'),
    path('booking/<uuid:reservation_id>/deposit/qris/<str:transaction_id>/simulate/', views_booking.booking_deposit_qris_simulate, name='booking_deposit_qris_simulate'),
    path('booking/<uuid:reservation_id>/checkin/', views_booking.booking_checkin, name='booking_checkin'),
    path('booking/<uuid:reservation_id>/cancel/', views_booking.booking_cancel_form, name='booking_cancel_form'),
    path('booking/<uuid:reservation_id>/cancel/confirm/', views_booking.booking_cancel, name='booking_cancel'),
    path('booking/<uuid:reservation_id>/noshow/', views_booking.booking_noshow, name='booking_noshow'),
    path('booking/<uuid:reservation_id>/deposit/data/', views_booking.booking_deposit_data, name='booking_deposit_data'),
    path('booking/<uuid:reservation_id>/deposit/print-preview/', views_booking.booking_deposit_print_preview, name='booking_deposit_print_preview'),
    path('booking/available-tables/', views_booking.available_tables, name='booking_available_tables'),
]
