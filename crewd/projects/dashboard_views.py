from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.urls import reverse, reverse_lazy
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import get_user_model
import json
import requests
import os

from .models import Project, Application, ProjectInvitation, Contribution, Group, GroupMessage
from accounts.models import TECH_CHOICES

User = get_user_model()

# Base dashboard views
class DashboardView(LoginRequiredMixin, View):
    """Main dashboard redirector view"""
    
    def get(self, request):
        if not request.user.role:
            return redirect('accounts:role_selection')
            
        if request.user.role == 'applicant':
            return redirect('projects:dashboard_applicant')
        elif request.user.role == 'leader':
            return redirect('projects:dashboard_leader')
        else:
            # For now, default to applicant for other roles
            return redirect('projects:dashboard_applicant')


class SwitchRoleView(LoginRequiredMixin, View):
    """View for switching between roles"""
    
    def get(self, request):
        user = request.user
        
        # Toggle role between applicant and leader
        if user.role == 'applicant':
            user.role = 'leader'
            messages.success(request, "Switched to Team Leader mode.")
        else:
            user.role = 'applicant'
            messages.success(request, "Switched to Applicant mode.")
            
        user.save()
        return redirect('projects:dashboard')


class ViewProfileView(LoginRequiredMixin, DetailView):
    """View for viewing another user's profile"""
    model = User
    template_name = 'projects/view_profile.html'
    context_object_name = 'profile_user'
    pk_url_kwarg = 'user_id'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_user = self.get_object()
        
        # Get relevant projects
        if profile_user.role == 'leader':
            context['projects'] = Project.objects.filter(creator=profile_user).order_by('-created_at')
        else:
            context['projects'] = Project.objects.filter(members=profile_user).order_by('-created_at')
        
        # Get contributions
        context['contributions'] = Contribution.objects.filter(user=profile_user).order_by('-created_at')
        
        # Check if there are mutual projects
        context['mutual_projects'] = Project.objects.filter(
            Q(creator=self.request.user, members=profile_user) | 
            Q(creator=profile_user, members=self.request.user)
        ).distinct()
        
        return context


# Applicant dashboard views
class ApplicantDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard view for applicants"""
    template_name = 'projects/dashboard_applicant.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get pending invitations
        context['pending_invitations'] = ProjectInvitation.objects.filter(
            user=user, 
            status='pending'
        ).order_by('-created_at')[:5]
        
        # Get recent applications
        context['recent_applications'] = Application.objects.filter(
            applicant=user
        ).order_by('-created_at')[:5]
        
        # Get active projects (where user is a member)
        context['active_projects'] = Project.objects.filter(
            members=user,
            status='active'
        ).order_by('-created_at')[:5]
        
        # Get recent project activity
        context['recent_contributions'] = Contribution.objects.filter(
            project__members=user
        ).order_by('-created_at')[:10]
        
        return context


class ContributorsListView(LoginRequiredMixin, ListView):
    """View for listing all contributors (users)"""
    model = User
    template_name = 'projects/contributors_list.html'
    context_object_name = 'contributors'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = User.objects.exclude(id=self.request.user.id).order_by('-date_joined')
        
        # Filter by tech stack if provided
        tech_filter = self.request.GET.get('tech')
        if tech_filter:
            queryset = queryset.filter(tech_stack__icontains=tech_filter)
            
        # Filter by role if provided
        role_filter = self.request.GET.get('role')
        if role_filter and role_filter in ['applicant', 'leader']:
            queryset = queryset.filter(role=role_filter)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tech_choices'] = TECH_CHOICES
        context['current_tech'] = self.request.GET.get('tech', '')
        context['current_role'] = self.request.GET.get('role', '')
        return context


class ProjectsListView(LoginRequiredMixin, ListView):
    """View for listing all available projects"""
    model = Project
    template_name = 'projects/projects_list.html'
    context_object_name = 'projects'
    paginate_by = 9
    
    def get_queryset(self):
        # Get active projects excluding those created by the user
        queryset = Project.objects.filter(status='active').exclude(creator=self.request.user).order_by('-created_at')
        
        # Filter by tech stack if provided
        tech_filter = self.request.GET.get('tech')
        if tech_filter:
            queryset = queryset.filter(required_skills__icontains=tech_filter)
            
        # Check for tech stack match with user
        if self.request.GET.get('match') == 'true' and self.request.user.tech_stack:
            user_tech = self.request.user.get_tech_stack_list()
            matching_projects = []
            
            for project in queryset:
                project_tech = project.get_required_skills_list()
                if any(tech in project_tech for tech in user_tech):
                    matching_projects.append(project.id)
                    
            queryset = queryset.filter(id__in=matching_projects)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tech_choices'] = TECH_CHOICES
        context['current_tech'] = self.request.GET.get('tech', '')
        context['match_selected'] = self.request.GET.get('match') == 'true'
        
        # Add application status for projects
        user_applications = Application.objects.filter(applicant=self.request.user)
        applied_projects = {app.project_id: app.status for app in user_applications}
        context['applied_projects'] = applied_projects
        
        return context


class InvitationsListView(LoginRequiredMixin, ListView):
    """View for listing all invitations received by the user"""
    model = ProjectInvitation
    template_name = 'projects/invitations_list.html'
    context_object_name = 'invitations'
    paginate_by = 10
    
    def get_queryset(self):
        return ProjectInvitation.objects.filter(user=self.request.user).order_by('-created_at')


class UpdateInvitationView(LoginRequiredMixin, View):
    """View for accepting or rejecting an invitation"""
    
    def post(self, request, invitation_id):
        invitation = get_object_or_404(ProjectInvitation, id=invitation_id, user=request.user)
        action = request.POST.get('action')
        
        if action == 'accept':
            invitation.status = 'accepted'
            invitation.save()
            
            # Add user to project members
            invitation.project.members.add(request.user)
            
            # Add user to project group
            try:
                group = invitation.project.group
                group.members.add(request.user)
            except Group.DoesNotExist:
                # Create group if it doesn't exist
                group = Group.objects.create(
                    name=invitation.project.title,
                    project=invitation.project
                )
                group.members.add(invitation.project.creator)
                group.members.add(request.user)
            
            messages.success(request, f"You have accepted the invitation to join {invitation.project.title}.")
            
        elif action == 'reject':
            invitation.status = 'rejected'
            invitation.save()
            messages.success(request, f"You have rejected the invitation to join {invitation.project.title}.")
            
        return redirect('projects:invitations_list')


class MyContributionsView(LoginRequiredMixin, TemplateView):
    """View for displaying user's contributions and projects"""
    template_name = 'projects/my_contributions.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Active projects (as member)
        context['active_projects'] = Project.objects.filter(
            members=user,
            status='active'
        ).order_by('-created_at')
        
        # Completed projects (as member)
        context['completed_projects'] = Project.objects.filter(
            members=user,
            status='completed'
        ).order_by('-created_at')
        
        # My contributions
        context['contributions'] = Contribution.objects.filter(
            user=user
        ).order_by('-created_at')
        
        return context


