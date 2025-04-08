from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import get_user_model

# Import models
from .models import Project, Application, Invitation, ProjectMembership, Group, Message, TECH_CHOICES

User = get_user_model()

class SwitchRoleView(LoginRequiredMixin, View):
    """View for switching between applicant and team leader roles"""
    
    def get(self, request):
        user = request.user
        
        if user.role == 'applicant':
            user.role = 'leader'
            user.save()
            messages.success(request, "You're now in Team Leader mode!")
            return redirect('projects:team_leader_dashboard')
        elif user.role == 'leader':
            user.role = 'applicant'
            user.save()
            messages.success(request, "You're now in Applicant mode!")
            return redirect('projects:applicant_dashboard')
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
        
        return render(request, 'dashboard/applicant_dashboard.html', context)


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
        
        return render(request, 'dashboard/team_leader_dashboard.html', context)


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
            return redirect('projects:invitations_list')
        
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
        
        return redirect('projects:invitations_list')


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
            return redirect('projects:groups_list')
        
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
            return redirect('projects:groups_list')
        
        message_content = request.POST.get('message', '').strip()
        
        if message_content:
            Message.objects.create(
                sender=request.user,
                content=message_content,
                group=group
            )
        
        return redirect('projects:view_group', group_id=group_id)


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
            return redirect('projects:create_project')
        
        try:
            team_size = int(team_size)
            if team_size < 1:
                raise ValueError("Team size must be at least 1.")
        except ValueError:
            messages.error(request, "Team size must be a valid number.")
            return redirect('projects:create_project')
        
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
        return redirect('projects:manage_project', project_id=project.id)


class ManageProjectView(LoginRequiredMixin, View):
    """View for managing a project as team leader"""
    
    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        
        # Check if user is the project creator
        if project.creator != request.user:
            messages.error(request, "You don't have permission to manage this project.")
            return redirect('projects:my_projects')
        
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
            return redirect('projects:my_projects')
        
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
                return redirect('projects:manage_project', project_id=project_id)
            
            project.duration = request.POST.get('duration', project.duration)
            required_skills = request.POST.getlist('required_skills')
            project.required_skills = ','.join(required_skills) if required_skills else ''
            
            project.save()
            
            messages.success(request, "Project updated successfully!")
        
        elif action == 'update_status':
            status = request.POST.get('status')
            
            if status not in ['active', 'completed', 'cancelled']:
                messages.error(request, "Invalid status.")
                return redirect('projects:manage_project', project_id=project_id)
            
            project.status = status
            project.save()
            
            messages.success(request, f"Project status updated to '{status}'.")
        
        elif action == 'remove_member':
            member_id = request.POST.get('member_id')
            
            if not member_id:
                messages.error(request, "Member ID is required.")
                return redirect('projects:manage_project', project_id=project_id)
            
            try:
                membership = ProjectMembership.objects.get(
                    project=project,
                    user_id=member_id
                )
                
                # Don't allow removing the project creator
                if membership.user == project.creator:
                    messages.error(request, "You cannot remove the project creator.")
                    return redirect('projects:manage_project', project_id=project_id)
                
                membership.delete()
                messages.success(request, "Member removed successfully.")
            except ProjectMembership.DoesNotExist:
                messages.error(request, "Membership not found.")
        
        return redirect('projects:manage_project', project_id=project_id)


class FindContributorsView(LoginRequiredMixin, View):
    """View for finding contributors for a project"""
    
    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id, creator=request.user)
        query = request.GET.get('q', '')
        tech_filter = request.GET.get('tech', '')
        
        # Get users excluding the ones already in the project
        existing_members_ids = ProjectMembership.objects.filter(project=project).values_list('user_id', flat=True)
        users = User.objects.exclude(id__in=existing_members_ids).exclude(id=request.user.id)
        
        # Check for existing pending invitations
        pending_invites_ids = Invitation.objects.filter(
            project=project,
            status='pending'
        ).values_list('recipient_id', flat=True)
        
        # Apply filters
        if query:
            users = users.filter(
                Q(username__icontains=query) | 
                Q(email__icontains=query) |
                Q(tech_stack__icontains=query)
            )
        
        if tech_filter:
            users = users.filter(tech_stack__icontains=tech_filter)
        
        # Mark users with pending invitations
        for user in users:
            user.has_pending_invite = user.id in pending_invites_ids
        
        # Get project's required skills
        project_skills = project.get_required_skills_list()
        
        # Find users with matching skills
        recommended_users = []
        for user in users:
            user_tech_stack = user.get_tech_stack_list()
            matching_skills = set(user_tech_stack) & set(project_skills)
            
            if matching_skills:
                user.matching_skill_count = len(matching_skills)
                user.matching_skills = list(matching_skills)
                recommended_users.append(user)
        
        # Sort by number of matching skills (descending)
        recommended_users.sort(key=lambda u: u.matching_skill_count, reverse=True)
        
        # Paginate other users
        other_users = [u for u in users if u not in recommended_users]
        paginator = Paginator(other_users, 12)  # 12 users per page
        page_number = request.GET.get('page', 1)
        other_users_page = paginator.get_page(page_number)
        
        context = {
            'active_tab': 'my_projects',
            'project': project,
            'recommended_users': recommended_users[:6],  # Limit to 6 users
            'other_users': other_users_page,
            'tech_filter': tech_filter,
            'query': query,
            'all_tech_options': TECH_CHOICES,
        }
        
        return render(request, 'dashboard/leader/find_contributors.html', context)


