import json
from channels.generic.websocket import AsyncWebsocketConsumer


class KDSConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.brand_id = self.scope['url_route']['kwargs']['brand_id']
        self.room_group_name = f'kds_{self.brand_id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def new_order(self, event):
        await self.send(text_data=json.dumps({
            'type': 'new_order',
            'order_id': event['order_id'],
            'station': event['station'],
        }))
    
    async def order_ready(self, event):
        await self.send(text_data=json.dumps({
            'type': 'order_ready',
            'order_id': event['order_id'],
            'table': event['table'],
        }))


class POSConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.brand_id = self.scope['url_route']['kwargs']['brand_id']
        self.room_group_name = f'pos_{self.brand_id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def order_ready(self, event):
        await self.send(text_data=json.dumps({
            'type': 'order_ready',
            'order_id': event['order_id'],
            'table': event['table'],
        }))
