"""
Terminal API Endpoints
Handles terminal validation, heartbeat, and configuration
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import connection
from .models import POSTerminal
import json


@csrf_exempt
@require_http_methods(["POST"])
def validate_terminal(request):
    """
    Validate terminal credentials and generate session token
    POST /api/terminal/validate
    Body: {"terminal_code": "BOE-001", "session_token": "uuid" (optional)}
    """
    try:
        data = json.loads(request.body)
        terminal_code = data.get('terminal_code')
        session_token = data.get('session_token')
        
        if not terminal_code:
            return JsonResponse({
                'valid': False,
                'error': 'terminal_code required'
            }, status=400)
        
        try:
            terminal = POSTerminal.objects.select_related('store', 'store__company').get(
                terminal_code=terminal_code,
                is_active=True
            )
            
            # Get brand (may be None for stores without brands)
            brand = terminal.brand if terminal.brand else terminal.store.get_primary_brand()
            
            # Validate existing session token if provided
            if session_token:
                if terminal.validate_session_token(session_token):
                    # Token valid, update last_seen
                    terminal.last_seen = timezone.now()
                    terminal.save(update_fields=['last_seen'])
                    
                    return JsonResponse({
                        'valid': True,
                        'terminal': {
                            'id': str(terminal.id),
                            'code': terminal.terminal_code,
                            'name': terminal.terminal_name,
                            'type': terminal.device_type,
                            'store_id': str(terminal.store.id),
                            'store_name': terminal.store.store_name,
                            'brand_id': str(brand.id) if brand else None,
                            'brand_name': brand.name if brand else None,
                        },
                        'session_token': str(terminal.session_token),
                        'token_expires_at': terminal.token_expires_at.isoformat()
                    })
                else:
                    # Token invalid or expired, generate new one
                    new_token = terminal.generate_session_token(expiry_hours=24)
                    
                    return JsonResponse({
                        'valid': True,
                        'terminal': {
                            'id': str(terminal.id),
                            'code': terminal.terminal_code,
                            'name': terminal.terminal_name,
                            'type': terminal.device_type,
                            'store_id': str(terminal.store.id),
                            'store_name': terminal.store.store_name,
                            'brand_id': str(brand.id) if brand else None,
                            'brand_name': brand.name if brand else None,
                        },
                        'session_token': str(new_token),
                        'token_expires_at': terminal.token_expires_at.isoformat(),
                        'message': 'New session token generated'
                    })
            else:
                # No token provided, generate new session token
                new_token = terminal.generate_session_token(expiry_hours=24)
                
                return JsonResponse({
                    'valid': True,
                    'terminal': {
                        'id': str(terminal.id),
                        'code': terminal.terminal_code,
                        'name': terminal.terminal_name,
                        'type': terminal.device_type,
                        'store_id': str(terminal.store.id),
                        'store_name': terminal.store.store_name,
                        'brand_id': str(brand.id) if brand else None,
                        'brand_name': brand.name if brand else None,
                    },
                    'session_token': str(new_token),
                    'token_expires_at': terminal.token_expires_at.isoformat()
                })
            
        except POSTerminal.DoesNotExist:
            return JsonResponse({
                'valid': False,
                'error': 'Terminal not found or inactive'
            }, status=404)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'valid': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'valid': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def terminal_heartbeat(request):
    """
    Terminal heartbeat to keep session alive
    POST /api/terminal/heartbeat
    Body: {"terminal_code": "BOE-001"}
    """
    try:
        data = json.loads(request.body)
        terminal_code = data.get('terminal_code')
        
        if not terminal_code:
            return JsonResponse({
                'success': False,
                'error': 'terminal_code required'
            }, status=400)
        
        try:
            terminal = POSTerminal.objects.get(
                terminal_code=terminal_code,
                is_active=True
            )
            
            # Update last heartbeat and last_seen
            terminal.last_heartbeat = timezone.now()
            terminal.last_seen = timezone.now()
            terminal.save(update_fields=['last_heartbeat', 'last_seen'])
            
            return JsonResponse({
                'success': True,
                'timestamp': timezone.now().isoformat(),
                'is_online': terminal.is_online
            })
            
        except POSTerminal.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Terminal not found or inactive'
            }, status=404)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_terminal_config(request):
    """
    Get terminal device configuration
    GET /api/terminal/config?terminal_code=BOE-001&company_code=YOGYA&brand_code=BOE&store_code=KPT
    """
    try:
        terminal_code = request.GET.get('terminal_code')
        company_code = request.GET.get('company_code')
        brand_code = request.GET.get('brand_code')
        store_code = request.GET.get('store_code')
        
        if not terminal_code:
            return JsonResponse({
                'success': False,
                'error': 'terminal_code parameter required'
            }, status=400)
        
        try:
            # Build query filters
            query_filters = {
                'terminal_code': terminal_code,
                'is_active': True
            }
            
            # Add optional filters for more specific matching
            if company_code:
                query_filters['store__company__code'] = company_code
            if brand_code:
                query_filters['brand__code'] = brand_code
            if store_code:
                query_filters['store__store_code'] = store_code
            
            terminal = POSTerminal.objects.select_related('store', 'store__company', 'brand').get(
                **query_filters
            )
            
            # Get brand (may be None for stores without brands)
            brand = terminal.brand if terminal.brand else terminal.store.get_primary_brand()
            
            # Build device configuration
            device_config = {
                # Printer Configuration
                'printer_type': terminal.printer_type,
                'receipt_printer_name': terminal.receipt_printer_name or '',
                'receipt_paper_width': terminal.receipt_paper_width,
                'kitchen_printer_name': terminal.kitchen_printer_name or '',
                'print_logo_on_receipt': terminal.print_logo_on_receipt,
                'auto_print_receipt': terminal.auto_print_receipt,
                'auto_print_kitchen_order': terminal.auto_print_kitchen_order,
                'print_to': terminal.print_to,  # printer or file (for development)
                
                # Hardware Configuration
                'cash_drawer_enabled': terminal.cash_drawer_enabled,
                'barcode_scanner_enabled': terminal.barcode_scanner_enabled,
                'customer_pole_display_enabled': terminal.customer_pole_display_enabled,
                
                # Display Configuration
                'enable_customer_display': terminal.enable_customer_display,
                'enable_kitchen_display': terminal.enable_kitchen_display,
                'enable_kitchen_printer': terminal.enable_kitchen_printer,
                
                # Payment Configuration
                'default_payment_methods': terminal.default_payment_methods or [],
                'edc_integration_mode': terminal.edc_integration_mode,
            }
            
            return JsonResponse({
                'success': True,
                'terminal': {
                    'id': str(terminal.id),
                    'code': terminal.terminal_code,
                    'name': terminal.terminal_name,
                    'type': terminal.device_type,
                    'store_id': str(terminal.store.id),
                    'store_code': terminal.store.store_code,
                    'store_name': terminal.store.store_name,
                    'brand_id': str(brand.id) if brand else None,
                    'brand_code': brand.code if brand else None,
                    'brand_name': brand.name if brand else None,
                    'company_id': str(terminal.store.company.id),
                    'company_code': terminal.store.company.code,
                    'company_name': terminal.store.company.name,
                    'device_config': device_config
                }
            })
            
        except POSTerminal.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Terminal not found or inactive'
            }, status=404)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_receipt_template(request):
    """
    Get receipt template for terminal
    GET /api/terminal/receipt-template?terminal_code=BOE-001&company_code=YOGYA&brand_code=BOE&store_code=KPT
    """
    try:
        terminal_code = request.GET.get('terminal_code')
        company_code = request.GET.get('company_code')
        brand_code = request.GET.get('brand_code')
        store_code = request.GET.get('store_code')
        
        if not terminal_code:
            return JsonResponse({
                'success': False,
                'error': 'terminal_code parameter required'
            }, status=400)
        
        try:
            # Build query filters
            query_filters = {
                'terminal_code': terminal_code,
                'is_active': True
            }
            
            # Add optional filters for more specific matching
            if company_code:
                query_filters['store__company__code'] = company_code
            if brand_code:
                query_filters['brand__code'] = brand_code
            if store_code:
                query_filters['store__store_code'] = store_code
            
            # Get terminal to find brand/store
            terminal = POSTerminal.objects.select_related('store', 'brand').get(
                **query_filters
            )
            
            brand = terminal.brand if terminal.brand else terminal.store.get_primary_brand()
            
            # Query receipt template from database
            with connection.cursor() as cursor:
                # Try to find template: 1) by brand, 2) by store, 3) by company
                cursor.execute("""
                    SELECT 
                        id, template_name, paper_width, show_logo,
                        header_line_1, header_line_2, header_line_3, header_line_4,
                        show_receipt_number, show_date_time, show_cashier_name,
                        show_customer_name, show_table_number, show_item_code,
                        show_item_category, show_modifiers, price_alignment,
                        show_currency_symbol, show_subtotal, show_tax,
                        show_service_charge, show_discount, show_payment_method,
                        show_paid_amount, show_change,
                        footer_line_1, footer_line_2, footer_line_3,
                        show_qr_payment, auto_print, auto_cut, feed_lines
                    FROM core_receipttemplate
                    WHERE is_active = true
                    AND (
                        brand_id = %s OR
                        store_id = %s OR
                        company_id = %s
                    )
                    ORDER BY 
                        CASE 
                            WHEN brand_id = %s THEN 1
                            WHEN store_id = %s THEN 2
                            ELSE 3
                        END
                    LIMIT 1
                """, [
                    str(brand.id) if brand else None,
                    str(terminal.store.id),
                    str(terminal.store.company.id),
                    str(brand.id) if brand else None,
                    str(terminal.store.id)
                ])
                
                row = cursor.fetchone()
                
                if not row:
                    return JsonResponse({
                        'success': False,
                        'error': 'No receipt template found'
                    }, status=404)
                
                # Build template dict
                template = {
                    'id': row[0],
                    'template_name': row[1],
                    'paper_width': row[2],
                    'show_logo': row[3],
                    'header_line_1': row[4],
                    'header_line_2': row[5],
                    'header_line_3': row[6],
                    'header_line_4': row[7],
                    'show_receipt_number': row[8],
                    'show_date_time': row[9],
                    'show_cashier_name': row[10],
                    'show_customer_name': row[11],
                    'show_table_number': row[12],
                    'show_item_code': row[13],
                    'show_item_category': row[14],
                    'show_modifiers': row[15],
                    'price_alignment': row[16],
                    'show_currency_symbol': row[17],
                    'show_subtotal': row[18],
                    'show_tax': row[19],
                    'show_service_charge': row[20],
                    'show_discount': row[21],
                    'show_payment_method': row[22],
                    'show_paid_amount': row[23],
                    'show_change': row[24],
                    'footer_line_1': row[25],
                    'footer_line_2': row[26],
                    'footer_line_3': row[27],
                    'show_qr_payment': row[28],
                    'auto_print': row[29],
                    'auto_cut': row[30],
                    'feed_lines': row[31],
                }
                
                return JsonResponse({
                    'success': True,
                    'template': template
                })
            
        except POSTerminal.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Terminal not found or inactive'
            }, status=404)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
