from django.urls import path
from .views import ResourceViewSet, ResourceBookmarkViewSet

urlpatterns = [
    path('', ResourceViewSet.as_view({'get': 'list', 'post': 'create'}), name='resource-list'),
    path('<str:pk>/', ResourceViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='resource-detail'),
    path('search/', ResourceViewSet.as_view({'get': 'search'}), name='resource-search'),
    path('bookmarks/', ResourceBookmarkViewSet.as_view({'get': 'list', 'post': 'create'}), name='resource-bookmark-list'),
    path('bookmarks/<str:pk>/', ResourceBookmarkViewSet.as_view({'delete': 'destroy'}), name='resource-bookmark-detail'),
]