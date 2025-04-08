from django.shortcuts import render, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.views import View

from .models import Project, Application
from accounts.models import TECH_CHOICES

class ProjectListView(ListView):
    """View for listing all projects"""
    model = Project
    template_name = 'projects/project_list.html'
    context_object_name = 'projects'
    paginate_by = 9
    
    def get_queryset(self):
        return Project.objects.filter(status='active').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tech_choices'] = TECH_CHOICES
        return context


class ProjectDetailView(DetailView):
    """View for viewing a project's details"""
    model = Project
    template_name = 'projects/project_detail.html'
    context_object_name = 'project'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_object()
        
        # Check if the user has already applied
        if self.request.user.is_authenticated:
            context['has_applied'] = Application.objects.filter(
                project=project, 
                applicant=self.request.user
            ).exists()
            
            # Check if the user is the project creator
            context['is_creator'] = (project.creator == self.request.user)
            
            # Check if the user is a member
            context['is_member'] = project.members.filter(id=self.request.user.id).exists()
        
        # Get team members (excluding the creator)
        context['team_members'] = project.members.exclude(id=project.creator.id)
        
        return context


class CreateProjectView(LoginRequiredMixin, CreateView):
    """View for creating a new project"""
    model = Project
    template_name = 'projects/create_project.html'
    fields = ['title', 'description', 'required_skills', 'team_size', 'duration']
    success_url = reverse_lazy('projects:project_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tech_choices'] = TECH_CHOICES
        return context
    
    def form_valid(self, form):
        form.instance.creator = self.request.user
        messages.success(self.request, "Project created successfully!")
        return super().form_valid(form)


class ApplyToProjectView(LoginRequiredMixin, View):
    """View for applying to a project"""
    
    def get(self, request, pk):
        project = Project.objects.get(pk=pk)
        
        # Check if the user is the creator
        if project.creator == request.user:
            messages.error(request, "You cannot apply to your own project.")
            return redirect('projects:project_detail', pk=pk)
        
        # Check if the user has already applied
        if Application.objects.filter(project=project, applicant=request.user).exists():
            messages.warning(request, "You have already applied to this project.")
            return redirect('projects:project_detail', pk=pk)
        
        # Check if the user is already a member
        if project.members.filter(id=request.user.id).exists():
            messages.warning(request, "You are already a member of this project.")
            return redirect('projects:project_detail', pk=pk)
        
        return render(request, 'projects/apply_project.html', {'project': project})
    
    def post(self, request, pk):
        project = Project.objects.get(pk=pk)
        message = request.POST.get('message', '')
        
        # Create application
        Application.objects.create(
            project=project,
            applicant=request.user,
            message=message
        )
        
        messages.success(request, f"Your application for {project.title} has been submitted!")
        return redirect('projects:project_detail', pk=pk)


class DashboardView(LoginRequiredMixin, View):
    """View for the user's dashboard"""
    
    def get(self, request):
        user = request.user
        
        if user.role == 'applicant':
            return redirect('projects:dashboard_applicant')
        elif user.role == 'leader':
            return redirect('projects:dashboard_leader')
        else:
            # Default to role selection
            return redirect('accounts:role_selection')