from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse, reverse_lazy
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import get_user_model

from accounts.models import TECH_CHOICES
from .models import Project, Application, Invitation, ProjectMembership, Group, Message
import requests
import json
import os

User = get_user_model()

class DashboardView(LoginRequiredMixin, View):
    """Base view for dashboard that redirects based on user role"""
    
    def get(self, request):
        user = request.user
        
        if not user.role:
            return redirect('accounts:role_selection')
        
        if user.role == 'applicant':
            return redirect('dashboard_applicant')
        elif user.role == 'leader':
            return redirect('dashboard_leader')
        else:
            # Default redirect for company role or others
            return redirect('accounts:role_selection')


class SwitchRoleView(LoginRequiredMixin, View):
    """View for switching between applicant and team leader roles"""
    
    def get(self, request):
        user = request.user
        
        if user.role == 'applicant':
            user.role = 'leader'
            user.save()
            messages.success(request, "You're now in Team Leader mode!")
            return redirect('dashboard_leader')
        elif user.role == 'leader':
            user.role = 'applicant'
            user.save()
            messages.success(request, "You're now in Applicant mode!")
            return redirect('dashboard_applicant')
        else:
            messages.error(request, "Invalid role switch.")
            return redirect('dashboard')


class ApplicantDashboardView(LoginRequiredMixin, View):
    """Dashboard view for applicant role"""
    
    def get(self, request):
        user = request.user
        
        if user.role != 'applicant':
            messages.warning(request, "Switched to Applicant view.")
            user.role = 'applicant'
            user.save()
        
        # Get recommended projects based on user tech stack
        recommended_projects = []
        user_tech_stack = user.get_tech_stack_list()
        
        if user_tech_stack:
            # Find projects that require at least one of the user's skills
            all_projects = Project.objects.filter(status='active').exclude(creator=user)
            
            for project in all_projects:
                project_skills = project.get_required_skills_list()
                matching_skills = set(user_tech_stack) & set(project_skills)
                
                if matching_skills:
                    project.matching_skill_count = len(matching_skills)
                    recommended_projects.append(project)
            
            # Sort by number of matching skills (descending)
            recommended_projects.sort(key=lambda p: p.matching_skill_count, reverse=True)
            recommended_projects = recommended_projects[:6]  # Limit to 6 projects
        
        # Get active memberships (projects user is currently participating in)
        active_memberships = ProjectMembership.objects.filter(
            user=user,
            project__status='active'
        ).select_related('project').order_by('-joined_at')[:3]
        
        # Get pending invitations count for notification
        pending_invitations_count = Invitation.objects.filter(
            recipient=user,
            status='pending'
        ).count()
        
        context = {
            'active_tab': 'dashboard',
            'recommended_projects': recommended_projects,
            'active_memberships': active_memberships,
            'pending_invitations_count': pending_invitations_count,
        }
        
        return render(request, 'dashboard/applicant.html', context)


class TeamLeaderDashboardView(LoginRequiredMixin, View):
    """Dashboard view for team leader role"""
    
    def get(self, request):
        user = request.user
        
        if user.role != 'leader':
            messages.warning(request, "Switched to Team Leader view.")
            user.role = 'leader'
            user.save()
        
        # Get user's projects
        user_projects = Project.objects.filter(creator=user).order_by('-created_at')[:6]
        
        # Get recent applications to user's projects
        recent_applications = Application.objects.filter(
            project__creator=user
        ).select_related('applicant', 'project').order_by('-created_at')[:5]
        
        # Get pending applications count for notification
        pending_applications_count = Application.objects.filter(
            project__creator=user,
            status='pending'
        ).count()
        
        context = {
            'active_tab': 'dashboard',
            'user_projects': user_projects,
            'recent_applications': recent_applications,
            'pending_applications_count': pending_applications_count,
        }
        
        return render(request, 'dashboard/leader.html', context)


