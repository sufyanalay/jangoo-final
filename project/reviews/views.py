from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from mongoengine.queryset.visitor import Q

from .models import Review
from .serializers import ReviewSerializer
from users.models import MongoUser

class ReviewViewSet(viewsets.ViewSet):
    def list(self, request):
        # Get query parameters
        expert_id = request.query_params.get('expert_id')
        service_type = request.query_params.get('service_type')
        
        # Build query
        query = {}
        if expert_id:
            expert = MongoUser.objects(id=expert_id).first()
            if not expert:
                return Response({"detail": f"Expert with ID {expert_id} not found"}, status=status.HTTP_404_NOT_FOUND)
            query['expert'] = expert
        if service_type:
            query['service_type'] = service_type
        
        reviews = Review.objects(**query).order_by('-created_at')
        
        serialized_data = []
        for review in reviews:
            serializer = ReviewSerializer(review)
            serialized_data.append(serializer.data)
        
        return Response(serialized_data)
    
    def create(self, request):
        serializer = ReviewSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            review = serializer.create(serializer.validated_data)
            return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def retrieve(self, request, pk=None):
        try:
            review = Review.objects(id=pk).first()
            if not review:
                return Response({"detail": "Review not found"}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = ReviewSerializer(review)
            return Response(serializer.data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def my_reviews(self, request):
        user_id = request.user.id
        mongo_user = MongoUser.objects(user_id=str(user_id)).first()
        
        # Get all reviews by this user
        reviews = Review.objects(user=mongo_user).order_by('-created_at')
        
        serialized_data = []
        for review in reviews:
            serializer = ReviewSerializer(review)
            serialized_data.append(serializer.data)
        
        return Response(serialized_data)
    
    @action(detail=False, methods=['get'])
    def expert_reviews(self, request):
        user_id = request.user.id
        mongo_user = MongoUser.objects(user_id=str(user_id)).first()
        
        # Only applicable for teachers and technicians
        if request.user.user_type not in ['teacher', 'technician']:
            return Response({"detail": "Only experts can view their reviews"}, status=status.HTTP_403_FORBIDDEN)
        
        # Get all reviews for this expert
        reviews = Review.objects(expert=mongo_user).order_by('-created_at')
        
        serialized_data = []
        for review in reviews:
            serializer = ReviewSerializer(review)
            serialized_data.append(serializer.data)
        
        return Response(serialized_data)