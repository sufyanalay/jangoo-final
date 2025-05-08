from rest_framework import serializers

class ChatMessageSerializer(serializers.Serializer):
    sender_id = serializers.CharField()
    sender_name = serializers.CharField()
    content = serializers.CharField()
    file_url = serializers.CharField(required=False, allow_blank=True)
    file_type = serializers.ChoiceField(choices=['image', 'document'], required=False, allow_blank=True)
    timestamp = serializers.DateTimeField()

class ChatRoomSerializer(serializers.Serializer):
    id = serializers.CharField(source='_id')
    user1_id = serializers.CharField(source='user1.id')
    user1_name = serializers.SerializerMethodField()
    user2_id = serializers.CharField(source='user2.id')
    user2_name = serializers.SerializerMethodField()
    messages = ChatMessageSerializer(many=True)
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    service_type = serializers.CharField()
    service_id = serializers.CharField()
    
    def get_user1_name(self, obj):
        return f"{obj.user1.first_name} {obj.user1.last_name}"
    
    def get_user2_name(self, obj):
        return f"{obj.user2.first_name} {obj.user2.last_name}"

class ChatRoomCreateSerializer(serializers.Serializer):
    user2_id = serializers.CharField()
    service_type = serializers.ChoiceField(choices=['repair', 'academic', 'general'])
    service_id = serializers.CharField(required=False, allow_blank=True)
    
    def create(self, validated_data):
        from chat.models import ChatRoom
        from users.models import MongoUser
        import datetime
        
        user1_id = self.context['request'].user.id
        user1 = MongoUser.objects(user_id=str(user1_id)).first()
        
        user2 = MongoUser.objects(id=validated_data['user2_id']).first()
        if not user2:
            raise serializers.ValidationError(f"User with ID {validated_data['user2_id']} not found")
        
        # Check if a chat room already exists between these users
        existing_room = ChatRoom.objects(
            (Q(user1=user1) & Q(user2=user2)) | 
            (Q(user1=user2) & Q(user2=user1))
        ).first()
        
        if existing_room:
            return existing_room
        
        now = datetime.datetime.now()
        
        chat_room = ChatRoom(
            user1=user1,
            user2=user2,
            messages=[],
            is_active=True,
            service_type=validated_data['service_type'],
            service_id=validated_data.get('service_id', ''),
            created_at=now,
            updated_at=now
        )
        
        chat_room.save()
        return chat_room