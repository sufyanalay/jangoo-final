from rest_framework import serializers
import datetime

class ReviewSerializer(serializers.Serializer):
    id = serializers.CharField(source='_id', read_only=True)
    user_id = serializers.CharField(read_only=True)
    user_name = serializers.SerializerMethodField(read_only=True)
    expert_id = serializers.CharField()
    expert_name = serializers.SerializerMethodField(read_only=True)
    service_type = serializers.ChoiceField(choices=['repair', 'academic'])
    service_id = serializers.CharField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField()
    created_at = serializers.DateTimeField(read_only=True)
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    
    def get_expert_name(self, obj):
        return f"{obj.expert.first_name} {obj.expert.last_name}"
    
    def validate(self, data):
        from users.models import MongoUser
        
        # Validate expert exists and is actually an expert
        expert = MongoUser.objects(id=data['expert_id']).first()
        if not expert:
            raise serializers.ValidationError(f"Expert with ID {data['expert_id']} not found")
        
        if expert.user_type not in ['teacher', 'technician']:
            raise serializers.ValidationError("The specified user is not an expert")
        
        # Validate service type matches expert type
        if data['service_type'] == 'repair' and expert.user_type != 'technician':
            raise serializers.ValidationError("Cannot review a non-technician for repair services")
        if data['service_type'] == 'academic' and expert.user_type != 'teacher':
            raise serializers.ValidationError("Cannot review a non-teacher for academic services")
        
        # Validate service exists
        if data['service_type'] == 'repair':
            from repair.models import RepairRequest
            service = RepairRequest.objects(id=data['service_id']).first()
            if not service:
                raise serializers.ValidationError(f"Repair request with ID {data['service_id']} not found")
            if service.status != 'completed':
                raise serializers.ValidationError("Cannot review an incomplete repair request")
        else:  # academic
            from academic.models import AcademicQuestion
            service = AcademicQuestion.objects(id=data['service_id']).first()
            if not service:
                raise serializers.ValidationError(f"Academic question with ID {data['service_id']} not found")
            if service.status != 'answered':
                raise serializers.ValidationError("Cannot review an unanswered academic question")
        
        return data
    
    def create(self, validated_data):
        from reviews.models import Review
        from users.models import MongoUser
        
        user_id = self.context['request'].user.id
        mongo_user = MongoUser.objects(user_id=str(user_id)).first()
        
        expert = MongoUser.objects(id=validated_data['expert_id']).first()
        
        # Check if user has already reviewed this service
        existing_review = Review.objects(
            user=mongo_user,
            service_type=validated_data['service_type'],
            service_id=validated_data['service_id']
        ).first()
        
        if existing_review:
            raise serializers.ValidationError("You have already reviewed this service")
        
        review = Review(
            user=mongo_user,
            expert=expert,
            service_type=validated_data['service_type'],
            service_id=validated_data['service_id'],
            rating=validated_data['rating'],
            comment=validated_data['comment'],
            created_at=datetime.datetime.now()
        )
        
        review.save()
        
        # Update expert's average rating
        from users.models import ExpertProfile
        expert_profile = ExpertProfile.objects(user=expert).first()
        if expert_profile:
            # Get all reviews for this expert
            all_reviews = Review.objects(expert=expert)
            avg_rating = sum(r.rating for r in all_reviews) / len(all_reviews)
            expert_profile.rating = str(round(avg_rating, 1))
            expert_profile.save()
        
        return review