class GroupsListView(LoginRequiredMixin, ListView):
    """View for listing all groups the user is a member of"""
    model = Group
    template_name = 'projects/groups_list.html'
    context_object_name = 'groups'
    
    def get_queryset(self):
        return Group.objects.filter(members=self.request.user).order_by('-created_at')


class ViewGroupView(LoginRequiredMixin, DetailView):
    """View for viewing a group's chat and details"""
    model = Group
    template_name = 'projects/view_group.html'
    context_object_name = 'group'
    pk_url_kwarg = 'group_id'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = self.get_object()
        
        # Verify user is a member
        if self.request.user not in group.members.all():
            messages.error(self.request, "You are not a member of this group.")
            return context
        
        # Get messages
        context['messages'] = GroupMessage.objects.filter(group=group).order_by('created_at')
        
        # Get project
        context['project'] = group.project
        
        # Get group members
        context['members'] = group.members.all()
        
        return context
    
    def post(self, request, group_id):
        group = self.get_object()
        
        # Verify user is a member
        if request.user not in group.members.all():
            messages.error(request, "You are not a member of this group.")
            return redirect('projects:groups_list')
        
        # Create message
        message_content = request.POST.get('message', '').strip()
        if message_content:
            GroupMessage.objects.create(
                group=group,
                sender=request.user,
                content=message_content
            )
            
        return redirect('projects:view_group', group_id=group_id)


# Team Leader dashboard views
class TeamLeaderDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard view for team leaders"""
    template_name = 'projects/dashboard_leader.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get user's projects
        context['projects'] = Project.objects.filter(creator=user).order_by('-created_at')[:5]
        
        # Get recent applications to user's projects
        context['recent_applications'] = Application.objects.filter(
            project__creator=user,
            status='pending'
        ).order_by('-created_at')[:5]
        
        # Get project statistics
        context['active_projects_count'] = Project.objects.filter(creator=user, status='active').count()
        context['completed_projects_count'] = Project.objects.filter(creator=user, status='completed').count()
        context['total_contributors'] = User.objects.filter(member_projects__creator=user).distinct().count()
        
        return context


class MyProjectsView(LoginRequiredMixin, ListView):
    """View for listing team leader's projects"""
    model = Project
    template_name = 'projects/my_projects.html'
    context_object_name = 'projects'
    
    def get_queryset(self):
        return Project.objects.filter(creator=self.request.user).order_by('-created_at')


