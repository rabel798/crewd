from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth.models import User

from accounts.models import UserProfile
from .models import (
    Project, Application, ProjectMembership, 
    Invitation, Group, Message
)
from .forms import ProjectForm, ApplicationForm


class SwitchRoleView(LoginRequiredMixin, View):
    """View for switching between applicant and team leader roles"""
    template_name = 'dashboard/switch_role.html'
    
    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        role = request.POST.get('role')
        
        if role in ['applicant', 'leader', 'company']:
            user_profile = request.user.profile
            user_profile.role = role
            user_profile.save()
            
            if role == 'applicant':
                messages.success(request, "Role switched to Applicant")
                return redirect('projects:applicant_dashboard')
            elif role == 'leader':
                messages.success(request, "Role switched to Team Leader")
                return redirect('projects:team_leader_dashboard')
            elif role == 'company':
                messages.success(request, "Role switched to Company")
                # Redirect to future company dashboard
                return redirect('projects:team_leader_dashboard')  # Placeholder
        else:
            messages.error(request, "Invalid role selected.")
            return redirect('projects:switch_role')


class ApplicantDashboardView(LoginRequiredMixin, View):
    """Dashboard view for applicants"""
    template_name = 'dashboard/applicant_dashboard.html'
    
    def get(self, request):
        # If user is not in applicant role, redirect to switch role page
        if request.user.profile.role != 'applicant':
            messages.info(request, "Please switch to applicant role to access this dashboard.")
            return redirect('projects:switch_role')
        
        # Get basic stats for dashboard
        context = {
            'applications_count': Application.objects.filter(
                applicant=request.user
            ).count(),
            'invitations_count': Invitation.objects.filter(
                recipient=request.user,
                status='pending'
            ).count(),
            'memberships_count': ProjectMembership.objects.filter(
                user=request.user
            ).count(),
        }
        
        return render(request, self.template_name, context)


class TeamLeaderDashboardView(LoginRequiredMixin, View):
    """Dashboard view for team leaders"""
    template_name = 'dashboard/team_leader_dashboard.html'
    
    def get(self, request):
        # If user is not in leader role, redirect to switch role page
        if request.user.profile.role != 'leader':
            messages.info(request, "Please switch to team leader role to access this dashboard.")
            return redirect('projects:switch_role')
        
        # Get basic stats for dashboard
        context = {
            'projects_count': Project.objects.filter(
                creator=request.user
            ).count(),
            'applications_count': Application.objects.filter(
                project__creator=request.user,
                status='pending'
            ).count(),
            'invitations_count': Invitation.objects.filter(
                sender=request.user,
                status='pending'
            ).count(),
        }
        
        return render(request, self.template_name, context)


# Applicant views
class ContributorsListView(LoginRequiredMixin, ListView):
    """List view of all contributors"""
    template_name = 'projects/contributors_list.html'
    context_object_name = 'contributors'
    paginate_by = 12
    
    def get_queryset(self):
        # Get search query
        query = self.request.GET.get('q', '')
        # Filter by tech stack
        tech_filter = self.request.GET.getlist('tech')
        
        # Base queryset
        queryset = UserProfile.objects.exclude(user=self.request.user)
        
        # Apply search query
        if query:
            queryset = queryset.filter(
                Q(user__username__icontains=query) |
                Q(tech_stack__icontains=query)
            )
        
        # Apply tech stack filters
        if tech_filter:
            for tech in tech_filter:
                queryset = queryset.filter(tech_stack__icontains=tech)
                
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add tech stack choices for filtering
        context['tech_choices'] = sorted(set([
            tech for profile in UserProfile.objects.all()
            for tech in profile.get_tech_stack_list()
        ]))
        # Add selected filters
        context['selected_tech'] = self.request.GET.getlist('tech')
        context['search_query'] = self.request.GET.get('q', '')
        return context


