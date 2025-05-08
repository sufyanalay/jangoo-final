from django.urls import path
from .views import RepairRequestViewSet, RepairSolutionViewSet

urlpatterns = [
    path('requests/', RepairRequestViewSet.as_view({'get': 'list', 'post': 'create'}), name='repair-request-list'),
    path('requests/<str:pk>/', RepairRequestViewSet.as_view({'get': 'retrieve', 'put': 'update'}), name='repair-request-detail'),
    path('requests/<str:pk>/messages/', RepairRequestViewSet.as_view({'post': 'add_message'}), name='repair-request-add-message'),
    path('technicians/', RepairRequestViewSet.as_view({'get': 'list_technicians'}), name='repair-technician-list'),
    path('solutions/', RepairSolutionViewSet.as_view({'post': 'create'}), name='repair-solution-create'),
    path('solutions/<str:pk>/', RepairSolutionViewSet.as_view({'get': 'retrieve'}), name='repair-solution-detail'),
]