class CreateProjectView(LoginRequiredMixin, CreateView):
    """View for creating a new project (Team Leader)"""
    model = Project
    template_name = 'projects/create_project_dashboard.html'
    fields = ['title', 'description', 'required_skills', 'team_size', 'duration']
    success_url = reverse_lazy('projects:my_projects')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tech_choices'] = TECH_CHOICES
        return context
    
    def form_valid(self, form):
        form.instance.creator = self.request.user
        response = super().form_valid(form)
        
        # Create project group
        Group.objects.create(
            name=form.instance.title,
            project=form.instance
        ).members.add(self.request.user)
        
        messages.success(self.request, f"Project '{form.instance.title}' created successfully!")
        return response


class ManageProjectView(LoginRequiredMixin, DetailView):
    """View for managing a project (Team Leader)"""
    model = Project
    template_name = 'projects/manage_project.html'
    context_object_name = 'project'
    pk_url_kwarg = 'project_id'
    
    def get_object(self):
        project = get_object_or_404(Project, id=self.kwargs['project_id'])
        if project.creator != self.request.user:
            raise PermissionError("You are not the creator of this project")
        return project
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_object()
        
        # Get applications
        context['applications'] = Application.objects.filter(project=project).order_by('-created_at')
        
        # Get team members
        context['team_members'] = project.members.exclude(id=self.request.user.id)
        
        # Get invitations
        context['invitations'] = ProjectInvitation.objects.filter(project=project).order_by('-created_at')
        
        return context
    
    def post(self, request, project_id):
        project = self.get_object()
        action = request.POST.get('action')
        
        if action == 'update_status':
            new_status = request.POST.get('status')
            if new_status in ['active', 'completed', 'cancelled']:
                project.status = new_status
                project.save()
                messages.success(request, f"Project status updated to {new_status}.")
        
        return redirect('projects:manage_project', project_id=project_id)


class FindContributorsView(LoginRequiredMixin, ListView):
    """View for finding contributors for a project"""
    model = User
    template_name = 'projects/find_contributors.html'
    context_object_name = 'contributors'
    paginate_by = 12
    
    def get_object(self):
        project = get_object_or_404(Project, id=self.kwargs['project_id'])
        if project.creator != self.request.user:
            raise PermissionError("You are not the creator of this project")
        return project
    
    def get_queryset(self):
        project = self.get_object()
        
        # Get users who aren't already members
        queryset = User.objects.exclude(
            Q(id=self.request.user.id) | 
            Q(id__in=project.members.all())
        ).order_by('-date_joined')
        
        # Filter by tech stack if provided
        tech_filter = self.request.GET.get('tech')
        if tech_filter:
            queryset = queryset.filter(tech_stack__icontains=tech_filter)
            
        # Filter by role if provided
        role_filter = self.request.GET.get('role')
        if role_filter and role_filter in ['applicant', 'leader']:
            queryset = queryset.filter(role=role_filter)
            
        # Sort by tech stack match
        if project.required_skills:
            required_skills = project.get_required_skills_list()
            if required_skills:
                # Add a match score for each user
                for user in queryset:
                    user_skills = user.get_tech_stack_list()
                    match_count = sum(1 for skill in required_skills if skill in user_skills)
                    user.match_score = match_count
                
                # Sort queryset by match score
                queryset = sorted(queryset, key=lambda u: u.match_score, reverse=True)
                
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_object()
        
        context['project'] = project
        context['tech_choices'] = TECH_CHOICES
        context['current_tech'] = self.request.GET.get('tech', '')
        context['current_role'] = self.request.GET.get('role', '')
        
        # Check invitations
        invited_users = ProjectInvitation.objects.filter(project=project).values_list('user_id', flat=True)
        context['invited_users'] = invited_users
        
        return context


class InviteContributorView(LoginRequiredMixin, View):
    """View for inviting a user to a project"""
    
    def post(self, request, project_id, user_id):
        project = get_object_or_404(Project, id=project_id, creator=request.user)
        user = get_object_or_404(User, id=user_id)
        message = request.POST.get('message', '')
        
        # Check if already invited
        if ProjectInvitation.objects.filter(project=project, user=user).exists():
            messages.warning(request, f"{user.username} has already been invited to this project.")
            return redirect('projects:find_contributors', project_id=project_id)
        
        # Check if already a member
        if project.members.filter(id=user.id).exists():
            messages.warning(request, f"{user.username} is already a member of this project.")
            return redirect('projects:find_contributors', project_id=project_id)
        
        # Create invitation
        ProjectInvitation.objects.create(
            project=project,
            user=user,
            message=message
        )
        
        messages.success(request, f"Invitation sent to {user.username}.")
        return redirect('projects:find_contributors', project_id=project_id)


