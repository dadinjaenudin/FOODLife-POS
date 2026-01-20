from django.urls import path
from . import views

app_name = 'promotions'

urlpatterns = [
    path('bill/<int:bill_id>/apply/', views.apply_promo_modal, name='apply_promo_modal'),
    path('bill/<int:bill_id>/voucher/', views.apply_voucher, name='apply_voucher'),
    path('bill/<int:bill_id>/promo/', views.apply_promotion, name='apply_promotion'),
    path('remove/<int:bill_promo_id>/', views.remove_promotion, name='remove_promotion'),
]
