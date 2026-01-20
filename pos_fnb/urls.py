from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.http import JsonResponse

def smart_home_redirect(request):
    """Smart redirect based on user authentication and role"""
    if request.user.is_authenticated:
        # All authenticated users go to management dashboard
        return redirect('management:dashboard')
    # Not authenticated → go to login page
    return redirect('core:login')

def api_auth_token_stub(request):
    """Stub endpoint to prevent 404 from browser extensions trying to authenticate"""
    return JsonResponse({'detail': 'Not implemented'}, status=501)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', smart_home_redirect, name='home'),
    
    # Stub for browser extensions trying to authenticate
    path('api/auth/token/', api_auth_token_stub, name='api_auth_token_stub'),
    
    path('pos/', include('apps.pos.urls', namespace='pos')),
    path('tables/', include('apps.tables.urls', namespace='tables')),
    path('kitchen/', include('apps.kitchen.urls', namespace='kitchen')),
    path('order/', include('apps.qr_order.urls', namespace='qr_order')),
    path('promotions/', include('apps.promotions.urls', namespace='promotions')),
    path('management/', include('apps.management.urls', namespace='management')),  # Management Interface
    path('', include('apps.core.urls', namespace='core')),  # Includes /setup/ and /login/
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
