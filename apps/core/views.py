from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .models import User


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('pos:main')
        else:
            return render(request, 'core/login.html', {'error': 'Invalid credentials'})
    
    return render(request, 'core/login.html')


def logout_view(request):
    logout(request)
    return redirect('core:login')


def pin_login(request):
    """Quick PIN login for staff"""
    if request.method == 'POST':
        pin = request.POST.get('pin')
        try:
            user = User.objects.get(pin=pin, is_active=True)
            login(request, user)
            return redirect('pos:main')
        except User.DoesNotExist:
            return render(request, 'core/pin_login.html', {'error': 'PIN tidak valid'})
    
    return render(request, 'core/pin_login.html')
