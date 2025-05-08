from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from mongoengine.queryset.visitor import Q

from .models import RepairRequest, RepairSolution
from .serializers import (
    RepairRequestCreateSerializer,
    RepairRequestUpdateSerializer,
    RepairRequestDetailSerializer,
    RepairMessageCreateSerializer,
    RepairSolutionSerializer
)
from users.models import MongoUser

class RepairRequestViewSet(viewsets.ViewSet):
    def get_permissions(self):
        if self.action == 'list_technicians':
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]
    
    def list(self, request):
        user_id = request.user.id
        mongo_user = MongoUser.objects(user_id=str(user_id)).first()
        
        # Filter requests based on user role
        if request.user.user_type == 'student':
            repair_requests = RepairRequest.objects(student=mongo_user)
        elif request.user.user_type == 'technician':
            # Technicians see both assigned requests and unassigned requests they can take
            assigned_requests = RepairRequest.objects(technician=mongo_user)
            unassigned_requests = RepairRequest.objects(technician=None, status='pending')
            repair_requests = list(assigned_requests) + list(unassigned_requests)
        else:
            return Response({"detail": "Unauthorized user type"}, status=status.HTTP_403_FORBIDDEN)
        
        # Serialize the data
        serialized_data = []
        for request_obj in repair_requests:
            serializer = RepairRequestDetailSerializer(request_obj)
            serialized_data.append(serializer.data)
        
        return Response(serialized_data)
    
    def create(self, request):
        if request.user.user_type != 'student':
            return Response({"detail": "Only students can create repair requests"}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = RepairRequestCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            repair_request = serializer.create(serializer.validated_data)
            return Response(RepairRequestDetailSerializer(repair_request).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def retrieve(self, request, pk=None):
        try:
            repair_request = RepairRequest.objects(id=pk).first()
            if not repair_request:
                return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if user is authorized to view this request
            user_id = request.user.id
            mongo_user = MongoUser.objects(user_id=str(user_id)).first()
            
            is_student_owner = str(repair_request.student.id) == str(mongo_user.id)
            is_assigned_technician = repair_request.technician and str(repair_request.technician.id) == str(mongo_user.id)
            is_unassigned_technician = request.user.user_type == 'technician' and not repair_request.technician
            
            if not (is_student_owner or is_assigned_technician or is_unassigned_technician):
                return Response({"detail": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)
            
            serializer = RepairRequestDetailSerializer(repair_request)
            return Response(serializer.data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, pk=None):
        try:
            repair_request = RepairRequest.objects(id=pk).first()
            if not repair_request:
                return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if user is authorized to update this request
            user_id = request.user.id
            mongo_user = MongoUser.objects(user_id=str(user_id)).first()
            
            is_student_owner = str(repair_request.student.id) == str(mongo_user.id)
            is_assigned_technician = repair_request.technician and str(repair_request.technician.id) == str(mongo_user.id)
            
            # Student can only update their own requests that are pending
            if request.user.user_type == 'student' and (not is_student_owner or repair_request.status != 'pending'):
                return Response({"detail": "Students can only update their own pending requests"}, status=status.HTTP_403_FORBIDDEN)
            
            # Technician can only update requests they're assigned to or take unassigned requests
            if request.user.user_type == 'technician' and not (is_assigned_technician or (not repair_request.technician and repair_request.status == 'pending')):
                return Response({"detail": "Technicians can only update assigned requests or take unassigned ones"}, status=status.HTTP_403_FORBIDDEN)
            
            # Handle technician assignment
            if request.user.user_type == 'technician' and not repair_request.technician and repair_request.status == 'pending':
                request.data['technician_id'] = str(mongo_user.id)
            
            serializer = RepairRequestUpdateSerializer(data=request.data)
            if serializer.is_valid():
                updated_request = serializer.update(repair_request, serializer.validated_data)
                return Response(RepairRequestDetailSerializer(updated_request).data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def add_message(self, request, pk=None):
        try:
            serializer = RepairMessageCreateSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                message = serializer.create(serializer.validated_data, pk)
                return Response(RepairMessageCreateSerializer(message).data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def list_technicians(self, request):
        # Get all technicians for student to view
        technicians = MongoUser.objects(user_type='technician')
        
        technician_list = []
        for tech in technicians:
            from users.models import ExpertProfile
            profile = ExpertProfile.objects(user=tech).first()
            technician_list.append({
                'id': str(tech.id),
                'name': f"{tech.first_name} {tech.last_name}",
                'expertise_areas': profile.expertise_areas if profile else "",
                'experience_years': profile.experience_years if profile else "0",
                'hourly_rate': profile.hourly_rate if profile else "0",
                'rating': profile.rating if profile else "0.0",
                'completed_services': profile.completed_services if profile else "0"
            })
        
        return Response(technician_list)


class RepairSolutionViewSet(viewsets.ViewSet):
    def create(self, request):
        if request.user.user_type != 'technician':
            return Response({"detail": "Only technicians can provide solutions"}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = RepairSolutionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            solution = serializer.create(serializer.validated_data)
            return Response(RepairSolutionSerializer(solution).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def retrieve(self, request, pk=None):
        try:
            repair_request = RepairRequest.objects(id=pk).first()
            if not repair_request:
                return Response({"detail": "Repair request not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Check authorization
            user_id = request.user.id
            mongo_user = MongoUser.objects(user_id=str(user_id)).first()
            
            is_student_owner = str(repair_request.student.id) == str(mongo_user.id)
            is_assigned_technician = repair_request.technician and str(repair_request.technician.id) == str(mongo_user.id)
            
            if not (is_student_owner or is_assigned_technician):
                return Response({"detail": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)
            
            # Look up solution for this repair request
            solution = RepairSolution.objects(repair_request=repair_request).first()
            if not solution:
                return Response({"detail": "No solution found for this repair request"}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = RepairSolutionSerializer(solution)
            return Response(serializer.data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)