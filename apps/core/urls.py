from django.urls import path
from . import views, views_terminal, views_setup, views_debug

app_name = 'core'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('pin-login/', views.pin_login, name='pin_login'),
    
    # Debug endpoints
    path('debug/csrf/', views_debug.csrf_debug, name='csrf_debug'),
    path('test-csrf/', views_debug.csrf_test_page, name='csrf_test'),
    
    # User profile settings
    path('profile/settings/', views.profile_settings, name='profile_settings'),
    path('profile/update-photo/', views.update_profile_photo, name='update_profile_photo'),
    
    # Setup wizard
    path('setup/', views_setup.setup_wizard, name='setup_wizard'),
    path('setup/store-config/', views_setup.setup_store_config_multi_brand, name='setup_store_config'),
    path('setup/reset/', views_setup.setup_reset, name='setup_reset'),
    
    # HO API proxy endpoints (for setup wizard)
    path('api/ho/companies/', views_setup.fetch_companies_from_ho, name='fetch_companies_from_ho'),
    path('api/ho/brands/', views_setup.fetch_brands_from_ho, name='fetch_brands_from_ho'),
    path('api/ho/stores/', views_setup.fetch_stores_from_ho, name='fetch_stores_from_ho'),
    
    # Terminal setup
    path('setup/terminal/', views_terminal.terminal_setup, name='terminal_setup'),
    path('api/terminal/heartbeat/', views_terminal.terminal_heartbeat, name='terminal_heartbeat'),
    path('api/terminal/check-code/', views_terminal.check_terminal_code, name='check_terminal_code'),
    path('admin/terminals/', views_terminal.terminal_list, name='terminal_list'),
    
]
