import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_fnb.settings')

django_asgi_app = get_asgi_application()

from apps.kitchen.consumers import KDSConsumer, POSConsumer

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path("ws/kds/<str:brand_id>/", KDSConsumer.as_asgi()),
            path("ws/pos/<str:brand_id>/", POSConsumer.as_asgi()),
        ])
    ),
})
