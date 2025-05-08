from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from mongoengine.queryset.visitor import Q

from .models import AcademicQuestion, AcademicAnswer
from .serializers import (
    AcademicQuestionCreateSerializer,
    AcademicQuestionUpdateSerializer,
    AcademicQuestionDetailSerializer,
    AcademicMessageCreateSerializer,
    AcademicAnswerSerializer
)
from users.models import MongoUser

class AcademicQuestionViewSet(viewsets.ViewSet):
    def get_permissions(self):
        if self.action == 'list_teachers':
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]
    
    def list(self, request):
        user_id = request.user.id
        mongo_user = MongoUser.objects(user_id=str(user_id)).first()
        
        # Filter questions based on user role
        if request.user.user_type == 'student':
            academic_questions = AcademicQuestion.objects(student=mongo_user)
        elif request.user.user_type == 'teacher':
            # Teachers see both assigned questions and unassigned questions they can take
            assigned_questions = AcademicQuestion.objects(teacher=mongo_user)
            unassigned_questions = AcademicQuestion.objects(teacher=None, status='pending')
            academic_questions = list(assigned_questions) + list(unassigned_questions)
        else:
            return Response({"detail": "Unauthorized user type"}, status=status.HTTP_403_FORBIDDEN)
        
        # Serialize the data
        serialized_data = []
        for question_obj in academic_questions:
            serializer = AcademicQuestionDetailSerializer(question_obj)
            serialized_data.append(serializer.data)
        
        return Response(serialized_data)
    
    def create(self, request):
        if request.user.user_type != 'student':
            return Response({"detail": "Only students can create academic questions"}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = AcademicQuestionCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            academic_question = serializer.create(serializer.validated_data)
            return Response(AcademicQuestionDetailSerializer(academic_question).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def retrieve(self, request, pk=None):
        try:
            academic_question = AcademicQuestion.objects(id=pk).first()
            if not academic_question:
                return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if user is authorized to view this question
            user_id = request.user.id
            mongo_user = MongoUser.objects(user_id=str(user_id)).first()
            
            is_student_owner = str(academic_question.student.id) == str(mongo_user.id)
            is_assigned_teacher = academic_question.teacher and str(academic_question.teacher.id) == str(mongo_user.id)
            is_unassigned_teacher = request.user.user_type == 'teacher' and not academic_question.teacher
            
            if not (is_student_owner or is_assigned_teacher or is_unassigned_teacher):
                return Response({"detail": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)
            
            serializer = AcademicQuestionDetailSerializer(academic_question)
            return Response(serializer.data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, pk=None):
        try:
            academic_question = AcademicQuestion.objects(id=pk).first()
            if not academic_question:
                return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if user is authorized to update this question
            user_id = request.user.id
            mongo_user = MongoUser.objects(user_id=str(user_id)).first()
            
            is_student_owner = str(academic_question.student.id) == str(mongo_user.id)
            is_assigned_teacher = academic_question.teacher and str(academic_question.teacher.id) == str(mongo_user.id)
            
            # Student can only update their own questions that are pending
            if request.user.user_type == 'student' and (not is_student_owner or academic_question.status != 'pending'):
                return Response({"detail": "Students can only update their own pending questions"}, status=status.HTTP_403_FORBIDDEN)
            
            # Teacher can only update questions they're assigned to or take unassigned questions
            if request.user.user_type == 'teacher' and not (is_assigned_teacher or (not academic_question.teacher and academic_question.status == 'pending')):
                return Response({"detail": "Teachers can only update assigned questions or take unassigned ones"}, status=status.HTTP_403_FORBIDDEN)
            
            # Handle teacher assignment
            if request.user.user_type == 'teacher' and not academic_question.teacher and academic_question.status == 'pending':
                request.data['teacher_id'] = str(mongo_user.id)
            
            serializer = AcademicQuestionUpdateSerializer(data=request.data)
            if serializer.is_valid():
                updated_question = serializer.update(academic_question, serializer.validated_data)
                return Response(AcademicQuestionDetailSerializer(updated_question).data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def add_message(self, request, pk=None):
        try:
            serializer = AcademicMessageCreateSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                message = serializer.create(serializer.validated_data, pk)
                return Response(AcademicMessageCreateSerializer(message).data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def list_teachers(self, request):
        # Get all teachers for student to view
        teachers = MongoUser.objects(user_type='teacher')
        
        teacher_list = []
        for teacher in teachers:
            from users.models import ExpertProfile
            profile = ExpertProfile.objects(user=teacher).first()
            teacher_list.append({
                'id': str(teacher.id),
                'name': f"{teacher.first_name} {teacher.last_name}",
                'expertise_areas': profile.expertise_areas if profile else "",
                'experience_years': profile.experience_years if profile else "0",
                'hourly_rate': profile.hourly_rate if profile else "0",
                'rating': profile.rating if profile else "0.0",
                'completed_services': profile.completed_services if profile else "0"
            })
        
        return Response(teacher_list)


class AcademicAnswerViewSet(viewsets.ViewSet):
    def create(self, request):
        if request.user.user_type != 'teacher':
            return Response({"detail": "Only teachers can provide answers"}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = AcademicAnswerSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            answer = serializer.create(serializer.validated_data)
            return Response(AcademicAnswerSerializer(answer).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def retrieve(self, request, pk=None):
        try:
            academic_question = AcademicQuestion.objects(id=pk).first()
            if not academic_question:
                return Response({"detail": "Academic question not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Check authorization
            user_id = request.user.id
            mongo_user = MongoUser.objects(user_id=str(user_id)).first()
            
            is_student_owner = str(academic_question.student.id) == str(mongo_user.id)
            is_assigned_teacher = academic_question.teacher and str(academic_question.teacher.id) == str(mongo_user.id)
            
            if not (is_student_owner or is_assigned_teacher):
                return Response({"detail": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)
            
            # Look up answer for this question
            answer = AcademicAnswer.objects(question=academic_question).first()
            if not answer:
                return Response({"detail": "No answer found for this question"}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = AcademicAnswerSerializer(answer)
            return Response(serializer.data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)