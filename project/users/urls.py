from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserRegistrationView,
    UserLoginView,
    UserProfileView,
    ExpertProfileViewSet,
    EarningsDashboardView
)

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('expert-profile/', ExpertProfileViewSet.as_view({'get': 'retrieve', 'put': 'update'}), name='expert-profile'),
    path('earnings/', EarningsDashboardView.as_view(), name='earnings'),
]