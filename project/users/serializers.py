from rest_framework import serializers
from .models import User
from django.contrib.auth import authenticate

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'first_name', 'last_name', 'user_type', 'bio']
        
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            user_type=validated_data.get('user_type', 'student'),
            bio=validated_data.get('bio', '')
        )
        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, data):
        user = authenticate(email=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Invalid email or password")
        if not user.is_active:
            raise serializers.ValidationError("User is disabled")
        return {'user': user}

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'user_type', 'bio', 'profile_picture', 'date_joined']
        read_only_fields = ['id', 'email', 'date_joined']

class ExpertProfileSerializer(serializers.Serializer):
    expertise_areas = serializers.CharField()
    experience_years = serializers.CharField()
    hourly_rate = serializers.CharField()
    availability_hours = serializers.CharField()
    completed_services = serializers.CharField(read_only=True)
    rating = serializers.CharField(read_only=True)

class EarningRecordSerializer(serializers.Serializer):
    amount = serializers.CharField()
    service_type = serializers.CharField()
    service_id = serializers.CharField()
    date = serializers.DateTimeField()
    is_paid = serializers.BooleanField()