from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, TemplateView
from django.urls import reverse_lazy
from django.db.models import Q

from .models import Project, Application
from .forms import ProjectForm, ApplicationForm
from accounts.models import TECH_CHOICES

class DashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard view for users based on their role"""
    
    def get_template_names(self):
        """Return appropriate template based on user role"""
        if not self.request.user.role:
            return ['accounts/role_selection.html']
        
        role = self.request.user.role
        return [f'projects/dashboard_{role}.html']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if not self.request.user.role:
            return context
        
        if self.request.user.role == 'applicant':
            # Get projects user has applied to
            applied_projects = Project.objects.filter(
                applications__applicant=self.request.user
            ).distinct()
            
            # Get all projects for browsing
            available_projects = Project.objects.filter(status='active')
            
            context.update({
                'applied_projects': applied_projects,
                'available_projects': available_projects
            })
            
        elif self.request.user.role == 'leader':
            # Get projects created by this team leader
            my_projects = Project.objects.filter(creator=self.request.user)
            
            # Get applications for each project
            project_applications = {}
            for project in my_projects:
                applications = Application.objects.filter(project=project)
                project_applications[project.id] = applications
            
            context.update({
                'projects': my_projects,
                'project_applications': project_applications
            })
            
        elif self.request.user.role == 'company':
            # Get all company projects
            company_projects = Project.objects.filter(creator=self.request.user)
            
            # Get all applications across all projects
            all_applications = Application.objects.filter(
                project__creator=self.request.user
            )
            
            context.update({
                'projects': company_projects,
                'applications': all_applications
            })
            
        return context

class ProjectListView(ListView):
    """View for listing all active projects"""
    model = Project
    template_name = 'projects/project_list.html'
    context_object_name = 'projects'
    
    def get_queryset(self):
        """Filter projects based on search criteria"""
        queryset = Project.objects.filter(status='active')
        
        # Search by title/description
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(description__icontains=search_query)
            )
        
        # Filter by skill
        skill = self.request.GET.get('skill')
        if skill:
            queryset = queryset.filter(required_skills__icontains=skill)
        
        # Sort projects
        sort_by = self.request.GET.get('sort', 'newest')
        if sort_by == 'newest':
            queryset = queryset.order_by('-created_at')
        elif sort_by == 'oldest':
            queryset = queryset.order_by('created_at')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tech_choices'] = TECH_CHOICES
        return context

class ProjectDetailView(DetailView):
    """View for displaying project details"""
    model = Project
    template_name = 'projects/project_view.html'
    context_object_name = 'project'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['creator'] = self.object.creator
        
        # Check if current user has already applied
        applied = False
        if self.request.user.is_authenticated:
            application = Application.objects.filter(
                project=self.object,
                applicant=self.request.user
            ).exists()
            applied = application
        
        context['applied'] = applied
        return context

class ProjectCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new project"""
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_create.html'
    success_url = reverse_lazy('dashboard')
    
    def dispatch(self, request, *args, **kwargs):
        """Check if user has appropriate role"""
        if request.user.role not in ['leader', 'company']:
            messages.error(request, 'Only team leaders and companies can create projects')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """Set the creator and required skills"""
        project = form.save(commit=False)
        project.creator = self.request.user
        
        # Process required skills selection
        required_skills = self.request.POST.getlist('required_skills')
        project.required_skills = ','.join(required_skills) if required_skills else ''
        
        project.save()
        messages.success(self.request, 'Project created successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tech_choices'] = TECH_CHOICES
        return context

class ApplicationCreateView(LoginRequiredMixin, CreateView):
    """View for applying to a project"""
    model = Application
    form_class = ApplicationForm
    template_name = 'projects/application_form.html'
    success_url = reverse_lazy('dashboard')
    
    def dispatch(self, request, *args, **kwargs):
        """Check if user has appropriate role"""
        if request.user.role != 'applicant':
            messages.error(request, 'Only applicants can apply to projects')
            return redirect('dashboard')
        
        # Check if already applied
        project = get_object_or_404(Project, pk=self.kwargs['pk'])
        existing_application = Application.objects.filter(
            project=project,
            applicant=request.user
        ).exists()
        
        if existing_application:
            messages.error(request, 'You have already applied to this project')
            return redirect('projects:project_detail', pk=project.pk)
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """Set the project and applicant"""
        application = form.save(commit=False)
        application.project = get_object_or_404(Project, pk=self.kwargs['pk'])
        application.applicant = self.request.user
        application.save()
        messages.success(self.request, 'Application submitted successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = get_object_or_404(Project, pk=self.kwargs['pk'])
        return context

class ApplicationListView(LoginRequiredMixin, ListView):
    """View for listing user applications"""
    model = Application
    template_name = 'projects/application_list.html'
    context_object_name = 'applications'
    
    def get_queryset(self):
        """Get applications based on user role"""
        if self.request.user.role == 'applicant':
            return Application.objects.filter(applicant=self.request.user)
        elif self.request.user.role in ['leader', 'company']:
            return Application.objects.filter(project__creator=self.request.user)
        return Application.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get project details for each application
        projects = {}
        for app in context['applications']:
            if app.project_id not in projects:
                projects[app.project_id] = app.project
        
        context['projects'] = projects
        return context

class ApplicationUpdateView(LoginRequiredMixin, View):
    """View for updating application status"""
    
    def post(self, request, pk):
        """Update application status"""
        application = get_object_or_404(Application, pk=pk)
        
        # Verify the project belongs to the current user
        if application.project.creator != request.user:
            messages.error(request, 'You do not have permission to update this application')
            return redirect('dashboard')
        
        # Update status
        new_status = request.POST.get('status')
        if new_status in ['pending', 'accepted', 'rejected']:
            application.status = new_status
            application.save()
            messages.success(request, 'Application status updated')
        else:
            messages.error(request, 'Invalid status')
        
        return redirect('projects:application_list')