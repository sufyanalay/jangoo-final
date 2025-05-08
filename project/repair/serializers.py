from rest_framework import serializers
import datetime

class RepairMediaSerializer(serializers.Serializer):
    file_url = serializers.CharField()
    file_type = serializers.ChoiceField(choices=['image', 'video'])
    description = serializers.CharField(required=False, allow_blank=True)

class RepairMessageSerializer(serializers.Serializer):
    sender_id = serializers.CharField()
    sender_name = serializers.CharField()
    sender_type = serializers.ChoiceField(choices=['student', 'technician', 'system'])
    message = serializers.CharField()
    media_url = serializers.CharField(required=False, allow_blank=True)
    timestamp = serializers.DateTimeField()

class RepairRequestCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    device_type = serializers.CharField()
    device_model = serializers.CharField()
    issue_description = serializers.CharField()
    media = RepairMediaSerializer(many=True, required=False)
    
    def create(self, validated_data):
        from repair.models import RepairRequest
        from users.models import MongoUser
        import datetime
        
        user_id = self.context['request'].user.id
        mongo_user = MongoUser.objects(user_id=str(user_id)).first()
        
        media_data = validated_data.pop('media', [])
        now = datetime.datetime.now()
        
        repair_request = RepairRequest(
            student=mongo_user,
            title=validated_data['title'],
            device_type=validated_data['device_type'],
            device_model=validated_data['device_model'],
            issue_description=validated_data['issue_description'],
            status='pending',
            created_at=now,
            updated_at=now,
            messages=[],
            media=[]
        )
        
        # Add media if provided
        for media_item in media_data:
            from repair.models import RepairMedia
            repair_media = RepairMedia(
                file_url=media_item['file_url'],
                file_type=media_item['file_type'],
                description=media_item.get('description', '')
            )
            repair_request.media.append(repair_media)
        
        # Add initial system message
        from repair.models import RepairMessage
        system_message = RepairMessage(
            sender_id='system',
            sender_name='System',
            sender_type='system',
            message='Repair request created. Waiting for a technician to assist.',
            timestamp=now
        )
        repair_request.messages.append(system_message)
        
        repair_request.save()
        return repair_request

class RepairRequestUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    device_type = serializers.CharField(required=False)
    device_model = serializers.CharField(required=False)
    issue_description = serializers.CharField(required=False)
    status = serializers.ChoiceField(
        choices=['pending', 'assigned', 'in_progress', 'completed', 'cancelled'], 
        required=False
    )
    technician_id = serializers.CharField(required=False)  # For assigning a technician
    price_quote = serializers.CharField(required=False)
    payment_status = serializers.ChoiceField(choices=['unpaid', 'paid'], required=False)
    
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            if attr == 'technician_id':
                from users.models import MongoUser
                technician = MongoUser.objects(id=value).first()
                if not technician:
                    raise serializers.ValidationError(f"Technician with ID {value} not found")
                instance.technician = technician
                
                # Add system message about technician assignment
                from repair.models import RepairMessage
                message = RepairMessage(
                    sender_id='system',
                    sender_name='System',
                    sender_type='system',
                    message=f'Technician {technician.first_name} {technician.last_name} has been assigned to this repair.',
                    timestamp=datetime.datetime.now()
                )
                instance.messages.append(message)
                
                # Update status if it's still pending
                if instance.status == 'pending':
                    instance.status = 'assigned'
            else:
                setattr(instance, attr, value)
        
        # If status is changing to completed, set completed_at
        if validated_data.get('status') == 'completed' and instance.status != 'completed':
            instance.completed_at = datetime.datetime.now()
            
            # Add system message about completion
            from repair.models import RepairMessage
            message = RepairMessage(
                sender_id='system',
                sender_name='System',
                sender_type='system',
                message='This repair request has been marked as completed.',
                timestamp=datetime.datetime.now()
            )
            instance.messages.append(message)
            
            # Update technician's completed services count
            if instance.technician:
                from users.models import ExpertProfile
                expert_profile = ExpertProfile.objects(user=instance.technician).first()
                if expert_profile:
                    completed = int(expert_profile.completed_services)
                    expert_profile.completed_services = str(completed + 1)
                    expert_profile.save()
            
            # Create earning record if payment_status is paid
            if instance.payment_status == 'paid' and instance.technician and instance.price_quote:
                from users.models import EarningRecord
                earning = EarningRecord(
                    expert=instance.technician,
                    amount=instance.price_quote,
                    service_type='repair',
                    service_id=str(instance.id),
                    date=datetime.datetime.now(),
                    is_paid=True
                )
                earning.save()
        
        instance.updated_at = datetime.datetime.now()
        instance.save()
        return instance

