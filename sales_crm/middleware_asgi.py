from channels.db import database_sync_to_async
from django.db import connection


class TenantWebsocketMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            schema_name = (
                scope.get("url_route", {}).get("kwargs", {}).get("schema_name")
            )
            if schema_name:
                await self.set_schema(schema_name)

        return await self.inner(scope, receive, send)

    @database_sync_to_async
    def set_schema(self, schema_name):
        from django.db import close_old_connections

        from tenants.models import Client

        close_old_connections()

        try:
            tenant = Client.objects.get(schema_name=schema_name)
            connection.set_tenant(tenant)
        except Client.DoesNotExist:
            connection.set_schema_to_public()
