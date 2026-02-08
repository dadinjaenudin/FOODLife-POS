"""
Terminal API Endpoints
Handles terminal validation and heartbeat
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import POSTerminal
import json


@csrf_exempt
@require_http_methods(["POST"])
def validate_terminal(request):
    """
    Validate terminal credentials
    POST /api/terminal/validate
    Body: {"terminal_code": "BOE-001", "session_token": "uuid"}
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
            terminal = POSTerminal.objects.select_related('store', 'store__brand').get(
                terminal_code=terminal_code,
                is_active=True
            )
            
            # Validate session token if provided
            if session_token:
                if str(terminal.session_token) != session_token:
                    return JsonResponse({
                        'valid': False,
                        'error': 'Invalid session token'
                    }, status=401)
                
                # Check if token expired
                if terminal.token_expires_at and terminal.token_expires_at < timezone.now():
                    return JsonResponse({
                        'valid': False,
                        'error': 'Session token expired'
                    }, status=401)
            
            return JsonResponse({
                'valid': True,
                'terminal': {
                    'id': str(terminal.id),
                    'code': terminal.terminal_code,
                    'name': terminal.terminal_name,
                    'type': terminal.terminal_type,
                    'store_id': str(terminal.store.id),
                    'store_name': terminal.store.store_name,
                    'brand_id': str(terminal.store.brand.id),
                    'brand_name': terminal.store.brand.name,
                }
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
            
            # Update last seen
            terminal.last_seen = timezone.now()
            terminal.save(update_fields=['last_seen'])
            
            return JsonResponse({
                'success': True,
                'timestamp': timezone.now().isoformat()
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
