import json
import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from mongoengine.queryset.visitor import Q

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type', 'message')
        
        if message_type == 'message':
            sender_id = text_data_json['sender_id']
            content = text_data_json['content']
            file_url = text_data_json.get('file_url', '')
            file_type = text_data_json.get('file_type', '')
            
            # Save message to database
            timestamp = await self.save_message(
                self.room_id, 
                sender_id, 
                content, 
                file_url, 
                file_type
            )
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'sender_id': sender_id,
                    'sender_name': text_data_json.get('sender_name', ''),
                    'content': content,
                    'file_url': file_url,
                    'file_type': file_type,
                    'timestamp': timestamp.isoformat()
                }
            )
        
        elif message_type == 'typing':
            # Send typing status to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_status',
                    'user_id': text_data_json['user_id'],
                    'is_typing': text_data_json['is_typing']
                }
            )
    
    # Receive message from room group
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'content': event['content'],
            'file_url': event['file_url'],
            'file_type': event['file_type'],
            'timestamp': event['timestamp']
        }))
    
    # Receive typing status from room group
    async def typing_status(self, event):
        # Send typing status to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'is_typing': event['is_typing']
        }))
    
    @database_sync_to_async
    def save_message(self, room_id, sender_id, content, file_url='', file_type=''):
        from chat.models import ChatRoom, ChatMessage
        from users.models import MongoUser
        
        # Get the chat room
        chat_room = ChatRoom.objects(id=room_id).first()
        if not chat_room:
            raise ValueError(f"Chat room with ID {room_id} not found")
        
        # Get the sender
        mongo_user = MongoUser.objects(id=sender_id).first()
        if not mongo_user:
            mongo_user = MongoUser.objects(user_id=sender_id).first()
        
        if not mongo_user:
            raise ValueError(f"User with ID {sender_id} not found")
        
        # Create message
        timestamp = datetime.datetime.now()
        message = ChatMessage(
            sender_id=str(mongo_user.id),
            sender_name=f"{mongo_user.first_name} {mongo_user.last_name}",
            content=content,
            file_url=file_url,
            file_type=file_type if file_url else None,
            timestamp=timestamp
        )
        
        # Add message to chat room
        chat_room.messages.append(message)
        chat_room.updated_at = timestamp
        chat_room.save()
        
        return timestamp