from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.pos.urls', namespace='pos')),
    path('tables/', include('apps.tables.urls', namespace='tables')),
    path('kitchen/', include('apps.kitchen.urls', namespace='kitchen')),
    path('order/', include('apps.qr_order.urls', namespace='qr_order')),
    path('promotions/', include('apps.promotions.urls', namespace='promotions')),
    path('auth/', include('apps.core.urls', namespace='core')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
