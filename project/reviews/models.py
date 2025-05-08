from mongoengine import Document, StringField, ListField, DateTimeField, ReferenceField, CASCADE, IntField

class Review(Document):
    """Review for a service provider (teacher or technician)"""
    user = ReferenceField('users.MongoUser', reverse_delete_rule=CASCADE, required=True)  # User giving the review
    expert = ReferenceField('users.MongoUser', reverse_delete_rule=CASCADE, required=True)  # Expert being reviewed
    service_type = StringField(required=True, choices=['repair', 'academic'])  # Type of service
    service_id = StringField(required=True)  # ID of the service (repair request or academic question)
    rating = IntField(required=True, min_value=1, max_value=5)  # Rating from 1-5
    comment = StringField(required=True)  # Review text
    created_at = DateTimeField(required=True)
    
    meta = {
        'collection': 'reviews',
        'indexes': [
            'user',
            'expert',
            'service_type',
            'service_id',
            ('expert', 'service_type')  # Compound index for querying reviews by expert and service type
        ]
    }