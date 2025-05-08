from django.urls import path
from .views import ReviewViewSet

urlpatterns = [
    path('', ReviewViewSet.as_view({'get': 'list', 'post': 'create'}), name='review-list'),
    path('<str:pk>/', ReviewViewSet.as_view({'get': 'retrieve'}), name='review-detail'),
    path('my-reviews/', ReviewViewSet.as_view({'get': 'my_reviews'}), name='my-reviews'),
    path('expert-reviews/', ReviewViewSet.as_view({'get': 'expert_reviews'}), name='expert-reviews'),
]