class RepairRequestDetailSerializer(serializers.Serializer):
    id = serializers.CharField(source='_id')
    student_id = serializers.CharField(source='student.id')
    student_name = serializers.SerializerMethodField()
    technician_id = serializers.SerializerMethodField()
    technician_name = serializers.SerializerMethodField()
    title = serializers.CharField()
    device_type = serializers.CharField()
    device_model = serializers.CharField()
    issue_description = serializers.CharField()
    media = RepairMediaSerializer(many=True)
    messages = RepairMessageSerializer(many=True)
    status = serializers.CharField()
    price_quote = serializers.CharField()
    payment_status = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(required=False)
    
    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}"
    
    def get_technician_id(self, obj):
        return str(obj.technician.id) if obj.technician else None
    
    def get_technician_name(self, obj):
        return f"{obj.technician.first_name} {obj.technician.last_name}" if obj.technician else None

class RepairMessageCreateSerializer(serializers.Serializer):
    message = serializers.CharField()
    media_url = serializers.CharField(required=False, allow_blank=True)
    
    def create(self, validated_data, repair_request_id):
        from repair.models import RepairRequest, RepairMessage
        from users.models import MongoUser
        
        user = self.context['request'].user
        mongo_user = MongoUser.objects(user_id=str(user.id)).first()
        
        repair_request = RepairRequest.objects(id=repair_request_id).first()
        if not repair_request:
            raise serializers.ValidationError(f"Repair request with ID {repair_request_id} not found")
        
        # Verify that the user is either the student or the assigned technician
        if str(repair_request.student.id) != str(mongo_user.id) and (
            not repair_request.technician or str(repair_request.technician.id) != str(mongo_user.id)
        ):
            raise serializers.ValidationError("You are not authorized to send messages for this repair request")
        
        message = RepairMessage(
            sender_id=str(mongo_user.id),
            sender_name=f"{mongo_user.first_name} {mongo_user.last_name}",
            sender_type=mongo_user.user_type,
            message=validated_data['message'],
            media_url=validated_data.get('media_url', ''),
            timestamp=datetime.datetime.now()
        )
        
        repair_request.messages.append(message)
        repair_request.updated_at = datetime.datetime.now()
        repair_request.save()
        
        return message

class RepairSolutionSerializer(serializers.Serializer):
    repair_request_id = serializers.CharField(write_only=True)
    solution_description = serializers.CharField()
    solution_steps = serializers.ListField(child=serializers.CharField())
    media = RepairMediaSerializer(many=True, required=False)
    is_successful = serializers.BooleanField(default=True)
    
    def create(self, validated_data):
        from repair.models import RepairSolution, RepairRequest, RepairMedia
        from users.models import MongoUser
        
        user = self.context['request'].user
        mongo_user = MongoUser.objects(user_id=str(user.id)).first()
        
        repair_request_id = validated_data.pop('repair_request_id')
        repair_request = RepairRequest.objects(id=repair_request_id).first()
        if not repair_request:
            raise serializers.ValidationError(f"Repair request with ID {repair_request_id} not found")
        
        # Verify that the user is the assigned technician
        if not repair_request.technician or str(repair_request.technician.id) != str(mongo_user.id):
            raise serializers.ValidationError("Only the assigned technician can create a solution")
        
        media_data = validated_data.pop('media', [])
        
        solution = RepairSolution(
            repair_request=repair_request,
            technician=mongo_user,
            solution_description=validated_data['solution_description'],
            solution_steps=validated_data['solution_steps'],
            is_successful=validated_data['is_successful'],
            created_at=datetime.datetime.now(),
            media=[]
        )
        
        # Add media if provided
        for media_item in media_data:
            media = RepairMedia(
                file_url=media_item['file_url'],
                file_type=media_item['file_type'],
                description=media_item.get('description', '')
            )
            solution.media.append(media)
        
        solution.save()
        
        # Update repair request status to completed if solution is successful
        if validated_data['is_successful']:
            repair_request.status = 'completed'
            repair_request.completed_at = datetime.datetime.now()
            
            # Add system message about solution
            from repair.models import RepairMessage
            message = RepairMessage(
                sender_id='system',
                sender_name='System',
                sender_type='system',
                message='A solution has been provided by the technician.',
                timestamp=datetime.datetime.now()
            )
            repair_request.messages.append(message)
            repair_request.save()
        
        return solution