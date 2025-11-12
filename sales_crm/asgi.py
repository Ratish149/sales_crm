import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import facebook.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sales_crm.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            facebook.routing.websocket_urlpatterns
        )
    ),
})
