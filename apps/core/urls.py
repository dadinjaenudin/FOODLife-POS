from django.urls import path
from . import views, views_terminal, views_setup

app_name = 'core'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('pin-login/', views.pin_login, name='pin_login'),
    
    # User profile settings
    path('profile/settings/', views.profile_settings, name='profile_settings'),
    path('profile/update-photo/', views.update_profile_photo, name='update_profile_photo'),
    
    # Setup wizard
    path('setup/', views_setup.setup_wizard, name='setup_wizard'),
    path('setup/company/', views_setup.setup_company, name='setup_company'),
    path('setup/store-config/', views_setup.setup_store_config, name='setup_store_config'),
    path('setup/reset/', views_setup.setup_reset, name='setup_reset'),
    
    # Terminal setup
    path('setup/terminal/', views_terminal.terminal_setup, name='terminal_setup'),
    path('api/terminal/heartbeat/', views_terminal.terminal_heartbeat, name='terminal_heartbeat'),
    path('admin/terminals/', views_terminal.terminal_list, name='terminal_list'),
]