class ProjectsListView(LoginRequiredMixin, ListView):
    """List view of all projects for applicants"""
    template_name = 'projects/projects_list.html'
    context_object_name = 'projects'
    paginate_by = 9
    
    def get_queryset(self):
        # Get search query and filters
        query = self.request.GET.get('q', '')
        status_filter = self.request.GET.get('status', 'active')
        tech_filter = self.request.GET.getlist('tech')
        
        # Base queryset - exclude user's own projects
        queryset = Project.objects.all()
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        
        # Apply search
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(required_skills__icontains=query)
            )
        
        # Apply tech filters
        if tech_filter:
            for tech in tech_filter:
                queryset = queryset.filter(required_skills__icontains=tech)
        
        # Add match score based on user tech stack
        user_tech_stack = self.request.user.profile.get_tech_stack_list()
        for project in queryset:
            project_skills = project.get_required_skills_list()
            project.match_score = len(set(user_tech_stack) & set(project_skills))
            if user_tech_stack:
                project.match_percentage = int((project.match_score / len(user_tech_stack)) * 100)
            else:
                project.match_percentage = 0
        
        # Sort by match score if user has skills
        if user_tech_stack:
            return sorted(queryset, key=lambda p: p.match_score, reverse=True)
        
        # Otherwise sort by created date
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add tech choices
        all_projects = Project.objects.all()
        tech_choices = set()
        for project in all_projects:
            tech_choices.update(project.get_required_skills_list())
        
        context['tech_choices'] = sorted(tech_choices)
        context['selected_tech'] = self.request.GET.getlist('tech')
        context['search_query'] = self.request.GET.get('q', '')
        context['status_filter'] = self.request.GET.get('status', 'active')
        
        return context


class InvitationsListView(LoginRequiredMixin, ListView):
    """List view of received invitations"""
    template_name = 'projects/invitations_list.html'
    context_object_name = 'invitations'
    paginate_by = 10
    
    def get_queryset(self):
        return Invitation.objects.filter(recipient=self.request.user).order_by('-created_at')
    

class UpdateInvitationView(LoginRequiredMixin, View):
    """Update invitation status"""
    
    def post(self, request, invitation_id):
        invitation = get_object_or_404(Invitation, id=invitation_id, recipient=request.user)
        action = request.POST.get('action')
        
        if action == 'accept':
            invitation.status = 'accepted'
            invitation.save()
            
            # Create project membership
            ProjectMembership.objects.create(
                user=request.user,
                project=invitation.project,
                role='member'
            )
            
            messages.success(request, f"You have joined {invitation.project.title}.")
        
        elif action == 'reject':
            invitation.status = 'rejected'
            invitation.save()
            messages.info(request, f"Invitation declined.")
        
        return redirect('projects:invitations_list')


class MyContributionsView(LoginRequiredMixin, ListView):
    """List view of user's applications and project memberships"""
    template_name = 'projects/my_contributions.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get applications and memberships
        context['applications'] = Application.objects.filter(
            applicant=self.request.user
        ).order_by('-created_at')
        
        context['memberships'] = ProjectMembership.objects.filter(
            user=self.request.user
        ).order_by('-joined_at')
        
        return context
    
    def get_queryset(self):
        # Empty queryset since we're using get_context_data
        return ProjectMembership.objects.none()


class GroupsListView(LoginRequiredMixin, ListView):
    """List view of user's group chats"""
    template_name = 'projects/groups_list.html'
    context_object_name = 'groups'
    
    def get_queryset(self):
        # Get projects where user is a member
        user_projects = Project.objects.filter(
            memberships__user=self.request.user
        )
        
        # Get groups for those projects
        return Group.objects.filter(project__in=user_projects).order_by('name')


class ViewGroupView(LoginRequiredMixin, View):
    """View for a group chat"""
    template_name = 'projects/view_group.html'
    
    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        
        # Check if user is a member
        is_member = ProjectMembership.objects.filter(
            user=request.user,
            project=group.project
        ).exists()
        
        if not is_member and group.project.creator != request.user:
            messages.error(request, "You are not a member of this group.")
            return redirect('projects:groups_list')
        
        # Get messages for the group
        messages_list = Message.objects.filter(group=group).order_by('created_at')
        
        context = {
            'group': group,
            'messages': messages_list,
            'project': group.project,
            'is_leader': group.project.creator == request.user
        }
        return render(request, self.template_name, context)
    
    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        content = request.POST.get('message', '').strip()
        
        # Check if user is a member
        is_member = ProjectMembership.objects.filter(
            user=request.user,
            project=group.project
        ).exists()
        
        if not is_member and group.project.creator != request.user:
            messages.error(request, "You are not a member of this group.")
            return redirect('projects:groups_list')
        
        if content:
            Message.objects.create(
                group=group,
                sender=request.user,
                content=content
            )
        
        return redirect('projects:view_group', group_id=group_id)


