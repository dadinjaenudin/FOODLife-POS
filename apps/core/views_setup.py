"""
Setup wizard views for initial Edge Server configuration
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from apps.core.models import Company, Outlet, StoreConfig, POSTerminal
from django.contrib.auth.decorators import login_required


def setup_wizard(request):
    """Main setup wizard - checks configuration status"""
    store_config = StoreConfig.get_current()
    
    if store_config:
        # Already configured, show status
        terminals = POSTerminal.objects.filter(store=store_config)
        return render(request, 'core/setup_status.html', {
            'store': store_config,
            'terminals': terminals,
            'is_configured': True
        })
    
    # Not configured, show setup wizard
    companies = Company.objects.filter(is_active=True)
    
    if not companies.exists():
        # No company exists, show company creation first
        return render(request, 'core/setup_company.html')
    
    return render(request, 'core/setup_store.html', {
        'companies': companies,
    })


def setup_company(request):
    """Create new company"""
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        name = request.POST.get('name', '').strip()
        timezone = request.POST.get('timezone', 'Asia/Jakarta')
        
        if not all([code, name]):
            messages.error(request, 'Company code and name are required')
            return redirect('core:setup_wizard')
        
        try:
            company = Company.objects.create(
                code=code,
                name=name,
                timezone=timezone
            )
            
            # Auto-create default outlet
            outlet = Outlet.objects.create(
                company=company,
                code=f'{code}-01',
                name=f'{name} - Main',
                address='',
                phone='',
            )
            
            messages.success(request, f'Company "{name}" created successfully')
            return redirect('core:setup_wizard')
        except Exception as e:
            messages.error(request, f'Error creating company: {str(e)}')
            return redirect('core:setup_wizard')
    
    return redirect('core:setup_wizard')


def setup_store_config(request):
    """Configure Edge Server store identity"""
    if StoreConfig.objects.exists():
        messages.warning(request, 'Store already configured')
        return redirect('core:setup_wizard')
    
    if request.method == 'POST':
        outlet_id = request.POST.get('outlet_id')
        store_code = request.POST.get('store_code', '').strip().upper()
        store_name = request.POST.get('store_name', '').strip()
        address = request.POST.get('address', '').strip()
        phone = request.POST.get('phone', '').strip()
        
        if not all([outlet_id, store_code, store_name]):
            messages.error(request, 'Outlet, store code, and name are required')
            return redirect('core:setup_wizard')
        
        try:
            outlet = Outlet.objects.get(id=outlet_id)
            
            store_config = StoreConfig.objects.create(
                outlet=outlet,
                store_code=store_code,
                store_name=store_name,
                address=address,
                phone=phone,
            )
            
            messages.success(request, f'Store "{store_name}" configured successfully! Now register your terminals.')
            return redirect('core:terminal_setup')
        except Outlet.DoesNotExist:
            messages.error(request, 'Invalid outlet selected')
        except Exception as e:
            messages.error(request, f'Error configuring store: {str(e)}')
        
        return redirect('core:setup_wizard')
    
    return redirect('core:setup_wizard')


def setup_reset(request):
    """Reset store configuration (admin only)"""
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, 'Unauthorized')
        return redirect('core:setup_wizard')
    
    if request.method == 'POST':
        confirm = request.POST.get('confirm', '').lower()
        if confirm == 'reset':
            # Delete store config and terminals
            POSTerminal.objects.all().delete()
            StoreConfig.objects.all().delete()
            messages.success(request, 'Store configuration reset successfully')
        else:
            messages.error(request, 'Confirmation failed')
    
    return redirect('core:setup_wizard')
