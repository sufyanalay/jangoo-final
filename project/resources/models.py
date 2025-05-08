from mongoengine import Document, StringField, ListField, DateTimeField, ReferenceField, CASCADE, BooleanField, IntField

class Resource(Document):
    """Educational or repair resource document"""
    title = StringField(required=True, max_length=200)
    description = StringField(required=True)
    resource_type = StringField(required=True, choices=['video', 'document', 'tutorial', 'guide'])
    category = StringField(required=True, choices=['repair', 'academic'])
    subject = StringField(required=True)  # Academic subject or repair device type
    file_url = StringField(required=True)  # URL to the resource file
    thumbnail_url = StringField()  # Preview image URL
    author = ReferenceField('users.MongoUser', reverse_delete_rule=CASCADE, required=True)
    is_premium = BooleanField(default=False)  # Indicates if resource is premium/paid
    views = IntField(default=0)  # Number of views
    tags = ListField(StringField())  # List of tags for search
    created_at = DateTimeField(required=True)
    updated_at = DateTimeField(required=True)
    
    meta = {
        'collection': 'resources',
        'indexes': [
            'author',
            'category',
            'subject',
            'resource_type',
            'tags',
            'created_at'
        ]
    }

class ResourceBookmark(Document):
    """User bookmarks for resources"""
    user = ReferenceField('users.MongoUser', reverse_delete_rule=CASCADE, required=True)
    resource = ReferenceField(Resource, reverse_delete_rule=CASCADE, required=True)
    created_at = DateTimeField(required=True)
    
    meta = {
        'collection': 'resource_bookmarks',
        'indexes': [
            'user',
            'resource',
            ('user', 'resource')  # Compound index
        ]
    }