class ContributorsListView(LoginRequiredMixin, View):
    """View for listing all contributors (users)"""
    
    def get(self, request):
        query = request.GET.get('q', '')
        tech_filter = request.GET.get('tech', '')
        role_filter = request.GET.get('role', '')
        
        users = User.objects.all().exclude(id=request.user.id)
        
        # Apply filters
        if query:
            users = users.filter(
                Q(username__icontains=query) | 
                Q(email__icontains=query) |
                Q(tech_stack__icontains=query)
            )
        
        if tech_filter:
            users = users.filter(tech_stack__icontains=tech_filter)
            
        if role_filter:
            users = users.filter(role=role_filter)
        
        # Paginate results
        paginator = Paginator(users, 12)  # 12 users per page
        page_number = request.GET.get('page', 1)
        contributors = paginator.get_page(page_number)
        
        context = {
            'active_tab': 'contributors',
            'active_subtab': 'contributors',
            'contributors': contributors,
            'all_tech_options': TECH_CHOICES,
        }
        
        return render(request, 'dashboard/applicant/contributors.html', context)


class ProjectsListView(LoginRequiredMixin, View):
    """View for listing all projects"""
    
    def get(self, request):
        query = request.GET.get('q', '')
        tech_filter = request.GET.get('tech', '')
        status_filter = request.GET.get('status', '')
        
        projects = Project.objects.all().exclude(creator=request.user)
        
        # Apply filters
        if query:
            projects = projects.filter(
                Q(title__icontains=query) | 
                Q(description__icontains=query)
            )
        
        if tech_filter:
            projects = projects.filter(required_skills__icontains=tech_filter)
            
        if status_filter:
            projects = projects.filter(status=status_filter)
        else:
            # Default to active projects
            projects = projects.filter(status='active')
        
        # Get recommended projects based on user tech stack
        recommended_projects = []
        user_tech_stack = request.user.get_tech_stack_list()
        
        if user_tech_stack:
            # Find projects that require at least one of the user's skills
            for project in projects:
                project_skills = project.get_required_skills_list()
                matching_skills = set(user_tech_stack) & set(project_skills)
                
                if matching_skills:
                    project.matching_skill_count = len(matching_skills)
                    recommended_projects.append(project)
            
            # Sort by number of matching skills (descending)
            recommended_projects.sort(key=lambda p: p.matching_skill_count, reverse=True)
            recommended_projects = recommended_projects[:6]  # Limit to 6 projects
            
            # Remove recommended projects from main list to avoid duplication
            project_ids = [p.id for p in recommended_projects]
            projects = projects.exclude(id__in=project_ids)
        
        # Paginate results
        paginator = Paginator(projects, 9)  # 9 projects per page
        page_number = request.GET.get('page', 1)
        projects_page = paginator.get_page(page_number)
        
        context = {
            'active_tab': 'projects',
            'active_subtab': 'projects',
            'projects': projects_page,
            'recommended_projects': recommended_projects,
            'all_tech_options': TECH_CHOICES,
        }
        
        return render(request, 'dashboard/applicant/projects.html', context)


class InvitationsListView(LoginRequiredMixin, View):
    """View for listing invitations received by the user"""
    
    def get(self, request):
        status_filter = request.GET.get('status', 'pending')
        
        # Set status filter
        if status_filter not in ['pending', 'accepted', 'rejected', 'all']:
            status_filter = 'pending'
        
        # Get invitations
        if status_filter == 'all':
            invitations = Invitation.objects.filter(recipient=request.user)
        else:
            invitations = Invitation.objects.filter(recipient=request.user, status=status_filter)
        
        invitations = invitations.select_related('project', 'sender').order_by('-created_at')
        
        # Get pending count for notification badge
        pending_count = Invitation.objects.filter(recipient=request.user, status='pending').count()
        
        # Paginate results
        paginator = Paginator(invitations, 10)  # 10 invitations per page
        page_number = request.GET.get('page', 1)
        invitations_page = paginator.get_page(page_number)
        
        context = {
            'active_tab': 'invitations',
            'invitations': invitations_page,
            'invitation_status': status_filter,
            'pending_count': pending_count,
        }
        
        return render(request, 'dashboard/applicant/invitations.html', context)


