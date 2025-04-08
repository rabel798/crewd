from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(next_page='index'), name='logout'),
    path('role-selection/', views.RoleSelectionView.as_view(), name='role_selection'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
]