from mongoengine import Document, StringField, ListField, DateTimeField, EmbeddedDocument, EmbeddedDocumentField, ReferenceField, CASCADE, BooleanField

class RepairMedia(EmbeddedDocument):
    """Embedded document for repair request media (images/videos)"""
    file_url = StringField(required=True)
    file_type = StringField(required=True, choices=['image', 'video'])
    description = StringField()

class RepairMessage(EmbeddedDocument):
    """Embedded document for messages in repair request thread"""
    sender_id = StringField(required=True)  # User ID of sender
    sender_name = StringField(required=True)  # Name of sender for display
    sender_type = StringField(required=True, choices=['student', 'technician', 'system'])
    message = StringField(required=True)
    media_url = StringField()  # Optional media attachment
    timestamp = DateTimeField(required=True)

class RepairRequest(Document):
    """Document for repair requests"""
    student = ReferenceField('users.MongoUser', reverse_delete_rule=CASCADE, required=True)
    technician = ReferenceField('users.MongoUser', reverse_delete_rule=CASCADE)  # Assigned technician (optional initially)
    title = StringField(required=True, max_length=200)
    device_type = StringField(required=True)  # e.g., "Smartphone", "Laptop"
    device_model = StringField(required=True)
    issue_description = StringField(required=True)
    media = ListField(EmbeddedDocumentField(RepairMedia))  # List of uploaded images/videos
    messages = ListField(EmbeddedDocumentField(RepairMessage))  # Thread of messages
    status = StringField(required=True, choices=[
        'pending', 'assigned', 'in_progress', 'completed', 'cancelled'
    ], default='pending')
    price_quote = StringField()  # Price quoted by technician
    payment_status = StringField(choices=['unpaid', 'paid'], default='unpaid')
    created_at = DateTimeField(required=True)
    updated_at = DateTimeField(required=True)
    completed_at = DateTimeField()
    
    meta = {
        'collection': 'repair_requests',
        'indexes': [
            'student', 
            'technician', 
            'status', 
            'created_at'
        ]
    }

class RepairSolution(Document):
    """Document for solutions to repair issues"""
    repair_request = ReferenceField(RepairRequest, reverse_delete_rule=CASCADE, required=True)
    technician = ReferenceField('users.MongoUser', reverse_delete_rule=CASCADE, required=True)
    solution_description = StringField(required=True)
    solution_steps = ListField(StringField())  # Step-by-step repair instructions
    media = ListField(EmbeddedDocumentField(RepairMedia))  # Illustrative media
    is_successful = BooleanField(default=True)
    created_at = DateTimeField(required=True)
    
    meta = {
        'collection': 'repair_solutions',
        'indexes': ['repair_request', 'technician']
    }