# Team Leader views
class MyProjectsView(LoginRequiredMixin, ListView):
    """List view of user's projects"""
    template_name = 'projects/my_projects.html'
    context_object_name = 'projects'
    
    def get_queryset(self):
        return Project.objects.filter(creator=self.request.user).order_by('-created_at')


class CreateProjectView(LoginRequiredMixin, View):
    """Create a new project"""
    template_name = 'projects/create_project.html'
    
    def get(self, request):
        form = ProjectForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = ProjectForm(request.POST)
        
        if form.is_valid():
            project = form.save(commit=False)
            project.creator = request.user
            project.save()
            
            # Create a group chat for the project
            Group.objects.create(
                name=f"{project.title} Group",
                project=project
            )
            
            # Add creator as a member
            ProjectMembership.objects.create(
                user=request.user,
                project=project,
                role='admin'
            )
            
            messages.success(request, f"Project '{project.title}' created successfully.")
            return redirect('projects:manage_project', project_id=project.id)
        
        return render(request, self.template_name, {'form': form})


class ManageProjectView(LoginRequiredMixin, View):
    """Manage a project"""
    template_name = 'projects/manage_project.html'
    
    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id, creator=request.user)
        form = ProjectForm(instance=project)
        
        # Get team members
        members = ProjectMembership.objects.filter(project=project)
        
        # Get pending applications
        applications = Application.objects.filter(
            project=project,
            status='pending'
        ).order_by('-created_at')
        
        context = {
            'project': project,
            'form': form,
            'members': members,
            'applications': applications
        }
        return render(request, self.template_name, context)
    
    def post(self, request, project_id):
        project = get_object_or_404(Project, id=project_id, creator=request.user)
        form = ProjectForm(request.POST, instance=project)
        
        if form.is_valid():
            form.save()
            messages.success(request, f"Project '{project.title}' updated successfully.")
            return redirect('projects:manage_project', project_id=project_id)
        
        # Get team members and applications for context
        members = ProjectMembership.objects.filter(project=project)
        applications = Application.objects.filter(
            project=project,
            status='pending'
        ).order_by('-created_at')
        
        context = {
            'project': project,
            'form': form,
            'members': members,
            'applications': applications
        }
        return render(request, self.template_name, context)


class FindContributorsView(LoginRequiredMixin, ListView):
    """Find potential contributors for a project"""
    template_name = 'projects/find_contributors.html'
    context_object_name = 'contributors'
    paginate_by = 12
    
    def get_queryset(self):
        project_id = self.kwargs.get('project_id')
        project = get_object_or_404(Project, id=project_id, creator=self.request.user)
        
        # Get search query
        query = self.request.GET.get('q', '')
        tech_filter = self.request.GET.getlist('tech')
        
        # Start with all users
        queryset = UserProfile.objects.all()
        
        # Exclude users who are already members or the creator
        member_ids = ProjectMembership.objects.filter(
            project=project
        ).values_list('user_id', flat=True)
        
        queryset = queryset.exclude(
            Q(user_id__in=member_ids) | Q(user=self.request.user)
        )
        
        # Apply search
        if query:
            queryset = queryset.filter(
                Q(user__username__icontains=query) |
                Q(tech_stack__icontains=query)
            )
        
        # Apply tech filters
        if tech_filter:
            for tech in tech_filter:
                queryset = queryset.filter(tech_stack__icontains=tech)
        
        # Calculate match scores based on project required skills
        project_skills = project.get_required_skills_list()
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        project_id = self.kwargs.get('project_id')
        project = get_object_or_404(Project, id=project_id, creator=self.request.user)
        context['project'] = project
        
        # Get project's required skills
        project_skills = project.get_required_skills_list()
        
        # Calculate match scores for each contributor
        contributors = context['contributors']
        for contributor in contributors:
            user_skills = contributor.get_tech_stack_list()
            match_count = len(set(user_skills) & set(project_skills))
            
            if project_skills:
                contributor.match_percentage = int((match_count / len(project_skills)) * 100)
            else:
                contributor.match_percentage = 0
        
        # Sort by match percentage if project has skills
        if project_skills:
            context['contributors'] = sorted(
                contributors,
                key=lambda c: c.match_percentage,
                reverse=True
            )
        
        # Get all tech skills for filtering
        all_profiles = UserProfile.objects.all()
        tech_choices = set()
        for profile in all_profiles:
            tech_choices.update(profile.get_tech_stack_list())
        
        context['tech_choices'] = sorted(tech_choices)
        context['selected_tech'] = self.request.GET.getlist('tech')
        context['search_query'] = self.request.GET.get('q', '')
        
        # Check for pending invitations
        pending_invitations = Invitation.objects.filter(
            project=project,
            status='pending'
        ).values_list('recipient_id', flat=True)
        context['pending_invitations'] = pending_invitations
        
        return context


