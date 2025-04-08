from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('auth/', views.register_login_view, name='auth'),
    path('role-selection/', views.role_selection, name='role_selection'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('project/create/', views.create_project, name='create_project'),
    path('project/<int:project_id>/', views.view_project, name='view_project'),
    path('projects/', views.project_list, name='project_list'),
    path('project/<int:project_id>/apply/', views.apply_project, name='apply_project'),
    path('applications/', views.application_list, name='application_list'),
    path('application/<int:application_id>/update/', views.update_application, name='update_application'),
    path('profile/', views.profile, name='profile'),
    path('logout/', views.logout_view, name='logout'),
]
