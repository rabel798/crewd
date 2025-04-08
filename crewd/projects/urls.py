from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.ProjectListView.as_view(), name='project_list'),
    path('<int:pk>/', views.ProjectDetailView.as_view(), name='project_detail'),
    path('create/', views.ProjectCreateView.as_view(), name='project_create'),
    path('<int:pk>/apply/', views.ApplicationCreateView.as_view(), name='apply_project'),
    path('applications/', views.ApplicationListView.as_view(), name='application_list'),
    path('applications/<int:pk>/update/', views.ApplicationUpdateView.as_view(), name='update_application'),
]