class UpdateInvitationView(LoginRequiredMixin, View):
    """View for updating invitation status (accept/reject)"""
    
    def post(self, request, invitation_id):
        invitation = get_object_or_404(Invitation, id=invitation_id, recipient=request.user)
        status = request.POST.get('status')
        
        if status not in ['accepted', 'rejected']:
            messages.error(request, "Invalid status.")
            return redirect('invitations_list')
        
        invitation.status = status
        invitation.save()
        
        if status == 'accepted':
            # Add user to project members
            project = invitation.project
            ProjectMembership.objects.create(
                user=request.user,
                project=project,
                role='member'
            )
            
            # Create or get project group
            group, created = Group.objects.get_or_create(
                project=project,
                defaults={'name': f"{project.title} Group"}
            )
            
            messages.success(request, f"You have accepted the invitation to join {project.title}.")
        else:
            messages.info(request, "Invitation rejected.")
        
        return redirect('invitations_list')


class MyContributionsView(LoginRequiredMixin, View):
    """View for listing user's contributions (project memberships)"""
    
    def get(self, request):
        status_filter = request.GET.get('status', 'active')
        
        # Get memberships
        memberships = ProjectMembership.objects.filter(user=request.user)
        
        if status_filter == 'active':
            memberships = memberships.filter(project__status='active')
        elif status_filter == 'completed':
            memberships = memberships.filter(project__status='completed')
        # 'all' shows everything
        
        memberships = memberships.select_related('project', 'project__creator').order_by('-joined_at')
        
        # Paginate results
        paginator = Paginator(memberships, 9)  # 9 projects per page
        page_number = request.GET.get('page', 1)
        contributions = paginator.get_page(page_number)
        
        context = {
            'active_tab': 'contributions',
            'contributions': contributions,
            'contribution_status': status_filter,
        }
        
        return render(request, 'dashboard/applicant/contributions.html', context)


class GroupsListView(LoginRequiredMixin, View):
    """View for listing user's groups"""
    
    def get(self, request):
        # Get memberships that have groups
        memberships = ProjectMembership.objects.filter(
            user=request.user,
            project__group__isnull=False
        ).select_related('project', 'project__group', 'project__creator').order_by('-project__group__created_at')
        
        # Paginate results
        paginator = Paginator(memberships, 9)  # 9 groups per page
        page_number = request.GET.get('page', 1)
        groups = paginator.get_page(page_number)
        
        context = {
            'active_tab': 'groups',
            'groups': groups,
        }
        
        return render(request, 'dashboard/applicant/groups.html', context)


class ViewGroupView(LoginRequiredMixin, View):
    """View for a specific group chat"""
    
    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        project = group.project
        
        # Check if user is a member of the project
        if not ProjectMembership.objects.filter(user=request.user, project=project).exists():
            messages.error(request, "You don't have access to this group.")
            return redirect('groups_list')
        
        # Get messages
        messages_list = Message.objects.filter(group=group).order_by('created_at')
        
        # Get members
        members = ProjectMembership.objects.filter(project=project).select_related('user')
        
        context = {
            'active_tab': 'groups',
            'group': group,
            'project': project,
            'messages': messages_list,
            'members': members,
        }
        
        return render(request, 'dashboard/group_chat.html', context)
    
    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        project = group.project
        
        # Check if user is a member of the project
        if not ProjectMembership.objects.filter(user=request.user, project=project).exists():
            messages.error(request, "You don't have access to this group.")
            return redirect('groups_list')
        
        message_content = request.POST.get('message', '').strip()
        
        if message_content:
            Message.objects.create(
                sender=request.user,
                content=message_content,
                group=group
            )
        
        return redirect('view_group', group_id=group_id)


class MyProjectsView(LoginRequiredMixin, View):
    """View for listing team leader's projects"""
    
    def get(self, request):
        status_filter = request.GET.get('status', 'active')
        
        # Get projects
        projects = Project.objects.filter(creator=request.user)
        
        if status_filter != 'all':
            projects = projects.filter(status=status_filter)
        
        projects = projects.order_by('-created_at')
        
        # Paginate results
        paginator = Paginator(projects, 9)  # 9 projects per page
        page_number = request.GET.get('page', 1)
        projects_page = paginator.get_page(page_number)
        
        context = {
            'active_tab': 'my_projects',
            'projects': projects_page,
            'project_status': status_filter,
        }
        
        return render(request, 'dashboard/leader/my_projects.html', context)


