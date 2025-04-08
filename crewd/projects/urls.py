from django.urls import path

from .views import (
    IndexView, ViewProjectView, ApplyProjectView, ProfileView, 
    ViewUserProfileView, AnalyzeTechStackView
)
from .dashboard_views import (
    ApplicantDashboardView, TeamLeaderDashboardView, SwitchRoleView,
    ContributorsListView, ProjectsListView, InvitationsListView,
    UpdateInvitationView, MyContributionsView, GroupsListView,
    ViewGroupView, MyProjectsView, CreateProjectView, ManageProjectView,
    FindContributorsView, InviteContributorView, SentInvitationsView,
    CancelInvitationView, ApplicationsListView, ViewApplicationView,
    UpdateApplicationView
)

app_name = 'projects'

urlpatterns = [
    # Dashboard views
    path('dashboard/applicant/', ApplicantDashboardView.as_view(), name='applicant_dashboard'),
    path('dashboard/leader/', TeamLeaderDashboardView.as_view(), name='team_leader_dashboard'),
    path('switch-role/', SwitchRoleView.as_view(), name='switch_role'),
    
    # Applicant views
    path('contributors/', ContributorsListView.as_view(), name='contributors_list'),
    path('browse-projects/', ProjectsListView.as_view(), name='projects_list'),
    path('invitations/', InvitationsListView.as_view(), name='invitations_list'),
    path('invitations/<int:invitation_id>/update/', UpdateInvitationView.as_view(), name='update_invitation'),
    path('my-contributions/', MyContributionsView.as_view(), name='my_contributions'),
    path('groups/', GroupsListView.as_view(), name='groups_list'),
    path('groups/<int:group_id>/', ViewGroupView.as_view(), name='view_group'),
    
    # Team Leader views
    path('my-projects/', MyProjectsView.as_view(), name='my_projects'),
    path('create-project/', CreateProjectView.as_view(), name='create_project'),
    path('manage-project/<int:project_id>/', ManageProjectView.as_view(), name='manage_project'),
    path('find-contributors/<int:project_id>/', FindContributorsView.as_view(), name='find_contributors'),
    path('invite-contributor/<int:project_id>/<int:user_id>/', InviteContributorView.as_view(), name='invite_contributor'),
    path('sent-invitations/', SentInvitationsView.as_view(), name='sent_invitations'),
    path('cancel-invitation/<int:invitation_id>/', CancelInvitationView.as_view(), name='cancel_invitation'),
    path('applications/', ApplicationsListView.as_view(), name='applications_list'),
    path('application/<int:application_id>/', ViewApplicationView.as_view(), name='view_application'),
    path('application/<int:application_id>/update/', UpdateApplicationView.as_view(), name='update_application'),
    
    # Common views
    path('project/<int:project_id>/', ViewProjectView.as_view(), name='view_project'),
    path('project/<int:project_id>/apply/', ApplyProjectView.as_view(), name='apply_project'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/<int:user_id>/', ViewUserProfileView.as_view(), name='view_profile'),
    
    # API views
    path('api/analyze-tech-stack/', AnalyzeTechStackView.as_view(), name='analyze_tech_stack'),
]
