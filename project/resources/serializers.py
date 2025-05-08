from rest_framework import serializers
import datetime

class ResourceSerializer(serializers.Serializer):
    id = serializers.CharField(source='_id', read_only=True)
    title = serializers.CharField(max_length=200)
    description = serializers.CharField()
    resource_type = serializers.ChoiceField(choices=['video', 'document', 'tutorial', 'guide'])
    category = serializers.ChoiceField(choices=['repair', 'academic'])
    subject = serializers.CharField()
    file_url = serializers.CharField()
    thumbnail_url = serializers.CharField(required=False, allow_blank=True)
    author_id = serializers.CharField(read_only=True)
    author_name = serializers.SerializerMethodField(read_only=True)
    is_premium = serializers.BooleanField(default=False)
    views = serializers.IntegerField(read_only=True)
    tags = serializers.ListField(child=serializers.CharField(), required=False)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    is_bookmarked = serializers.SerializerMethodField(read_only=True)
    
    def get_author_name(self, obj):
        return f"{obj.author.first_name} {obj.author.last_name}"
    
    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        from resources.models import ResourceBookmark
        from users.models import MongoUser
        
        mongo_user = MongoUser.objects(user_id=str(request.user.id)).first()
        if not mongo_user:
            return False
        
        return ResourceBookmark.objects(user=mongo_user, resource=obj).first() is not None
    
    def create(self, validated_data):
        from resources.models import Resource
        from users.models import MongoUser
        
        user_id = self.context['request'].user.id
        mongo_user = MongoUser.objects(user_id=str(user_id)).first()
        
        now = datetime.datetime.now()
        
        resource = Resource(
            title=validated_data['title'],
            description=validated_data['description'],
            resource_type=validated_data['resource_type'],
            category=validated_data['category'],
            subject=validated_data['subject'],
            file_url=validated_data['file_url'],
            thumbnail_url=validated_data.get('thumbnail_url', ''),
            author=mongo_user,
            is_premium=validated_data.get('is_premium', False),
            views=0,
            tags=validated_data.get('tags', []),
            created_at=now,
            updated_at=now
        )
        
        resource.save()
        return resource
    
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.updated_at = datetime.datetime.now()
        instance.save()
        return instance

class ResourceBookmarkSerializer(serializers.Serializer):
    user_id = serializers.CharField(read_only=True)
    resource_id = serializers.CharField(write_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    
    def create(self, validated_data):
        from resources.models import ResourceBookmark, Resource
        from users.models import MongoUser
        
        user_id = self.context['request'].user.id
        mongo_user = MongoUser.objects(user_id=str(user_id)).first()
        
        resource_id = validated_data['resource_id']
        resource = Resource.objects(id=resource_id).first()
        if not resource:
            raise serializers.ValidationError(f"Resource with ID {resource_id} not found")
        
        # Check if bookmark already exists
        existing_bookmark = ResourceBookmark.objects(user=mongo_user, resource=resource).first()
        if existing_bookmark:
            return existing_bookmark
        
        bookmark = ResourceBookmark(
            user=mongo_user,
            resource=resource,
            created_at=datetime.datetime.now()
        )
        
        bookmark.save()
        return bookmark