class CreateProjectView(LoginRequiredMixin, View):
    """View for creating a new project"""
    
    def get(self, request):
        context = {
            'active_tab': 'create_project',
            'tech_choices': TECH_CHOICES,
        }
        
        return render(request, 'dashboard/leader/create_project.html', context)
    
    def post(self, request):
        title = request.POST.get('title')
        description = request.POST.get('description')
        team_size = request.POST.get('team_size')
        duration = request.POST.get('duration')
        required_skills = request.POST.getlist('required_skills')
        
        if not all([title, description, team_size, duration]):
            messages.error(request, "All fields are required.")
            return redirect('create_project')
        
        try:
            team_size = int(team_size)
            if team_size < 1:
                raise ValueError("Team size must be at least 1.")
        except ValueError:
            messages.error(request, "Team size must be a valid number.")
            return redirect('create_project')
        
        # Create project
        project = Project.objects.create(
            title=title,
            description=description,
            team_size=team_size,
            duration=duration,
            required_skills=','.join(required_skills) if required_skills else '',
            creator=request.user
        )
        
        # Add creator as project member (admin)
        ProjectMembership.objects.create(
            user=request.user,
            project=project,
            role='admin'
        )
        
        # Create project group
        Group.objects.create(
            name=f"{project.title} Group",
            project=project
        )
        
        messages.success(request, f"Project '{project.title}' created successfully!")
        return redirect('manage_project', project_id=project.id)


