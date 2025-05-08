from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from mongoengine import Document, StringField, EmailField, DateTimeField, BooleanField, ReferenceField, CASCADE

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
            
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    USER_TYPES = (
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('technician', 'Technician'),
        ('admin', 'Admin'),
    )
    
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    user_type = models.CharField(max_length=20, choices=USER_TYPES)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'user_type']
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

class MongoUser(Document):
    """
    MongoDB mirror of User model with additional fields for MongoDB-specific operations
    """
    user_id = StringField(required=True, unique=True)  # Django User model ID
    email = EmailField(required=True, unique=True)
    first_name = StringField(required=True)
    last_name = StringField(required=True)
    user_type = StringField(required=True, choices=['student', 'teacher', 'technician', 'admin'])
    bio = StringField()
    profile_picture_url = StringField()
    date_joined = DateTimeField()
    is_active = BooleanField(default=True)
    is_expert = BooleanField(default=False)  # If user can provide repair/academic help
    expertise_areas = StringField()  # Comma-separated areas of expertise
    
    meta = {
        'collection': 'users',
        'indexes': ['user_id', 'email', 'user_type']
    }

class ExpertProfile(Document):
    """
    Profile for teachers and technicians with expertise information
    """
    user = ReferenceField('MongoUser', reverse_delete_rule=CASCADE)
    expertise_areas = StringField(required=True)  # e.g., "Math, Physics" or "Smartphones, Laptops"
    experience_years = StringField(default="0")
    hourly_rate = StringField(default="0")
    availability_hours = StringField(default="9-17")  # e.g., "9-17" for 9 AM to 5 PM
    completed_services = StringField(default="0")  # Number of completed services
    rating = StringField(default="0.0")  # Average rating
    
    meta = {
        'collection': 'expert_profiles',
        'indexes': ['user']
    }

class EarningRecord(Document):
    """
    Record of earnings for experts
    """
    expert = ReferenceField('MongoUser', reverse_delete_rule=CASCADE)
    amount = StringField(required=True)  # Amount earned
    service_type = StringField(required=True, choices=['repair', 'academic'])  # Type of service
    service_id = StringField(required=True)  # ID of the repair request or academic question
    date = DateTimeField()
    is_paid = BooleanField(default=False)
    
    meta = {
        'collection': 'earnings',
        'indexes': ['expert', 'date']
    }