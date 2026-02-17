from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path("ws/website/<str:schema_name>/", consumers.WebsiteConsumer.as_asgi()),
]
