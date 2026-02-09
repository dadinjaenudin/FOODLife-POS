from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.http import JsonResponse
from apps.core.models import Store
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

def smart_home_redirect(request):
    """Smart redirect based on Edge Server setup status"""
    print("=== SMART HOME REDIRECT ===")
    print(f"Path: {request.path}")
    print(f"User authenticated: {request.user.is_authenticated}")
    print(f"User: {request.user}")

    store_count = Store.objects.count()
    print(f"Store count: {store_count}")

    if not store_count:
        print("Redirecting to /setup/ - Store not configured")
        return redirect('/setup/')

    if request.user.is_authenticated:
        print("Redirecting to /management/ - Authenticated user")
        return redirect('/management/')

    print("Redirecting to /login/ - Not authenticated")
    return redirect('/login/')

def api_auth_token_stub(request):
    """Stub endpoint to prevent 404 from browser extensions trying to authenticate"""
    return JsonResponse({'detail': 'Not implemented'}, status=501)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', smart_home_redirect, name='home'),
    
    # JWT Authentication endpoints
    path('api/v1/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Terminal validation API
    path('api/', include('apps.core.urls_api')),
    
    path('api/auth/token/', api_auth_token_stub, name='api_auth_token_stub'),
    path('api/print/', include('apps.pos.print_urls')),
    #path('api/v1/core/', include('apps.core.api.urls')),
    path('pos/', include('apps.pos.urls', namespace='pos')),
    path('tables/', include('apps.tables.urls', namespace='tables')),
    path('kitchen/', include('apps.kitchen.urls', namespace='kitchen')),
    path('order/', include('apps.qr_order.urls', namespace='qr_order')),
    path('promotions/', include('apps.promotions.urls', namespace='promotions')),
    path('management/', include('apps.management.urls', namespace='management')),
    path('', include('apps.core.urls', namespace='core')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Static files are automatically served by django.contrib.staticfiles when DEBUG=True
    # No need to add static() for STATIC_URL in development
