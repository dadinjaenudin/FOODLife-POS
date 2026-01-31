"""Debug view to check CSRF status"""
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie

@ensure_csrf_cookie
def csrf_test_page(request):
    """HTML page to test CSRF cookie status in browser"""
    return render(request, 'core/csrf_test.html')

@csrf_exempt
def csrf_debug(request):
    """Debug endpoint to check CSRF cookie and token status"""
    return JsonResponse({
        'method': request.method,
        'cookies_received': list(request.COOKIES.keys()),
        'csrftoken_cookie': request.COOKIES.get('csrftoken', 'NOT SET'),
        'csrf_cookie_from_meta': request.META.get('CSRF_COOKIE', 'NOT SET'),
        'session_key': request.session.session_key,
        'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown'),
        'referer': request.META.get('HTTP_REFERER', 'None'),
    })
