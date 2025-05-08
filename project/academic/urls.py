from django.urls import path
from .views import AcademicQuestionViewSet, AcademicAnswerViewSet

urlpatterns = [
    path('questions/', AcademicQuestionViewSet.as_view({'get': 'list', 'post': 'create'}), name='academic-question-list'),
    path('questions/<str:pk>/', AcademicQuestionViewSet.as_view({'get': 'retrieve', 'put': 'update'}), name='academic-question-detail'),
    path('questions/<str:pk>/messages/', AcademicQuestionViewSet.as_view({'post': 'add_message'}), name='academic-question-add-message'),
    path('teachers/', AcademicQuestionViewSet.as_view({'get': 'list_teachers'}), name='academic-teacher-list'),
    path('answers/', AcademicAnswerViewSet.as_view({'post': 'create'}), name='academic-answer-create'),
    path('answers/<str:pk>/', AcademicAnswerViewSet.as_view({'get': 'retrieve'}), name='academic-answer-detail'),
]