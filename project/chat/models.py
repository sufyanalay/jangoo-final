from mongoengine import Document, StringField, ListField, DateTimeField, ReferenceField, CASCADE, BooleanField, EmbeddedDocument, EmbeddedDocumentField

class ChatMessage(EmbeddedDocument):
    """Individual chat message"""
    sender_id = StringField(required=True)
    sender_name = StringField(required=True)
    content = StringField(required=True)
    file_url = StringField()  # Optional file attachment
    file_type = StringField(choices=['image', 'document'])  # Type of file
    timestamp = DateTimeField(required=True)

class ChatRoom(Document):
    """Chat room between two users"""
    user1 = ReferenceField('users.MongoUser', reverse_delete_rule=CASCADE, required=True)
    user2 = ReferenceField('users.MongoUser', reverse_delete_rule=CASCADE, required=True)
    messages = ListField(EmbeddedDocumentField(ChatMessage))
    is_active = BooleanField(default=True)
    created_at = DateTimeField(required=True)
    updated_at = DateTimeField(required=True)
    
    # Additional fields to track service context
    service_type = StringField(choices=['repair', 'academic', 'general'])  # Type of service
    service_id = StringField()  # ID of related service (repair request or academic question)
    
    meta = {
        'collection': 'chat_rooms',
        'indexes': [
            'user1', 
            'user2', 
            'created_at',
            ('user1', 'user2')  # Compound index
        ]
    }