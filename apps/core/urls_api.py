"""
Core API URLs for Terminal Validation
"""
from django.urls import path
from . import api_terminal

app_name = 'core_api'

urlpatterns = [
    # Terminal validation
    path('terminal/validate', api_terminal.validate_terminal, name='terminal_validate'),
    path('terminal/heartbeat', api_terminal.terminal_heartbeat, name='terminal_heartbeat'),
]
