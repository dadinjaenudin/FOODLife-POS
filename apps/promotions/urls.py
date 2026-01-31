"""
Promotions URLs
"""
from django.urls import path
from . import views

app_name = 'promotions'

urlpatterns = [
    # Testing UI / Simulator
    path('simulator/', views.promotion_test_page, name='simulator'),
    path('simulator/add/', views.test_add_to_cart, name='simulator_add'),
    path('simulator/calculate/', views.test_calculate_promotions, name='simulator_calculate'),
    path('simulator/clear/', views.test_clear_cart, name='simulator_clear'),
    path('simulator/remove/', views.test_remove_item, name='simulator_remove'),
    
    # API Endpoints (for POS integration)
    path('api/calculate/', views.api_calculate_promotions, name='api_calculate'),
    path('api/applicable/', views.api_get_applicable_promotions, name='api_applicable'),
]
