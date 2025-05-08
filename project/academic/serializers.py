from rest_framework import serializers
import datetime

class AcademicMediaSerializer(serializers.Serializer):
    file_url = serializers.CharField()
    file_type = serializers.ChoiceField(choices=['image', 'video'])
    description = serializers.CharField(required=False, allow_blank=True)

class AcademicMessageSerializer(serializers.Serializer):
    sender_id = serializers.CharField()
    sender_name = serializers.CharField()
    sender_type = serializers.ChoiceField(choices=['student', 'teacher', 'system'])
    message = serializers.CharField()
    media_url = serializers.CharField(required=False, allow_blank=True)
    timestamp = serializers.DateTimeField()

class AcademicQuestionCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    subject = serializers.CharField()
    question_text = serializers.CharField()
    grade_level = serializers.CharField(required=False)
    media = AcademicMediaSerializer(many=True, required=False)
    
    def create(self, validated_data):
        from academic.models import AcademicQuestion
        from users.models import MongoUser
        import datetime
        
        user_id = self.context['request'].user.id
        mongo_user = MongoUser.objects(user_id=str(user_id)).first()
        
        media_data = validated_data.pop('media', [])
        now = datetime.datetime.now()
        
        academic_question = AcademicQuestion(
            student=mongo_user,
            title=validated_data['title'],
            subject=validated_data['subject'],
            question_text=validated_data['question_text'],
            grade_level=validated_data.get('grade_level', ''),
            status='pending',
            created_at=now,
            updated_at=now,
            messages=[],
            media=[]
        )
        
        # Add media if provided
        for media_item in media_data:
            from academic.models import AcademicMedia
            academic_media = AcademicMedia(
                file_url=media_item['file_url'],
                file_type=media_item['file_type'],
                description=media_item.get('description', '')
            )
            academic_question.media.append(academic_media)
        
        # Add initial system message
        from academic.models import AcademicMessage
        system_message = AcademicMessage(
            sender_id='system',
            sender_name='System',
            sender_type='system',
            message='Academic question created. Waiting for a teacher to assist.',
            timestamp=now
        )
        academic_question.messages.append(system_message)
        
        academic_question.save()
        return academic_question

class AcademicQuestionUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    subject = serializers.CharField(required=False)
    question_text = serializers.CharField(required=False)
    grade_level = serializers.CharField(required=False)
    status = serializers.ChoiceField(
        choices=['pending', 'assigned', 'in_progress', 'answered', 'closed'], 
        required=False
    )
    teacher_id = serializers.CharField(required=False)  # For assigning a teacher
    price_quote = serializers.CharField(required=False)
    payment_status = serializers.ChoiceField(choices=['unpaid', 'paid'], required=False)
    
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            if attr == 'teacher_id':
                from users.models import MongoUser
                teacher = MongoUser.objects(id=value).first()
                if not teacher:
                    raise serializers.ValidationError(f"Teacher with ID {value} not found")
                instance.teacher = teacher
                
                # Add system message about teacher assignment
                from academic.models import AcademicMessage
                message = AcademicMessage(
                    sender_id='system',
                    sender_name='System',
                    sender_type='system',
                    message=f'Teacher {teacher.first_name} {teacher.last_name} has been assigned to this question.',
                    timestamp=datetime.datetime.now()
                )
                instance.messages.append(message)
                
                # Update status if it's still pending
                if instance.status == 'pending':
                    instance.status = 'assigned'
            else:
                setattr(instance, attr, value)
        
        # If status is changing to answered, set answered_at
        if validated_data.get('status') == 'answered' and instance.status != 'answered':
            instance.answered_at = datetime.datetime.now()
            
            # Add system message about answer
            from academic.models import AcademicMessage
            message = AcademicMessage(
                sender_id='system',
                sender_name='System',
                sender_type='system',
                message='This question has been marked as answered.',
                timestamp=datetime.datetime.now()
            )
            instance.messages.append(message)
            
            # Update teacher's completed services count
            if instance.teacher:
                from users.models import ExpertProfile
                expert_profile = ExpertProfile.objects(user=instance.teacher).first()
                if expert_profile:
                    completed = int(expert_profile.completed_services)
                    expert_profile.completed_services = str(completed + 1)
                    expert_profile.save()
            
            # Create earning record if payment_status is paid
            if instance.payment_status == 'paid' and instance.teacher and instance.price_quote:
                from users.models import EarningRecord
                earning = EarningRecord(
                    expert=instance.teacher,
                    amount=instance.price_quote,
                    service_type='academic',
                    service_id=str(instance.id),
                    date=datetime.datetime.now(),
                    is_paid=True
                )
                earning.save()
        
        instance.updated_at = datetime.datetime.now()
        instance.save()
        return instance

