from mongoengine import Document, StringField, ListField, DateTimeField, EmbeddedDocument, EmbeddedDocumentField, ReferenceField, CASCADE, BooleanField

class AcademicMedia(EmbeddedDocument):
    """Embedded document for academic question media (images/videos)"""
    file_url = StringField(required=True)
    file_type = StringField(required=True, choices=['image', 'video'])
    description = StringField()

class AcademicMessage(EmbeddedDocument):
    """Embedded document for messages in academic question thread"""
    sender_id = StringField(required=True)  # User ID of sender
    sender_name = StringField(required=True)  # Name of sender for display
    sender_type = StringField(required=True, choices=['student', 'teacher', 'system'])
    message = StringField(required=True)
    media_url = StringField()  # Optional media attachment
    timestamp = DateTimeField(required=True)

class AcademicQuestion(Document):
    """Document for academic questions"""
    student = ReferenceField('users.MongoUser', reverse_delete_rule=CASCADE, required=True)
    teacher = ReferenceField('users.MongoUser', reverse_delete_rule=CASCADE)  # Assigned teacher (optional initially)
    title = StringField(required=True, max_length=200)
    subject = StringField(required=True)  # e.g., "Math", "Physics"
    question_text = StringField(required=True)
    grade_level = StringField()  # e.g., "High School", "College"
    media = ListField(EmbeddedDocumentField(AcademicMedia))  # List of uploaded images/videos
    messages = ListField(EmbeddedDocumentField(AcademicMessage))  # Thread of messages
    status = StringField(required=True, choices=[
        'pending', 'assigned', 'in_progress', 'answered', 'closed'
    ], default='pending')
    price_quote = StringField()  # Price quoted by teacher
    payment_status = StringField(choices=['unpaid', 'paid'], default='unpaid')
    created_at = DateTimeField(required=True)
    updated_at = DateTimeField(required=True)
    answered_at = DateTimeField()
    
    meta = {
        'collection': 'academic_questions',
        'indexes': [
            'student', 
            'teacher', 
            'status', 
            'created_at'
        ]
    }

class AcademicAnswer(Document):
    """Document for answers to academic questions"""
    question = ReferenceField(AcademicQuestion, reverse_delete_rule=CASCADE, required=True)
    teacher = ReferenceField('users.MongoUser', reverse_delete_rule=CASCADE, required=True)
    answer_text = StringField(required=True)
    explanation = StringField(required=True)  # Detailed explanation
    references = ListField(StringField())  # References or sources
    media = ListField(EmbeddedDocumentField(AcademicMedia))  # Illustrative media
    created_at = DateTimeField(required=True)
    
    meta = {
        'collection': 'academic_answers',
        'indexes': ['question', 'teacher']
    }