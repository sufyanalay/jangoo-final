from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from mongoengine.queryset.visitor import Q

from .models import ChatRoom
from .serializers import ChatRoomSerializer, ChatRoomCreateSerializer
from users.models import MongoUser

class ChatRoomViewSet(viewsets.ViewSet):
    def list(self, request):
        user_id = request.user.id
        mongo_user = MongoUser.objects(user_id=str(user_id)).first()
        
        # Get all chat rooms where the user is a participant
        chat_rooms = ChatRoom.objects(Q(user1=mongo_user) | Q(user2=mongo_user))
        
        serialized_data = []
        for room in chat_rooms:
            serializer = ChatRoomSerializer(room)
            serialized_data.append(serializer.data)
        
        return Response(serialized_data)
    
    def create(self, request):
        serializer = ChatRoomCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            chat_room = serializer.create(serializer.validated_data)
            return Response(ChatRoomSerializer(chat_room).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def retrieve(self, request, pk=None):
        try:
            user_id = request.user.id
            mongo_user = MongoUser.objects(user_id=str(user_id)).first()
            
            chat_room = ChatRoom.objects(id=pk).first()
            if not chat_room:
                return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if user is a participant in this chat room
            if str(chat_room.user1.id) != str(mongo_user.id) and str(chat_room.user2.id) != str(mongo_user.id):
                return Response({"detail": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)
            
            serializer = ChatRoomSerializer(chat_room)
            return Response(serializer.data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)