class InviteContributorView(LoginRequiredMixin, View):
    """View for inviting a contributor to a project"""
    
    def get(self, request, project_id, user_id):
        project = get_object_or_404(Project, id=project_id, creator=request.user)
        invited_user = get_object_or_404(User, id=user_id)
        
        # Check if user is already a member
        if ProjectMembership.objects.filter(project=project, user=invited_user).exists():
            messages.error(request, f"{invited_user.username} is already a member of this project.")
            return redirect('projects:find_contributors', project_id=project_id)
        
        # Check if there's already a pending invitation
        if Invitation.objects.filter(project=project, recipient=invited_user, status='pending').exists():
            messages.error(request, f"{invited_user.username} already has a pending invitation.")
            return redirect('projects:find_contributors', project_id=project_id)
        
        context = {
            'active_tab': 'my_projects',
            'project': project,
            'invited_user': invited_user,
        }
        
        return render(request, 'dashboard/leader/invite_contributor.html', context)
    
    def post(self, request, project_id, user_id):
        project = get_object_or_404(Project, id=project_id, creator=request.user)
        invited_user = get_object_or_404(User, id=user_id)
        message = request.POST.get('message', '').strip()
        
        # Create invitation
        Invitation.objects.create(
            project=project,
            sender=request.user,
            recipient=invited_user,
            message=message
        )
        
        messages.success(request, f"Invitation sent to {invited_user.username}!")
        return redirect('projects:find_contributors', project_id=project_id)


class SentInvitationsView(LoginRequiredMixin, View):
    """View for listing invitations sent by the team leader"""
    
    def get(self, request):
        status_filter = request.GET.get('status', 'pending')
        
        # Set status filter
        if status_filter not in ['pending', 'accepted', 'rejected', 'all']:
            status_filter = 'pending'
        
        # Get invitations for user's projects
        user_projects = Project.objects.filter(creator=request.user).values_list('id', flat=True)
        
        if status_filter == 'all':
            invitations = Invitation.objects.filter(project_id__in=user_projects)
        else:
            invitations = Invitation.objects.filter(project_id__in=user_projects, status=status_filter)
        
        invitations = invitations.select_related('project', 'recipient').order_by('-created_at')
        
        # Paginate results
        paginator = Paginator(invitations, 10)  # 10 invitations per page
        page_number = request.GET.get('page', 1)
        invitations_page = paginator.get_page(page_number)
        
        context = {
            'active_tab': 'sent_invitations',
            'invitations': invitations_page,
            'invitation_status': status_filter,
        }
        
        return render(request, 'dashboard/leader/sent_invitations.html', context)


class CancelInvitationView(LoginRequiredMixin, View):
    """View for cancelling a sent invitation"""
    
    def post(self, request, invitation_id):
        # Get invitation ensuring it's for the user's project
        invitation = get_object_or_404(
            Invitation,
            id=invitation_id,
            project__creator=request.user,
            status='pending'
        )
        
        # Delete the invitation
        invitation.delete()
        
        messages.success(request, "Invitation cancelled successfully.")
        return redirect('projects:sent_invitations')


class ApplicationsListView(LoginRequiredMixin, View):
    """View for listing applications to the team leader's projects"""
    
    def get(self, request):
        status_filter = request.GET.get('status', 'pending')
        
        # Set status filter
        if status_filter not in ['pending', 'accepted', 'rejected', 'all']:
            status_filter = 'pending'
        
        # Get applications for user's projects
        user_projects = Project.objects.filter(creator=request.user).values_list('id', flat=True)
        
        if status_filter == 'all':
            applications = Application.objects.filter(project_id__in=user_projects)
        else:
            applications = Application.objects.filter(project_id__in=user_projects, status=status_filter)
        
        applications = applications.select_related('project', 'applicant').order_by('-created_at')
        
        # Get pending count for notification badge
        pending_count = Application.objects.filter(
            project__creator=request.user,
            status='pending'
        ).count()
        
        # Paginate results
        paginator = Paginator(applications, 10)  # 10 applications per page
        page_number = request.GET.get('page', 1)
        applications_page = paginator.get_page(page_number)
        
        context = {
            'active_tab': 'applications',
            'applications': applications_page,
            'application_status': status_filter,
            'pending_count': pending_count,
        }
        
        return render(request, 'dashboard/leader/applications.html', context)


class ViewApplicationView(LoginRequiredMixin, View):
    """View for viewing and responding to an application"""
    
    def get(self, request, application_id):
        # Get application ensuring it's for the user's project
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
        # Get application ensuring it's for the user's project
        application = get_object_or_404(
            Application,
            id=application_id,
            project__creator=request.user
        )
        
        status = request.POST.get('status')
        
        if status not in ['accepted', 'rejected']:
            messages.error(request, "Invalid status.")
            return redirect('projects:view_application', application_id=application_id)
        
        # Update application status
        application.status = status
        application.save()
        
        if status == 'accepted':
            # Add applicant to project members
            project = application.project
            applicant = application.applicant
            
            # Check if already a member
            if not ProjectMembership.objects.filter(project=project, user=applicant).exists():
                ProjectMembership.objects.create(
                    user=applicant,
                    project=project,
                    role='member'
                )
            
            messages.success(request, f"Application accepted! {applicant.username} has been added to the project.")
        else:
            messages.info(request, "Application rejected.")
        
        return redirect('projects:applications_list')