class InviteContributorView(LoginRequiredMixin, View):
    """Invite a user to a project"""
    
    def post(self, request, project_id, user_id):
        project = get_object_or_404(Project, id=project_id, creator=request.user)
        user = get_object_or_404(User, id=user_id)
        
        # Check if already a member
        is_member = ProjectMembership.objects.filter(
            project=project,
            user=user
        ).exists()
        
        if is_member:
            messages.warning(request, f"{user.username} is already a member of this project.")
            return redirect('projects:find_contributors', project_id=project_id)
        
        # Check if already invited
        invitation_exists = Invitation.objects.filter(
            project=project,
            recipient=user,
            status='pending'
        ).exists()
        
        if invitation_exists:
            messages.warning(request, f"{user.username} has already been invited to this project.")
            return redirect('projects:find_contributors', project_id=project_id)
        
        # Create invitation
        message = request.POST.get('message', '')
        Invitation.objects.create(
            project=project,
            sender=request.user,
            recipient=user,
            message=message
        )
        
        messages.success(request, f"Invitation sent to {user.username}.")
        return redirect('projects:find_contributors', project_id=project_id)


class SentInvitationsView(LoginRequiredMixin, ListView):
    """List view of sent invitations"""
    template_name = 'projects/sent_invitations.html'
    context_object_name = 'invitations'
    paginate_by = 10
    
    def get_queryset(self):
        return Invitation.objects.filter(sender=self.request.user).order_by('-created_at')


class CancelInvitationView(LoginRequiredMixin, View):
    """Cancel a sent invitation"""
    
    def post(self, request, invitation_id):
        invitation = get_object_or_404(Invitation, id=invitation_id, sender=request.user)
        
        if invitation.status == 'pending':
            invitation.delete()
            messages.success(request, "Invitation canceled successfully.")
        else:
            messages.warning(request, "Cannot cancel an invitation that has already been responded to.")
        
        return redirect('projects:sent_invitations')


class ApplicationsListView(LoginRequiredMixin, ListView):
    """List view of applications to user's projects"""
    template_name = 'projects/applications_list.html'
    context_object_name = 'applications'
    paginate_by = 10
    
    def get_queryset(self):
        # Get applications for projects created by user
        return Application.objects.filter(
            project__creator=self.request.user
        ).order_by('-created_at')


class ViewApplicationView(LoginRequiredMixin, View):
    """View an application details"""
    template_name = 'projects/view_application.html'
    
    def get(self, request, application_id):
        application = get_object_or_404(
            Application,
            id=application_id,
            project__creator=request.user
        )
        
        # Get applicant's profile details
        applicant = application.applicant
        
        context = {
            'application': application,
            'applicant': applicant,
            'tech_stack': applicant.profile.get_tech_stack_list() if hasattr(applicant, 'profile') else []
        }
        return render(request, self.template_name, context)


class UpdateApplicationView(LoginRequiredMixin, View):
    """Update application status"""
    
    def post(self, request, application_id):
        application = get_object_or_404(
            Application,
            id=application_id,
            project__creator=request.user
        )
        
        action = request.POST.get('action')
        
        if action == 'accept':
            application.status = 'accepted'
            application.save()
            
            # Add applicant to project members
            ProjectMembership.objects.create(
                user=application.applicant,
                project=application.project,
                role='member'
            )
            
            messages.success(request, f"{application.applicant.username} has been added to the project.")
        
        elif action == 'reject':
            application.status = 'rejected'
            application.save()
            messages.info(request, f"Application from {application.applicant.username} has been rejected.")
        
        return redirect('projects:applications_list')