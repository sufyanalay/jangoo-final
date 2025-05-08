from rest_framework import status, viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from mongoengine.queryset.visitor import Q

from .models import User, MongoUser, ExpertProfile, EarningRecord
from .serializers import (
    UserRegistrationSerializer, 
    UserLoginSerializer, 
    UserProfileSerializer,
    ExpertProfileSerializer,
    EarningRecordSerializer
)


class UserRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Create mirrored document in MongoDB
            mongo_user = MongoUser(
                user_id=str(user.id),
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                user_type=user.user_type,
                bio=user.bio if user.bio else "",
                profile_picture_url=user.profile_picture.url if user.profile_picture else "",
                date_joined=user.date_joined,
                is_expert=user.user_type in ['teacher', 'technician']
            )
            mongo_user.save()
            
            # If user is an expert (teacher or technician), create an expert profile
            if user.user_type in ['teacher', 'technician']:
                expert_profile = ExpertProfile(
                    user=mongo_user,
                    expertise_areas="",
                    experience_years="0",
                    hourly_rate="0",
                    availability_hours="9-17",
                )
                expert_profile.save()
            
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        
        # Return user profile along with tokens
        profile = UserProfileSerializer(user)
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': profile.data
        })


class UserProfileView(APIView):
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    
    def put(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            
            # Update mirrored MongoDB document
            mongo_user = MongoUser.objects(user_id=str(request.user.id)).first()
            if mongo_user:
                mongo_user.first_name = request.user.first_name
                mongo_user.last_name = request.user.last_name
                mongo_user.bio = request.user.bio if request.user.bio else ""
                mongo_user.profile_picture_url = request.user.profile_picture.url if request.user.profile_picture else ""
                mongo_user.save()
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ExpertProfileViewSet(viewsets.ViewSet):
    def retrieve(self, request):
        if request.user.user_type not in ['teacher', 'technician']:
            return Response({"detail": "Not an expert user"}, status=status.HTTP_403_FORBIDDEN)
        
        mongo_user = MongoUser.objects(user_id=str(request.user.id)).first()
        if not mongo_user:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        expert_profile = ExpertProfile.objects(user=mongo_user).first()
        if not expert_profile:
            return Response({"detail": "Expert profile not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ExpertProfileSerializer({
            'expertise_areas': expert_profile.expertise_areas,
            'experience_years': expert_profile.experience_years,
            'hourly_rate': expert_profile.hourly_rate,
            'availability_hours': expert_profile.availability_hours,
            'completed_services': expert_profile.completed_services,
            'rating': expert_profile.rating
        })
        return Response(serializer.data)
    
    def update(self, request):
        if request.user.user_type not in ['teacher', 'technician']:
            return Response({"detail": "Not an expert user"}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ExpertProfileSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        mongo_user = MongoUser.objects(user_id=str(request.user.id)).first()
        if not mongo_user:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        expert_profile = ExpertProfile.objects(user=mongo_user).first()
        if not expert_profile:
            return Response({"detail": "Expert profile not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Update profile fields
        expert_profile.expertise_areas = serializer.validated_data.get('expertise_areas', expert_profile.expertise_areas)
        expert_profile.experience_years = serializer.validated_data.get('experience_years', expert_profile.experience_years)
        expert_profile.hourly_rate = serializer.validated_data.get('hourly_rate', expert_profile.hourly_rate)
        expert_profile.availability_hours = serializer.validated_data.get('availability_hours', expert_profile.availability_hours)
        expert_profile.save()
        
        # Also update the expertise_areas in MongoUser for easier querying
        mongo_user.expertise_areas = expert_profile.expertise_areas
        mongo_user.save()
        
        return Response(serializer.data)


class EarningsDashboardView(APIView):
    def get(self, request):
        if request.user.user_type not in ['teacher', 'technician']:
            return Response({"detail": "Not an expert user"}, status=status.HTTP_403_FORBIDDEN)
        
        mongo_user = MongoUser.objects(user_id=str(request.user.id)).first()
        if not mongo_user:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Get all earnings for the expert
        earnings = EarningRecord.objects(expert=mongo_user)
        serializer = EarningRecordSerializer([
            {
                'amount': e.amount,
                'service_type': e.service_type,
                'service_id': e.service_id,
                'date': e.date,
                'is_paid': e.is_paid
            } for e in earnings
        ], many=True)
        
        # Calculate total earnings
        total_earnings = sum(float(e.amount) for e in earnings)
        paid_earnings = sum(float(e.amount) for e in earnings if e.is_paid)
        pending_earnings = total_earnings - paid_earnings
        
        # Get expert profile for service count
        expert_profile = ExpertProfile.objects(user=mongo_user).first()
        completed_services = int(expert_profile.completed_services) if expert_profile else 0
        
        return Response({
            'total_earnings': str(total_earnings),
            'paid_earnings': str(paid_earnings),
            'pending_earnings': str(pending_earnings),
            'completed_services': str(completed_services),
            'transactions': serializer.data
        })