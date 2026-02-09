"""
Setup wizard views for initial Edge Server configuration
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from apps.core.models import Company, Brand, Store, POSTerminal
from django.contrib.auth.decorators import login_required
from django.conf import settings
import requests
import logging
import time
import uuid

logger = logging.getLogger(__name__)


def sync_company_from_remote(company_data):
    """
    Sync company data from remote HO API to local database
    """
    try:
        company, created = Company.objects.update_or_create(
            id=company_data['id'],
            defaults={
                'code': company_data['code'],
                'name': company_data['name'],
                'timezone': company_data.get('timezone', 'Asia/Jakarta'),
                'is_active': company_data.get('is_active', True),
                'point_expiry_months': company_data.get('point_expiry_months', 12),
                'points_per_currency': company_data.get('points_per_currency', 1.00),
            }
        )
        return company, created
    except Exception as e:
        print(f"Error syncing company: {e}")
        return None, False


def sync_brand_from_remote(brand_data):
    """
    Sync brand data from remote HO API to local database
    """
    try:
        # Ensure company exists
        company = Company.objects.filter(id=brand_data['company_id']).first()
        if not company:
            logger.error(f"[SYNC] Company {brand_data['company_id']} not found for brand {brand_data.get('name')}")
            return None, False
        
        brand, created = Brand.objects.update_or_create(
            id=brand_data['id'],
            defaults={
                'company': company,
                'code': brand_data['code'],
                'name': brand_data['name'],
                'address': brand_data.get('address', ''),
                'phone': brand_data.get('phone', ''),
                'tax_id': brand_data.get('tax_id', ''),
                'tax_rate': brand_data.get('tax_rate', 11.00),
                'service_charge': brand_data.get('service_charge', 5.00),
                'is_active': brand_data.get('is_active', True),
                'point_expiry_months_override': brand_data.get('point_expiry_months_override'),
            }
        )
        logger.info(f"[SYNC] Brand {brand.name} synced successfully (created={created})")
        return brand, created
    except Exception as e:
        logger.error(f"[SYNC] Error syncing brand {brand_data.get('name', 'Unknown')}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None, False


@csrf_exempt
def setup_wizard(request):
    """Main setup wizard - checks configuration status"""
    store_config = Store.get_current()
    
    if store_config:
        # Already configured, show status
        terminals = POSTerminal.objects.filter(store=store_config)
        return render(request, 'core/setup_status.html', {
            'store': store_config,
            'terminals': terminals,
            'is_configured': True
        })
    
    # Not configured yet - show multi-brand setup form
    # This form will fetch companies and brands from HO Server via API
    return render(request, 'core/setup_store.html')


# Legacy setup views removed - now using multi-brand setup with HO sync only


@csrf_exempt
def setup_store_config_multi_brand(request):
    """
    Setup Edge Server - Fetch data from HO and save to Edge database
    Uses HOAPIClient for clean integration
    """
    # Check if already setup
    if Store.objects.exists():
        # Store already configured - return JSON for SweetAlert
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            store = Store.get_current()
            return JsonResponse({
                'success': False,
                'already_configured': True,
                'message': 'Store telah di-setup sebelumnya',
                'store_name': store.store_name,
                'store_code': store.store_code,
                'company_name': store.company.name
            })
        messages.warning(request, 'Edge Server already configured')
        return redirect('core:setup_wizard')
    
    if request.method == 'POST':
        company_id = request.POST.get('company_id')
        ho_store_id = request.POST.get('ho_store_id')
        
        if not all([company_id, ho_store_id]):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Company and Store are required'
                }, status=400)
            messages.error(request, 'Company and Store are required')
            return redirect('core:setup_wizard')
        
        try:
            from apps.core.ho_api import HOAPIClient, HOAPIException
            
            logger.info("[SETUP] Starting Edge Server setup...")
            logger.info(f"[SETUP] Company ID: {company_id}, Store ID: {ho_store_id}")
            
            # Initialize HO API Client
            client = HOAPIClient()
            
            # Step 1: Fetch Company from HO
            logger.info("[SETUP] Fetching company from HO...")
            companies = client.get_companies()
            company_data = next((c for c in companies if c['id'] == company_id), None)
            
            if not company_data:
                raise Exception('Company not found in HO Server')
            
            # Sync company to Edge
            company, created = sync_company_from_remote(company_data)
            logger.info(f"[SETUP] ✓ Company synced: {company.name} (created={created})")
            
            # Step 2: Fetch Store from HO
            logger.info("[SETUP] Fetching store from HO...")
            stores = client.get_stores(company_id=company_id)
            ho_store_data = next((s for s in stores if s['id'] == ho_store_id), None)
            
            if not ho_store_data:
                raise Exception(f'Store not found in HO Server')
            
            # Step 3: Fetch store-brand relationships from HO (multiple brands per store)
            logger.info(f"[SETUP] Fetching store-brands for store {ho_store_id} from HO...")
            store_brands_data = client.get_store_brands(company_id=company_id, store_id=ho_store_id)
            
            logger.info(f"[SETUP] Store-brands API response: {store_brands_data}")
            
            if not store_brands_data or len(store_brands_data) == 0:
                raise Exception('No brands found for this store in HO Server')
            
            logger.info(f"[SETUP] Found {len(store_brands_data)} brand(s) for this store")
            
            # Step 4: Sync all brands for this store
            synced_brands = []
            for idx, store_brand_rel in enumerate(store_brands_data):
                logger.info(f"[SETUP] Processing store-brand #{idx + 1}: {store_brand_rel}")
                
                # HO API returns flat structure with brand_id, brand_code, brand_name
                # Need to construct brand_data from these fields
                brand_id = store_brand_rel.get('brand_id')
                if not brand_id:
                    logger.warning(f"[SETUP] Skipping store-brand relationship #{idx + 1} - missing brand_id")
                    continue
                
                # Construct brand data from flat structure
                brand_data = {
                    'id': brand_id,
                    'company_id': store_brand_rel.get('company_id'),
                    'code': store_brand_rel.get('brand_code', ''),
                    'name': store_brand_rel.get('brand_name', ''),
                    'address': '',
                    'phone': '',
                    'tax_id': '',
                    'tax_rate': 11.00,
                    'service_charge': 5.00,
                    'is_active': store_brand_rel.get('is_active', True),
                }
                
                logger.info(f"[SETUP] Syncing brand: {brand_data['name']} (ID: {brand_data['id']})")
                
                try:
                    brand, created = sync_brand_from_remote(brand_data)
                    if brand:
                        synced_brands.append({
                            'brand': brand,
                            'created': created,
                            'is_active': store_brand_rel.get('is_active', True)
                        })
                        logger.info(f"[SETUP] ✓ Brand synced: {brand.name} (created={created})")
                    else:
                        logger.error(f"[SETUP] sync_brand_from_remote returned None for brand: {brand_data}")
                except Exception as brand_sync_error:
                    logger.error(f"[SETUP] Failed to sync brand {brand_data.get('name')}: {brand_sync_error}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            if not synced_brands:
                logger.error(f"[SETUP] No brands were successfully synced. Total store-brands received: {len(store_brands_data)}")
                raise Exception(f'Failed to sync any brands for this store. Received {len(store_brands_data)} brand(s) but all failed to sync.')
            
            # Step 5: Create Edge Store
            edge_store = Store.objects.create(
                company=company,
                store_code=ho_store_data['store_code'],
                store_name=ho_store_data['store_name'],
                address=ho_store_data.get('address', ''),
                phone=ho_store_data.get('phone', ''),
                timezone=ho_store_data.get('timezone', company.timezone),
                is_active=True,
            )
            logger.info(f"[SETUP] ✓ Store created: {edge_store.store_name}")
            
            # Step 6: Link all brands to store via StoreBrand junction table
            from .models import StoreBrand
            for brand_info in synced_brands:
                StoreBrand.objects.create(
                    store=edge_store,
                    brand=brand_info['brand'],
                    ho_store_id=ho_store_id,
                    is_active=brand_info['is_active']
                )
                logger.info(f"[SETUP] ✓ Brand '{brand_info['brand'].name}' linked to store")
            
            brand_names = ', '.join([b['brand'].name for b in synced_brands])
            logger.info(f"[SETUP] ✓ Setup complete - Store configured with {len(synced_brands)} brand(s): {brand_names}")
            logger.info(f"[SETUP] Note: Master data sync should be done from /management/master-data/")
            
            # Return success response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Setup berhasil!',
                    'store_name': edge_store.store_name,
                    'store_code': edge_store.store_code,
                    'company_name': company.name,
                    'brand_count': len(synced_brands),
                    'brand_names': brand_names,
                    'next_step': 'Silakan sync master data dari menu Management > Master Data'
                })
            
            messages.success(
                request,
                f'✅ Edge Server Setup Complete!\n\n'
                f'Company: {company.name} ({company.code})\n'
                f'Store: {edge_store.store_name} ({edge_store.store_code})\n'
                f'Brands: {brand_names}\n\n'
                f'Next Step:\n'
                f'Silakan login dan sync master data dari menu:\n'
                f'Management > Master Data'
            )
            return redirect('core:setup_wizard')
            
        except HOAPIException as e:
            logger.error(f"[SETUP] HO API Error: {str(e)}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f'Failed to connect to HO Server: {str(e)}'
                }, status=500)
            messages.error(request, f'Failed to connect to HO Server: {str(e)}')
        except Exception as e:
            logger.error(f"[SETUP] Error: {str(e)}")
            import traceback
            traceback.print_exc()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f'Setup failed: {str(e)}'
                }, status=500)
            messages.error(request, f'Setup failed: {str(e)}')
        
        return redirect('core:setup_wizard')
    
    return redirect('core:setup_wizard')


# Legacy single-brand setup removed - use setup_store_config_multi_brand instead


@csrf_exempt
@require_http_methods(["GET", "POST"])
def fetch_companies_from_ho(request):
    """
    Proxy endpoint to fetch companies from HO Server API
    This is used by the setup page dropdown to get companies from HO
    Uses HOAPIClient for clean integration
    """
    from apps.core.ho_api import HOAPIClient, HOAPIException
    
    # Mock data fallback
    mock_data = {
        'companies': [
            {
                'id': '812e76b6-f235-4bb2-948a-cae58ee62b97',
                'code': 'AVRIL',
                'name': 'AVRIL COMPANY',
                'timezone': 'Asia/Jakarta',
                'is_active': True,
                'point_expiry_months': 12,
                'points_per_currency': 1.00
            },
            {
                'id': 'test-company-id-2',
                'code': 'DEMO',
                'name': 'DEMO COMPANY',
                'timezone': 'Asia/Jakarta',
                'is_active': True,
                'point_expiry_months': 12,
                'points_per_currency': 1.00
            }
        ],
        'total': 2,
        'success': True
    }
    
    try:
        # Use HOAPIClient to fetch companies
        client = HOAPIClient()
        companies = client.get_companies()
        
        return JsonResponse({
            'companies': companies,
            'total': len(companies),
            'success': True
        })
        
    except HOAPIException as e:
        logger.error("[HO API] Error fetching companies: %s", str(e))
        # Return mock data on error
        return JsonResponse(mock_data)
    except Exception as e:
        logger.exception("[HO API] Unexpected error fetching companies: %s", str(e))
        return JsonResponse(mock_data)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def fetch_brands_from_ho(request):
    """
    Proxy endpoint to fetch brands from HO Server API
    This is used by the setup page dropdown to get brands from HO
    Uses HOAPIClient for clean integration
    Supports both GET and POST methods
    """
    from apps.core.ho_api import HOAPIClient, HOAPIException
    
    # Get parameters from GET or POST
    company_id = request.GET.get('company_id') or request.POST.get('company_id')
    store_id = request.GET.get('store_id') or request.POST.get('store_id')
    
    # Try to get from JSON body if POST
    if request.method == 'POST' and not company_id:
        try:
            import json
            body_data = json.loads(request.body)
            company_id = body_data.get('company_id')
            store_id = body_data.get('store_id')
        except:
            pass
    
    if not company_id:
        return JsonResponse({
            'success': False,
            'error': 'Missing required parameter: company_id',
            'brands': [],
            'total': 0
        }, status=400)
    
    try:
        # Use HOAPIClient to fetch brands
        client = HOAPIClient()
        brands = client.get_brands(company_id=company_id, store_id=store_id)
        
        return JsonResponse({
            'brands': brands,
            'total': len(brands),
            'success': True
        })
        
    except HOAPIException as e:
        logger.error("[HO API] Error fetching brands: %s", str(e))
        return JsonResponse({
            'success': False,
            'error': str(e),
            'brands': [],
            'total': 0
        }, status=500)
    except Exception as e:
        logger.exception("[HO API] Unexpected error fetching brands: %s", str(e))
        return JsonResponse({
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'brands': [],
            'total': 0
        }, status=500)


@csrf_exempt
def fetch_stores_from_ho(request):
    """
    Proxy endpoint to fetch stores from HO Server API
    This is used by the setup page dropdown to get stores from HO
    Uses HOAPIClient for clean integration
    
    Supports both brand_id and company_id parameters:
    - ?brand_id={uuid} - Get stores for specific brand
    - ?company_id={uuid} - Get stores for specific company
    """
    from apps.core.ho_api import HOAPIClient, HOAPIException
    
    brand_id = request.GET.get('brand_id')
    company_id = request.GET.get('company_id')
    
    if not brand_id and not company_id:
        # Check if json body has params
        try:
            import json
            body_data = json.loads(request.body)
            brand_id = body_data.get('brand_id')
            company_id = body_data.get('company_id')
        except:
            pass
            
    if not brand_id and not company_id:
        return JsonResponse({
            'success': False,
            'error': 'Missing required parameter: brand_id or company_id',
            'stores': [],
            'total': 0
        }, status=400)
    
    try:
        # Use HOAPIClient to fetch stores
        client = HOAPIClient()
        stores = client.get_stores(company_id=company_id, brand_id=brand_id)
        
        return JsonResponse({
            'stores': stores,
            'total': len(stores),
            'success': True
        })
        
    except HOAPIException as e:
        logger.error("[HO API] Error fetching stores: %s", str(e))
        return JsonResponse({
            'success': False,
            'error': str(e),
            'stores': [],
            'total': 0
        }, status=500)
    except Exception as e:
        logger.exception("[HO API] Unexpected error fetching stores: %s", str(e))
        return JsonResponse({
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'stores': [],
            'total': 0
        }, status=500)


# Legacy sync endpoint removed - setup flow now auto-syncs everything


def setup_reset(request):
    """Reset ALL multi-tenant configuration (admin only)"""
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, 'Unauthorized')
        return redirect('core:setup_wizard')
    
    if request.method == 'POST':
        confirm = request.POST.get('confirm', '').lower()
        if confirm == 'reset':
            # Delete in proper order (respects FK constraints)
            from apps.core.models import Category, Product, Modifier
            from apps.pos.models import Bill, BillItem, Payment
            from apps.core.models_session import CashierShift, StoreSession, CashDrop
            
            # Count before deletion
            terminal_count = POSTerminal.objects.count()
            store_count = Store.objects.count()
            product_count = Product.objects.count()
            category_count = Category.objects.count()
            modifier_count = Modifier.objects.count()
            brand_count = Brand.objects.count()
            company_count = Company.objects.count()
            bill_count = Bill.objects.count()
            bill_item_count = BillItem.objects.count()
            payment_count = Payment.objects.count()
            shift_count = CashierShift.objects.count()
            session_count = StoreSession.objects.count()
            cashdrop_count = CashDrop.objects.count()
            
            # Step 0: Delete POS transactions (they reference Products, Store, Brand, Company with PROTECT)
            BillItem.objects.all().delete()
            Payment.objects.all().delete()
            Bill.objects.all().delete()
            
            # Step 0.5: Delete cash drops (they reference CashierShift with PROTECT)
            CashDrop.objects.all().delete()
            
            # Step 0.6: Delete cashier shifts and sessions (they reference POSTerminal and Store with PROTECT)
            CashierShift.objects.all().delete()
            StoreSession.objects.all().delete()
            
            # Step 1: Delete terminals (depends on Store)
            POSTerminal.objects.all().delete()
            
            # Step 2: Delete stores (depends on Brand)
            Store.objects.all().delete()
            
            # Step 3: Delete products, categories, modifiers (depends on Brand)
            Product.objects.all().delete()
            Category.objects.all().delete()
            Modifier.objects.all().delete()
            
            # Step 4: Delete brands (depends on Company)
            Brand.objects.all().delete()
            
            # Step 5: Delete companies (top level)
            Company.objects.all().delete()
            
            messages.success(request, 
                f'✅ Complete reset successful! Deleted: {company_count} companies, '
                f'{brand_count} brands, {store_count} stores, {terminal_count} terminals, '
                f'{session_count} sessions, {shift_count} shifts, {cashdrop_count} cash drops, '
                f'{product_count} products, {category_count} categories, {modifier_count} modifiers, '
                f'{bill_count} bills, {bill_item_count} bill items, {payment_count} payments. '
                f'Start fresh from /setup/')
        else:
            messages.error(request, 'Confirmation failed. Type "reset" (lowercase) to confirm.')
    
    return redirect('core:setup_wizard')
