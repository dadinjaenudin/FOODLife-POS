"""
Session safeguard middleware to prevent session loss
"""
import logging

logger = logging.getLogger(__name__)


class SessionSafeguardMiddleware:
    """
    Middleware to ensure sessions are properly maintained
    and debug session issues
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Log session info for debugging
        if request.user.is_authenticated:
            session_key = request.session.session_key
            logger.debug(f"User {request.user.username} - Session: {session_key} - Path: {request.path}")
            
            # Ensure session is marked as modified if user is authenticated
            # This helps prevent session expiry issues
            if not request.session.modified:
                # Touch the session to keep it alive
                request.session['_last_activity'] = str(request.path)
        
        response = self.get_response(request)
        
        # Ensure session cookie is set properly in response
        if request.user.is_authenticated and hasattr(request, 'session'):
            # Make sure session is saved
            if request.session.modified or '_last_activity' in request.session:
                request.session.save()
        
        return response
