"""
Terminal detection middleware
Ensures all requests have valid terminal_id and injects terminal object into request
"""
from django.shortcuts import redirect
from django.urls import reverse
from apps.core.models import POSTerminal
import logging

logger = logging.getLogger(__name__)


class TerminalMiddleware:
    """Middleware to validate and inject terminal information"""
    
    # URLs that don't require terminal validation
    EXEMPT_URLS = [
        '/setup/',
        '/api/',
        '/login/',
        '/logout/',
        '/pin-login/',
        '/auth/',
        '/admin/',
        '/management/',  # Management interface for managers (no terminal required)
        '/static/',
        '/media/',
        '/order/',  # QR Order (guest access)
        '/',  # Root URL (for redirect)
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip exempt URLs
        is_exempt = any(request.path.startswith(url) for url in self.EXEMPT_URLS)
        if is_exempt:
            return self.get_response(request)
        
        # Get terminal ID from header (HTMX requests) or session
        terminal_id = request.headers.get('X-Terminal-ID') or request.session.get('terminal_id')
        
        if not terminal_id:
            # No terminal ID - redirect to setup
            logger.warning(f'No terminal ID for path: {request.path}, user: {request.user}')
            return redirect('core:terminal_setup')
        
        # Validate terminal exists and is active
        try:
            terminal = POSTerminal.objects.select_related('store', 'store__brand', 'store__brand__company').get(
                id=terminal_id,
                is_active=True
            )
            
            # Inject terminal into request
            request.terminal = terminal
            request.store = terminal.store
            
            # Store in session for non-HTMX requests
            request.session['terminal_id'] = str(terminal.id)
            
            # Update heartbeat every request (or periodically in JS)
            # Commented to avoid too frequent updates, use JS heartbeat instead
            # terminal.update_heartbeat(self.get_client_ip(request))
            
        except POSTerminal.DoesNotExist:
            logger.error(f'Invalid terminal ID: {terminal_id}')
            # Clear only terminal-related session data, preserve user session
            if 'terminal_id' in request.session:
                del request.session['terminal_id']
            # Don't force session.modified = True here, let Django handle it
            return redirect('core:terminal_setup')
        
        response = self.get_response(request)
        return response
    
    @staticmethod
    def get_client_ip(request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