class SentInvitationsView(LoginRequiredMixin, ListView):
    """View for listing all invitations sent by the team leader"""
    model = ProjectInvitation
    template_name = 'projects/sent_invitations.html'
    context_object_name = 'invitations'
    paginate_by = 10
    
    def get_queryset(self):
        return ProjectInvitation.objects.filter(project__creator=self.request.user).order_by('-created_at')


class CancelInvitationView(LoginRequiredMixin, View):
    """View for cancelling a sent invitation"""
    
    def post(self, request, invitation_id):
        invitation = get_object_or_404(ProjectInvitation, id=invitation_id, project__creator=request.user, status='pending')
        invitation.delete()
        messages.success(request, "Invitation cancelled successfully.")
        return redirect('projects:sent_invitations')


class ApplicationsListView(LoginRequiredMixin, ListView):
    """View for listing all applications to team leader's projects"""
    model = Application
    template_name = 'projects/applications_list.html'
    context_object_name = 'applications'
    paginate_by = 10
    
    def get_queryset(self):
        return Application.objects.filter(project__creator=self.request.user).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Group applications by project
        applications_by_project = {}
        for app in context['applications']:
            if app.project.id not in applications_by_project:
                applications_by_project[app.project.id] = {
                    'project': app.project,
                    'applications': []
                }
            applications_by_project[app.project.id]['applications'].append(app)
        
        context['applications_by_project'] = applications_by_project
        
        return context


class ViewApplicationView(LoginRequiredMixin, DetailView):
    """View for viewing a specific application"""
    model = Application
    template_name = 'projects/view_application.html'
    context_object_name = 'application'
    pk_url_kwarg = 'application_id'
    
    def get_object(self):
        application = get_object_or_404(Application, id=self.kwargs['application_id'])
        if application.project.creator != self.request.user:
            raise PermissionError("You are not the creator of this project")
        return application


class UpdateApplicationView(LoginRequiredMixin, View):
    """View for accepting or rejecting an application"""
    
    def post(self, request, application_id):
        application = get_object_or_404(Application, id=application_id, project__creator=request.user)
        action = request.POST.get('action')
        
        if action == 'accept':
            application.status = 'accepted'
            application.save()
            
            # Add user to project members
            application.project.members.add(application.applicant)
            
            # Add user to project group
            try:
                group = application.project.group
                group.members.add(application.applicant)
            except Group.DoesNotExist:
                # Create group if it doesn't exist
                group = Group.objects.create(
                    name=application.project.title,
                    project=application.project
                )
                group.members.add(application.project.creator)
                group.members.add(application.applicant)
            
            messages.success(request, f"{application.applicant.username}'s application has been accepted.")
            
        elif action == 'reject':
            application.status = 'rejected'
            application.save()
            messages.success(request, f"{application.applicant.username}'s application has been rejected.")
            
        return redirect('projects:applications_list')


class AnalyzeTechStackView(LoginRequiredMixin, View):
    """API view for analyzing project description and suggesting tech stack"""
    
    def post(self, request):
        description = request.POST.get('description', '')
        
        if not description:
            return JsonResponse({
                'success': False,
                'message': 'Project description is required.'
            })
        
        try:
            # Call Grok API to analyze the description
            api_key = "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" # Should be stored in environment variable
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            prompt = f"""
            Analyze the following project description and suggest the most appropriate tech stack from the list below:

            PROJECT DESCRIPTION:
            {description}

            AVAILABLE TECH STACK OPTIONS:
            {', '.join(TECH_CHOICES)}

            Please return only the names of the 5-7 most appropriate technologies separated by commas, with no additional text.
            """
            
            response = requests.post(
                'https://api.grok.ai/v1/completions',
                headers=headers,
                json={
                    'prompt': prompt,
                    'max_tokens': 200,
                    'temperature': 0.2
                }
            )
            
            response_data = response.json()
            suggested_stack = response_data.get('choices', [{}])[0].get('text', '').strip()
            
            # Filter and validate the tech stack
            suggested_stack_list = [tech.strip() for tech in suggested_stack.split(',')]
            valid_stack = [tech for tech in suggested_stack_list if tech in TECH_CHOICES]
            
            return JsonResponse({
                'success': True,
                'tech_stack': valid_stack
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error analyzing tech stack: {str(e)}'
            })