class ManageProjectView(LoginRequiredMixin, View):
    """View for managing a project as team leader"""
    
    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        
        # Check if user is the project creator
        if project.creator != request.user:
            messages.error(request, "You don't have permission to manage this project.")
            return redirect('my_projects')
        
        # Get project members
        members = ProjectMembership.objects.filter(project=project).select_related('user')
        
        # Get pending applications
        pending_applications = Application.objects.filter(
            project=project,
            status='pending'
        ).select_related('applicant').order_by('-created_at')
        
        # Get pending invitations
        pending_invitations = Invitation.objects.filter(
            project=project,
            status='pending'
        ).select_related('recipient').order_by('-created_at')
        
        context = {
            'active_tab': 'my_projects',
            'project': project,
            'members': members,
            'pending_applications': pending_applications,
            'pending_invitations': pending_invitations,
            'tech_choices': TECH_CHOICES,
        }
        
        return render(request, 'dashboard/leader/manage_project.html', context)
    
    def post(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        
        # Check if user is the project creator
        if project.creator != request.user:
            messages.error(request, "You don't have permission to manage this project.")
            return redirect('my_projects')
        
        action = request.POST.get('action')
        
        if action == 'update_project':
            # Update project details
            project.title = request.POST.get('title', project.title)
            project.description = request.POST.get('description', project.description)
            
            try:
                team_size = int(request.POST.get('team_size', project.team_size))
                if team_size < 1:
                    raise ValueError()
                project.team_size = team_size
            except ValueError:
                messages.error(request, "Team size must be a valid number.")
                return redirect('manage_project', project_id=project_id)
            
            project.duration = request.POST.get('duration', project.duration)
            required_skills = request.POST.getlist('required_skills')
            project.required_skills = ','.join(required_skills) if required_skills else ''
            
            project.save()
            messages.success(request, "Project details updated successfully!")
        
        elif action == 'update_status':
            status = request.POST.get('status')
            if status in ['active', 'completed', 'cancelled']:
                project.status = status
                project.save()
                messages.success(request, f"Project status updated to {status}.")
        
        elif action == 'remove_member':
            member_id = request.POST.get('member_id')
            if member_id:
                try:
                    membership = ProjectMembership.objects.get(
                        project=project,
                        user_id=member_id
                    )
                    # Don't allow removing the creator
                    if membership.user != project.creator:
                        membership.delete()
                        messages.success(request, "Team member removed successfully.")
                    else:
                        messages.error(request, "Cannot remove the project creator.")
                except ProjectMembership.DoesNotExist:
                    messages.error(request, "Member not found.")
        
        return redirect('manage_project', project_id=project_id)


class FindContributorsView(LoginRequiredMixin, View):
    """View for finding contributors for a project"""
    
    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        
        # Check if user is the project creator
        if project.creator != request.user:
            messages.error(request, "You don't have permission to manage this project.")
            return redirect('my_projects')
        
        query = request.GET.get('q', '')
        tech_filter = request.GET.get('tech', '')
        match_filter = request.GET.get('match', 'recommended')
        
        # Get all users except the current user
        users = User.objects.exclude(id=request.user.id)
        
        # Apply filters
        if query:
            users = users.filter(
                Q(username__icontains=query) | 
                Q(email__icontains=query) |
                Q(tech_stack__icontains=query)
            )
        
        if tech_filter:
            users = users.filter(tech_stack__icontains=tech_filter)
        
        # Get already invited users
        already_invited = Invitation.objects.filter(project=project).values_list('recipient_id', flat=True)
        
        # Get users who have already applied
        already_applied = Application.objects.filter(project=project).values_list('applicant_id', flat=True)
        
        # Get current project members
        project_members = ProjectMembership.objects.filter(project=project).values_list('user_id', flat=True)
        
        # Find recommended users based on tech stack match
        recommended_users = []
        project_skills = project.get_required_skills_list()
        
        if project_skills and match_filter == 'recommended':
            for user in users:
                user_skills = user.get_tech_stack_list()
                matching_skills = set(user_skills) & set(project_skills)
                
                if matching_skills:
                    user.matching_skill_count = len(matching_skills)
                    user.matching_skill_percent = (len(matching_skills) / len(project_skills)) * 100
                    recommended_users.append(user)
            
            # Sort by percentage of matching skills (descending)
            recommended_users.sort(key=lambda u: u.matching_skill_percent, reverse=True)
        
        # Paginate results if showing all
        if match_filter == 'all':
            paginator = Paginator(users, 12)  # 12 users per page
            page_number = request.GET.get('page', 1)
            contributors = paginator.get_page(page_number)
        else:
            contributors = []
        
        context = {
            'active_tab': 'my_projects',
            'project': project,
            'contributors': contributors,
            'recommended_users': recommended_users[:9],  # Limit to 9 recommended users
            'already_invited': already_invited,
            'already_applied': already_applied,
            'project_members': project_members,
            'all_tech_options': TECH_CHOICES,
            'match_filter': match_filter,
        }
        
        return render(request, 'dashboard/leader/find_contributors.html', context)


class InviteContributorView(LoginRequiredMixin, View):
    """View for inviting a contributor to a project"""
    
    def get(self, request, project_id, user_id):
        project = get_object_or_404(Project, id=project_id, creator=request.user)
        user = get_object_or_404(User, id=user_id)
        
        # Check if user is already invited
        if Invitation.objects.filter(project=project, recipient=user).exists():
            messages.warning(request, f"{user.username} has already been invited to this project.")
            return redirect('find_contributors', project_id=project_id)
        
        # Check if user has already applied
        if Application.objects.filter(project=project, applicant=user).exists():
            messages.warning(request, f"{user.username} has already applied to this project.")
            return redirect('find_contributors', project_id=project_id)
        
        # Check if user is already a member
        if ProjectMembership.objects.filter(project=project, user=user).exists():
            messages.warning(request, f"{user.username} is already a member of this project.")
            return redirect('find_contributors', project_id=project_id)
        
        # Create invitation
        Invitation.objects.create(
            project=project,
            recipient=user,
            sender=request.user
        )
        
        messages.success(request, f"Invitation sent to {user.username}.")
        return redirect('find_contributors', project_id=project_id)


class SentInvitationsView(LoginRequiredMixin, View):
    """View for listing invitations sent by the team leader"""
    
    def get(self, request):
        status_filter = request.GET.get('status', 'pending')
        selected_project = request.GET.get('project')
        
        # Set status filter
        if status_filter not in ['pending', 'accepted', 'rejected', 'all']:
            status_filter = 'pending'
        
        # Get user's projects
        user_projects = Project.objects.filter(creator=request.user)
        
        # Get invitations
        invitations = Invitation.objects.filter(sender=request.user)
        
        if status_filter != 'all':
            invitations = invitations.filter(status=status_filter)
        
        if selected_project:
            try:
                project_id = int(selected_project)
                invitations = invitations.filter(project_id=project_id)
            except ValueError:
                pass
        
        invitations = invitations.select_related('project', 'recipient').order_by('-created_at')
        
        # Get pending count for notification badge
        pending_count = Invitation.objects.filter(sender=request.user, status='pending').count()
        
        # Paginate results
        paginator = Paginator(invitations, 10)  # 10 invitations per page
        page_number = request.GET.get('page', 1)
        invitations_page = paginator.get_page(page_number)
        
        context = {
            'active_tab': 'sent_invitations',
            'invitations': invitations_page,
            'invitation_status': status_filter,
            'pending_count': pending_count,
            'user_projects': user_projects,
            'selected_project': int(selected_project) if selected_project and selected_project.isdigit() else None,
        }
        
        return render(request, 'dashboard/leader/sent_invitations.html', context)


class CancelInvitationView(LoginRequiredMixin, View):
    """View for cancelling a sent invitation"""
    
    def post(self, request, invitation_id):
        invitation = get_object_or_404(Invitation, id=invitation_id, sender=request.user, status='pending')
        
        invitation.delete()
        messages.success(request, "Invitation cancelled successfully.")
        
        return redirect('sent_invitations')


class ApplicationsListView(LoginRequiredMixin, View):
    """View for listing applications to the team leader's projects"""
    
    def get(self, request):
        status_filter = request.GET.get('status', 'pending')
        selected_project = request.GET.get('project')
        
        # Set status filter
        if status_filter not in ['pending', 'accepted', 'rejected', 'all']:
            status_filter = 'pending'
        
        # Get user's projects
        user_projects = Project.objects.filter(creator=request.user)
        
        # Get applications
        applications = Application.objects.filter(project__creator=request.user)
        
        if status_filter != 'all':
            applications = applications.filter(status=status_filter)
        
        if selected_project:
            try:
                project_id = int(selected_project)
                applications = applications.filter(project_id=project_id)
            except ValueError:
                pass
        
        applications = applications.select_related('project', 'applicant').order_by('-created_at')
        
        # Get pending count for notification badge
        pending_count = Application.objects.filter(project__creator=request.user, status='pending').count()
        
        # Paginate results
        paginator = Paginator(applications, 10)  # 10 applications per page
        page_number = request.GET.get('page', 1)
        applications_page = paginator.get_page(page_number)
        
        context = {
            'active_tab': 'applications',
            'applications': applications_page,
            'application_status': status_filter,
            'pending_count': pending_count,
            'user_projects': user_projects,
            'selected_project': int(selected_project) if selected_project and selected_project.isdigit() else None,
        }
        
        return render(request, 'dashboard/leader/applications.html', context)


class ViewApplicationView(LoginRequiredMixin, View):
    """View for viewing and responding to an application"""
    
    def get(self, request, application_id):
        application = get_object_or_404(
            Application, 
            id=application_id,
            project__creator=request.user
        )
        
        context = {
            'active_tab': 'applications',
            'application': application,
        }
        
        return render(request, 'dashboard/leader/view_application.html', context)


class UpdateApplicationView(LoginRequiredMixin, View):
    """View for updating an application status (accept/reject)"""
    
    def post(self, request, application_id):
        application = get_object_or_404(
            Application, 
            id=application_id,
            project__creator=request.user
        )
        
        status = request.POST.get('status')
        
        if status not in ['accepted', 'rejected']:
            messages.error(request, "Invalid status.")
            return redirect('view_application', application_id=application_id)
        
        application.status = status
        application.save()
        
        if status == 'accepted':
            # Add applicant to project members
            project = application.project
            applicant = application.applicant
            
            # Check if already a member
            if not ProjectMembership.objects.filter(user=applicant, project=project).exists():
                ProjectMembership.objects.create(
                    user=applicant,
                    project=project,
                    role='member'
                )
            
            # Create or get project group
            group, created = Group.objects.get_or_create(
                project=project,
                defaults={'name': f"{project.title} Group"}
            )
            
            messages.success(request, f"Application accepted! {applicant.username} has been added to the project team.")
        else:
            messages.info(request, "Application rejected.")
        
        return redirect('applications_list')


class AnalyzeTechStackView(LoginRequiredMixin, View):
    """API view for analyzing project description to suggest tech stack"""
    
    def post(self, request):
        # Parse the JSON data from the request body
        try:
            data = json.loads(request.body)
            description = data.get('description', '')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        if not description:
            return JsonResponse({'error': 'Project description is required'}, status=400)
        
        # Get Grok API key
        grok_api_key = "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"
        
        if not grok_api_key:
            # If no API key, use a fallback logic to suggest tech stack
            return self._fallback_analyze(description)
        
        # Prepare the API request
        headers = {
            "Authorization": f"Bearer {grok_api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""
        Based on this project description, suggest which technologies from the list below would be required.
        Return only the technologies from this list that would be needed, as a JSON array:
        
        {', '.join(TECH_CHOICES)}
        
        Project description: {description}
        
        Your response should be a JSON array like ["Python", "Django", "PostgreSQL"]
        """
        
        try:
            response = requests.post(
                "https://api.grok.ai/v1/chat/completions",
                headers=headers,
                json={
                    "model": "mixtral-8x7b-32768",
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant that analyzes project descriptions and suggests the required tech stack."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 200
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                # Extract JSON array from the response
                import re
                json_match = re.search(r'\[.*\]', content)
                if json_match:
                    try:
                        skills = json.loads(json_match.group(0))
                        # Filter out any skills not in our tech choices
                        valid_skills = [skill for skill in skills if skill in TECH_CHOICES]
                        return JsonResponse({'skills': valid_skills})
                    except json.JSONDecodeError:
                        pass
            
            # If we get here, something went wrong with the API
            return self._fallback_analyze(description)
            
        except Exception as e:
            return self._fallback_analyze(description)
    
    def _fallback_analyze(self, description):
        """Fallback method to suggest tech stack based on keywords"""
        description = description.lower()
        suggested_skills = []
        
        # Define keyword to tech mapping
        keyword_mapping = {
            'web': ['HTML/CSS', 'JavaScript', 'React', 'Bootstrap'],
            'website': ['HTML/CSS', 'JavaScript', 'Bootstrap'],
            'frontend': ['HTML/CSS', 'JavaScript', 'React', 'Angular', 'Vue'],
            'backend': ['Python', 'Django', 'Node.js', 'Express'],
            'database': ['SQL', 'PostgreSQL', 'MySQL', 'MongoDB'],
            'mobile': ['React Native', 'Swift', 'Kotlin', 'Mobile Development'],
            'app': ['JavaScript', 'React Native', 'Mobile Development'],
            'data': ['Python', 'Data Science', 'PostgreSQL', 'MySQL'],
            'analytics': ['Python', 'Data Science'],
            'machine learning': ['Python', 'Machine Learning'],
            'ai': ['Python', 'Machine Learning'],
            'cloud': ['AWS', 'Azure', 'Google Cloud'],
            'docker': ['Docker', 'Kubernetes'],
            'microservices': ['Microservices', 'Docker', 'Kubernetes'],
            'api': ['REST API', 'Express', 'Django', 'Node.js'],
        }
        
        # Check for specific technologies mentioned directly
        for tech in TECH_CHOICES:
            if tech.lower() in description:
                suggested_skills.append(tech)
        
        # Check for keywords
        for keyword, techs in keyword_mapping.items():
            if keyword in description:
                for tech in techs:
                    if tech not in suggested_skills:
                        suggested_skills.append(tech)
        
        # Limit to a reasonable number
        return JsonResponse({'skills': suggested_skills[:10]})


class ViewProfileView(LoginRequiredMixin, View):
    """View for viewing another user's profile"""
    
    def get(self, request, user_id):
        profile_user = get_object_or_404(User, id=user_id)
        
        # Get user's projects
        if profile_user.role == 'leader':
            projects = Project.objects.filter(creator=profile_user, status='active')
        else:
            projects = Project.objects.filter(members=profile_user, status='active')
        
        context = {
            'profile_user': profile_user,
            'projects': projects,
        }
        
        return render(request, 'dashboard/view_profile.html', context)