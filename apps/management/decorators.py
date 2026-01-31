"""
Access control decorators for management interface
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def manager_required(view_func):
    """
    Decorator to restrict access to Manager and Supervisor roles only.
    Cashier and Kitchen staff are redirected to POS/KDS.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        
        # Superuser always has access
        if user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Check if user has manager or supervisor role
        allowed_roles = ['manager', 'supervisor', 'admin']
        
        if hasattr(user, 'role') and user.role in allowed_roles:
            return view_func(request, *args, **kwargs)
        
        # Redirect non-managers back to login with message
        messages.error(request, 'Anda tidak memiliki akses ke Management Interface.')
        return redirect('core:login')
    
    return _wrapped_view


def supervisor_required(view_func):
    """
    Decorator to restrict access to Supervisor and Manager only.
    Higher level permissions.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        
        # Superuser always has access
        if user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Check if user has supervisor or manager role
        allowed_roles = ['manager', 'supervisor']
        
        if hasattr(user, 'role') and user.role in allowed_roles:
            return view_func(request, *args, **kwargs)
        
        messages.error(request, 'Akses ditolak. Hanya Supervisor atau Manager.')
        return redirect('management:dashboard')
    
    return _wrapped_view


def management_access_required(view_func):
    """
    General decorator for management interface access.
    Alias for manager_required for clarity.
    """
    return manager_required(view_func)
