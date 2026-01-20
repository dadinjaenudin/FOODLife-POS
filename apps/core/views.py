from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from .models import User, StoreConfig


def login_view(request):
    # Get store config for login image
    store_config = StoreConfig.get_current()
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        terminal_id = request.POST.get('terminal_id')  # From localStorage via JS
        
        # CRITICAL: Validate terminal_id exists
        if not terminal_id:
            return render(request, 'core/login.html', {
                'error': '⚠️ Terminal not setup. Please setup terminal first.',
                'store_config': store_config
            })
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Store terminal ID in session if provided
            if terminal_id:
                try:
                    from apps.core.models import POSTerminal
                    terminal = POSTerminal.objects.get(id=terminal_id, is_active=True)
                    request.session['terminal_id'] = str(terminal.id)
                    request.session['terminal_code'] = terminal.terminal_code
                except POSTerminal.DoesNotExist:
                    pass  # Terminal not found, middleware will handle redirect
            
            # Smart redirect based on user role
            next_url = request.GET.get('next')
            if next_url and next_url not in ['/', '/setup/', '/setup/terminal/']:
                return redirect(next_url)
            
            # Role-based default redirect
            if user.role in ['admin', 'manager', 'supervisor']:
                return redirect('management:dashboard')
            else:
                # Cashier/waiter/kitchen need terminal or go to POS
                return redirect('pos:main')
        else:
            return render(request, 'core/login.html', {
                'error': 'Invalid credentials',
                'store_config': store_config
            })
    
    return render(request, 'core/login.html', {'store_config': store_config})


def logout_view(request):
    logout(request)
    return redirect('core:login')


@ensure_csrf_cookie
def pin_login(request):
    """Quick PIN login for staff"""
    if request.method == 'POST':
        pin = request.POST.get('pin')
        terminal_id = request.POST.get('terminal_id')  # From localStorage via JS
        
        # CRITICAL: Validate terminal_id exists
        if not terminal_id:
            return render(request, 'core/pin_login.html', {
                'error': '⚠️ Terminal not setup. Please setup terminal first.'
            })
        
        try:
            user = User.objects.get(pin=pin, is_active=True)
            login(request, user)
            
            # Store terminal ID in session
            if terminal_id:
                try:
                    from apps.core.models import POSTerminal
                    terminal = POSTerminal.objects.get(id=terminal_id, is_active=True)
                    request.session['terminal_id'] = str(terminal.id)
                    request.session['terminal_code'] = terminal.terminal_code
                except POSTerminal.DoesNotExist:
                    pass
            
            return redirect('pos:main')
        except User.DoesNotExist:
            return render(request, 'core/pin_login.html', {'error': 'PIN tidak valid'})
    
    return render(request, 'core/pin_login.html')


@login_required
def profile_settings(request):
    """Profile settings page for cashiers to upload photo"""
    return render(request, 'core/profile_settings.html', {
        'user': request.user
    })


@login_required
def update_profile_photo(request):
    """Update user profile photo via AJAX"""
    if request.method == 'POST' and request.FILES.get('profile_photo'):
        user = request.user
        user.profile_photo = request.FILES['profile_photo']
        user.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Photo profile berhasil diupdate',
            'photo_url': user.profile_photo.url if user.profile_photo else None
        })
    
    return JsonResponse({
        'success': False,
        'message': 'Tidak ada file yang diupload'
    }, status=400)
