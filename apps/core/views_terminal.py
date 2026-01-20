from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from apps.core.models import StoreConfig, POSTerminal
import json


def terminal_setup(request):
    """Terminal registration page"""
    store = StoreConfig.get_current()
    
    if not store:
        return render(request, 'core/terminal_setup_error.html', {
            'error': 'Store not configured. Please run: python manage.py setup_store --interactive'
        })
    
    if request.method == 'POST':
        terminal_code = request.POST.get('terminal_code', '').strip()
        terminal_name = request.POST.get('terminal_name', '').strip()
        device_type = request.POST.get('device_type')
        
        if not all([terminal_code, terminal_name, device_type]):
            messages.error(request, 'All fields are required')
            return redirect('core:terminal_setup')
        
        # Check if terminal code already exists
        if POSTerminal.objects.filter(terminal_code=terminal_code).exists():
            messages.error(request, f'Terminal code {terminal_code} already registered')
            return redirect('core:terminal_setup')
        
        # Get client information
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        mac_address = request.POST.get('mac_address', '')  # From JS if available
        
        # Create terminal
        terminal = POSTerminal.objects.create(
            store=store,
            terminal_code=terminal_code,
            terminal_name=terminal_name,
            device_type=device_type,
            ip_address=ip_address,
            user_agent=user_agent,
            mac_address=mac_address,
            registered_by=request.user if request.user.is_authenticated else None
        )
        
        terminal.update_heartbeat(ip_address)
        
        # Store terminal ID in session
        request.session['terminal_id'] = str(terminal.id)
        request.session['terminal_code'] = terminal.terminal_code
        
        messages.success(request, f'Terminal {terminal.terminal_code} registered successfully!')
        
        # Return terminal info as JSON for localStorage
        return JsonResponse({
            'success': True,
            'terminal': {
                'id': str(terminal.id),
                'code': terminal.terminal_code,
                'name': terminal.terminal_name,
                'type': terminal.device_type,
                'store_id': str(store.id),
                'store_code': store.store_code,
                'company_id': str(store.outlet.company.id),
                'company_name': store.outlet.company.name,
                'ip': terminal.ip_address,
                'mac': terminal.mac_address,
            },
            'message': f'Terminal {terminal.terminal_code} registered successfully!',
            'redirect': '/'
        })
    
    # GET request - show form
    existing_terminals = POSTerminal.objects.filter(store=store, is_active=True).order_by('terminal_code')
    
    return render(request, 'core/terminal_setup.html', {
        'store': store,
        'existing_terminals': existing_terminals,
    })


def terminal_heartbeat(request):
    """Update terminal heartbeat (called periodically)"""
    terminal_id = request.headers.get('X-Terminal-ID')
    
    if not terminal_id:
        return JsonResponse({'error': 'No terminal ID'}, status=400)
    
    try:
        terminal = POSTerminal.objects.get(id=terminal_id)
        ip_address = get_client_ip(request)
        terminal.update_heartbeat(ip_address)
        
        return JsonResponse({
            'success': True,
            'terminal': terminal.terminal_code,
            'online': terminal.is_online
        })
    except POSTerminal.DoesNotExist:
        return JsonResponse({'error': 'Terminal not found'}, status=404)


def terminal_list(request):
    """List all registered terminals (for admin)"""
    store = StoreConfig.get_current()
    terminals = POSTerminal.objects.filter(store=store).order_by('-last_heartbeat')
    
    return render(request, 'core/terminal_list.html', {
        'store': store,
        'terminals': terminals,
    })


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
