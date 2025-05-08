from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from mongoengine.queryset.visitor import Q

from .models import Resource, ResourceBookmark
from .serializers import ResourceSerializer, ResourceBookmarkSerializer
from users.models import MongoUser

class ResourceViewSet(viewsets.ViewSet):
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'search']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]
    
    def list(self, request):
        # Get query parameters
        category = request.query_params.get('category')
        subject = request.query_params.get('subject')
        resource_type = request.query_params.get('resource_type')
        
        # Build query
        query = {}
        if category:
            query['category'] = category
        if subject:
            query['subject'] = subject
        if resource_type:
            query['resource_type'] = resource_type
        
        resources = Resource.objects(**query).order_by('-created_at')
        
        serialized_data = []
        for resource in resources:
            serializer = ResourceSerializer(resource, context={'request': request})
            serialized_data.append(serializer.data)
        
        return Response(serialized_data)
    
    def create(self, request):
        # Only teachers and technicians can create resources
        if request.user.user_type not in ['teacher', 'technician']:
            return Response({"detail": "Only teachers and technicians can create resources"}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ResourceSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            resource = serializer.create(serializer.validated_data)
            return Response(ResourceSerializer(resource, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def retrieve(self, request, pk=None):
        try:
            resource = Resource.objects(id=pk).first()
            if not resource:
                return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Increment view count
            resource.views += 1
            resource.save()
            
            serializer = ResourceSerializer(resource, context={'request': request})
            return Response(serializer.data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, pk=None):
        try:
            resource = Resource.objects(id=pk).first()
            if not resource:
                return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if user is the author
            user_id = request.user.id
            mongo_user = MongoUser.objects(user_id=str(user_id)).first()
            
            if str(resource.author.id) != str(mongo_user.id):
                return Response({"detail": "Only the author can update this resource"}, status=status.HTTP_403_FORBIDDEN)
            
            serializer = ResourceSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                updated_resource = serializer.update(resource, serializer.validated_data)
                return Response(ResourceSerializer(updated_resource, context={'request': request}).data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, pk=None):
        try:
            resource = Resource.objects(id=pk).first()
            if not resource:
                return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if user is the author
            user_id = request.user.id
            mongo_user = MongoUser.objects(user_id=str(user_id)).first()
            
            if str(resource.author.id) != str(mongo_user.id):
                return Response({"detail": "Only the author can delete this resource"}, status=status.HTTP_403_FORBIDDEN)
            
            resource.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')
        if not query:
            return Response({"detail": "Search query is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Search in title, description, and tags
        resources = Resource.objects(
            Q(title__icontains=query) | 
            Q(description__icontains=query) | 
            Q(tags__icontains=query)
        ).order_by('-created_at')
        
        serialized_data = []
        for resource in resources:
            serializer = ResourceSerializer(resource, context={'request': request})
            serialized_data.append(serializer.data)
        
        return Response(serialized_data)


class ResourceBookmarkViewSet(viewsets.ViewSet):
    def list(self, request):
        user_id = request.user.id
        mongo_user = MongoUser.objects(user_id=str(user_id)).first()
        
        # Get all bookmarks for this user
        bookmarks = ResourceBookmark.objects(user=mongo_user)
        
        # Get the resources
        resources = [bookmark.resource for bookmark in bookmarks]
        
        serialized_data = []
        for resource in resources:
            serializer = ResourceSerializer(resource, context={'request': request})
            serialized_data.append(serializer.data)
        
        return Response(serialized_data)
    
    def create(self, request):
        serializer = ResourceBookmarkSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            bookmark = serializer.create(serializer.validated_data)
            return Response({"detail": "Resource bookmarked successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, pk=None):
        try:
            user_id = request.user.id
            mongo_user = MongoUser.objects(user_id=str(user_id)).first()
            
            resource = Resource.objects(id=pk).first()
            if not resource:
                return Response({"detail": "Resource not found"}, status=status.HTTP_404_NOT_FOUND)
            
            bookmark = ResourceBookmark.objects(user=mongo_user, resource=resource).first()
            if not bookmark:
                return Response({"detail": "Bookmark not found"}, status=status.HTTP_404_NOT_FOUND)
            
            bookmark.delete()
            return Response({"detail": "Bookmark removed successfully"}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)