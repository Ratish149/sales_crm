import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

import builder.routing
import facebook.routing
import website.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sales_crm.settings")

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(
            URLRouter(
                facebook.routing.websocket_urlpatterns
                + builder.routing.websocket_urlpatterns
                + website.routing.websocket_urlpatterns
            )
        ),
    }
)
