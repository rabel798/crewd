from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden
from .models import Project, Application, UserProfile, TECH_CHOICES
from .forms import UserRegisterForm, UserLoginForm, UserProfileForm, ProjectForm, ApplicationForm

def home(request):
    """Landing page"""
    return render(request, 'index.html')

def register_login_view(request):
    """Combined register and login view"""
    if request.method == 'POST':
        if 'register' in request.POST:
            form = UserRegisterForm(request.POST)
            if form.is_valid():
                user = form.save()
                
                # Handle profile picture upload
                if request.FILES.get('profile_picture'):
                    user.profile.profile_picture = request.FILES['profile_picture']
                
                # Process tech stack selection
                tech_stack = request.POST.getlist('tech_stack')
                if tech_stack:
                    user.profile.tech_stack = ','.join(tech_stack)
                
                user.profile.save()
                
                # Log the user in
                login(request, user)
                messages.success(request, 'Account created successfully')
                return redirect('role_selection')
        else:  # Login
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.profile.role:
                    return redirect('dashboard')
                return redirect('role_selection')
            messages.error(request, 'Invalid login credentials')
    
    return render(request, 'auth.html', {'tech_choices': TECH_CHOICES})

@login_required
def role_selection(request):
    """Role selection view"""
    if request.method == 'POST':
        role = request.POST.get('role')
        if role in ['applicant', 'leader', 'company']:
            request.user.profile.role = role
            request.user.profile.save()
            return redirect('dashboard')
        messages.error(request, 'Invalid role selected')
    
    return render(request, 'role_selection.html')

@login_required
def dashboard(request):
    """Dashboard view based on user role"""
    user = request.user
    
    if not user.profile.role:
        return redirect('role_selection')
    
    if user.profile.role == 'applicant':
        # Get user's applications and available projects
        applications = Application.objects.filter(applicant=user)
        applied_projects = Project.objects.filter(applications__applicant=user)
        available_projects = Project.objects.filter(status='active').exclude(applications__applicant=user)
        
        return render(request, 'dashboard_applicant.html', {
            'applications': applications,
            'applied_projects': applied_projects,
            'available_projects': available_projects
        })
    
    elif user.profile.role == 'leader':
        # Get leader's projects and their applications
        projects = Project.objects.filter(creator=user)
        project_applications = {}
        
        for project in projects:
            project_applications[project.id] = Application.objects.filter(project=project)
        
        return render(request, 'dashboard_leader.html', {
            'projects': projects,
            'project_applications': project_applications
        })
    
    elif user.profile.role == 'company':
        # Get company's projects and their applications
        projects = Project.objects.filter(creator=user)
        applications = Application.objects.filter(project__in=projects)
        
        return render(request, 'dashboard_company.html', {
            'projects': projects,
            'applications': applications
        })
    
    return redirect('home')

@login_required
def create_project(request):
    """Create a new project"""
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.creator = request.user
            project.save()
            messages.success(request, 'Project created successfully')
            return redirect('dashboard')
    else:
        form = ProjectForm()
    
    return render(request, 'project_create.html', {
        'form': form,
        'tech_choices': TECH_CHOICES
    })

@login_required
def view_project(request, project_id):
    """View a specific project"""
    project = get_object_or_404(Project, id=project_id)
    creator = project.creator
    
    # Check if user has already applied to this project
    applied = False
    if request.user.is_authenticated:
        applied = Application.objects.filter(project=project, applicant=request.user).exists()
    
    return render(request, 'project_view.html', {
        'project': project,
        'creator': creator,
        'applied': applied
    })

@login_required
def project_list(request):
    """List all projects with filtering"""
    projects = Project.objects.filter(status='active')
    
    # Apply filters if provided
    search = request.GET.get('search')
    skill = request.GET.get('skill')
    sort = request.GET.get('sort', 'newest')
    
    if search:
        projects = projects.filter(title__icontains=search) | projects.filter(description__icontains=search)
    
    if skill:
        projects = [p for p in projects if skill in p.get_required_skills_list()]
    
    # Apply sorting
    if sort == 'oldest':
        projects = projects.order_by('created_at')
    else:  # newest
        projects = projects.order_by('-created_at')
    
    return render(request, 'project_list.html', {
        'projects': projects,
        'tech_choices': TECH_CHOICES,
        'User': User  # Pass User model to template for lookups
    })

@login_required
def apply_project(request, project_id):
    """Apply to a project"""
    project = get_object_or_404(Project, id=project_id)
    
    # Only applicants can apply
    if request.user.profile.role != 'applicant':
        messages.error(request, 'Only applicants can apply to projects')
        return redirect('view_project', project_id=project_id)
    
    # Check if already applied
    if Application.objects.filter(project=project, applicant=request.user).exists():
        messages.error(request, 'You have already applied to this project')
        return redirect('view_project', project_id=project_id)
    
    if request.method == 'POST':
        form = ApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.project = project
            application.applicant = request.user
            application.save()
            messages.success(request, 'Application submitted successfully')
            return redirect('dashboard')
    else:
        form = ApplicationForm()
    
    return render(request, 'application_form.html', {
        'form': form,
        'project': project
    })

@login_required
def application_list(request):
    """List all applications"""
    user = request.user
    
    if user.profile.role == 'applicant':
        applications = Application.objects.filter(applicant=user)
        projects = {p.id: p for p in Project.objects.filter(applications__in=applications)}
    else:  # leader or company
        projects = {p.id: p for p in Project.objects.filter(creator=user)}
        applications = Application.objects.filter(project__in=projects.values())
    
    return render(request, 'application_list.html', {
        'applications': applications,
        'projects': projects
    })

@login_required
def update_application(request, application_id):
    """Update application status"""
    application = get_object_or_404(Application, id=application_id)
    
    # Only project creators can update applications
    if request.user != application.project.creator:
        return HttpResponseForbidden()
    
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['pending', 'accepted', 'rejected']:
            application.status = status
            application.save()
            messages.success(request, f'Application status updated to {status}')
    
    return redirect('application_list')

@login_required
def profile(request):
    """User profile view"""
    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, request.FILES, instance=request.user.profile)
        
        if profile_form.is_valid():
            # Update username and email
            request.user.username = request.POST.get('username')
            request.user.email = request.POST.get('email')
            request.user.save()
            
            profile_form.save()
            messages.success(request, 'Profile updated successfully')
            return redirect('profile')
    else:
        profile_form = UserProfileForm(instance=request.user.profile)
    
    return render(request, 'profile.html', {
        'form': profile_form,
        'tech_choices': TECH_CHOICES
    })

@login_required
def logout_view(request):
    """Logout view"""
    logout(request)
    return redirect('home')
