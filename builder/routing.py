from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path("ws/workspace/<str:workspace_id>/", consumers.LiveEditConsumer.as_asgi()),
]
 