from django.urls import path
from .views import ChatRoomViewSet

urlpatterns = [
    path('rooms/', ChatRoomViewSet.as_view({'get': 'list', 'post': 'create'}), name='chat-room-list'),
    path('rooms/<str:pk>/', ChatRoomViewSet.as_view({'get': 'retrieve'}), name='chat-room-detail'),
]