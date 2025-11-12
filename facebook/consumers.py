import json
from channels.generic.websocket import AsyncWebsocketConsumer


class FacebookConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Get tenant schema from path (e.g. ws://yourdomain/ws/facebook/<tenant>/)
        self.tenant_schema = self.scope['url_route']['kwargs']['tenant_schema']
        self.group_name = f"tenant_{self.tenant_schema}"

        # Add user to the group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        print(f"✅ WebSocket connected: {self.group_name}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        print(f"❌ WebSocket disconnected: {self.group_name}")

    async def receive(self, text_data):
        data = json.loads(text_data)
        print(f"📩 Message received from frontend: {data}")

    async def send_notification(self, event):
        message = event['message']
        print(f"🚀 Sending to WebSocket: {message}")
        await self.send(text_data=json.dumps(message))