class AcademicQuestionDetailSerializer(serializers.Serializer):
    id = serializers.CharField(source='_id')
    student_id = serializers.CharField(source='student.id')
    student_name = serializers.SerializerMethodField()
    teacher_id = serializers.SerializerMethodField()
    teacher_name = serializers.SerializerMethodField()
    title = serializers.CharField()
    subject = serializers.CharField()
    question_text = serializers.CharField()
    grade_level = serializers.CharField()
    media = AcademicMediaSerializer(many=True)
    messages = AcademicMessageSerializer(many=True)
    status = serializers.CharField()
    price_quote = serializers.CharField()
    payment_status = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    answered_at = serializers.DateTimeField(required=False)
    
    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}"
    
    def get_teacher_id(self, obj):
        return str(obj.teacher.id) if obj.teacher else None
    
    def get_teacher_name(self, obj):
        return f"{obj.teacher.first_name} {obj.teacher.last_name}" if obj.teacher else None

class AcademicMessageCreateSerializer(serializers.Serializer):
    message = serializers.CharField()
    media_url = serializers.CharField(required=False, allow_blank=True)
    
    def create(self, validated_data, question_id):
        from academic.models import AcademicQuestion, AcademicMessage
        from users.models import MongoUser
        
        user = self.context['request'].user
        mongo_user = MongoUser.objects(user_id=str(user.id)).first()
        
        question = AcademicQuestion.objects(id=question_id).first()
        if not question:
            raise serializers.ValidationError(f"Academic question with ID {question_id} not found")
        
        # Verify that the user is either the student or the assigned teacher
        if str(question.student.id) != str(mongo_user.id) and (
            not question.teacher or str(question.teacher.id) != str(mongo_user.id)
        ):
            raise serializers.ValidationError("You are not authorized to send messages for this question")
        
        message = AcademicMessage(
            sender_id=str(mongo_user.id),
            sender_name=f"{mongo_user.first_name} {mongo_user.last_name}",
            sender_type=mongo_user.user_type,
            message=validated_data['message'],
            media_url=validated_data.get('media_url', ''),
            timestamp=datetime.datetime.now()
        )
        
        question.messages.append(message)
        question.updated_at = datetime.datetime.now()
        question.save()
        
        return message

class AcademicAnswerSerializer(serializers.Serializer):
    question_id = serializers.CharField(write_only=True)
    answer_text = serializers.CharField()
    explanation = serializers.CharField()
    references = serializers.ListField(child=serializers.CharField(), required=False)
    media = AcademicMediaSerializer(many=True, required=False)
    
    def create(self, validated_data):
        from academic.models import AcademicAnswer, AcademicQuestion, AcademicMedia
        from users.models import MongoUser
        
        user = self.context['request'].user
        mongo_user = MongoUser.objects(user_id=str(user.id)).first()
        
        question_id = validated_data.pop('question_id')
        question = AcademicQuestion.objects(id=question_id).first()
        if not question:
            raise serializers.ValidationError(f"Academic question with ID {question_id} not found")
        
        # Verify that the user is the assigned teacher
        if not question.teacher or str(question.teacher.id) != str(mongo_user.id):
            raise serializers.ValidationError("Only the assigned teacher can create an answer")
        
        media_data = validated_data.pop('media', [])
        references = validated_data.pop('references', [])
        
        answer = AcademicAnswer(
            question=question,
            teacher=mongo_user,
            answer_text=validated_data['answer_text'],
            explanation=validated_data['explanation'],
            references=references,
            created_at=datetime.datetime.now(),
            media=[]
        )
        
        # Add media if provided
        for media_item in media_data:
            media = AcademicMedia(
                file_url=media_item['file_url'],
                file_type=media_item['file_type'],
                description=media_item.get('description', '')
            )
            answer.media.append(media)
        
        answer.save()
        
        # Update question status to answered
        question.status = 'answered'
        question.answered_at = datetime.datetime.now()
        
        # Add system message about answer
        from academic.models import AcademicMessage
        message = AcademicMessage(
            sender_id='system',
            sender_name='System',
            sender_type='system',
            message='An answer has been provided by the teacher.',
            timestamp=datetime.datetime.now()
        )
        question.messages.append(message)
        question.save()
        
        return answer