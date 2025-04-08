from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse
from django.views import View
from django.http import JsonResponse

import json
import os
import openai
from django.conf import settings

from .models import Project, Application
from accounts.models import UserProfile
from .forms import ProjectForm, ApplicationForm


class IndexView(TemplateView):
    """Landing page view"""
    template_name = 'index_standalone.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hide_nav'] = True  # Hide navbar for landing page
        return context


class ViewProjectView(LoginRequiredMixin, View):
    """View details of a project"""
    template_name = 'projects/view_project.html'
    
    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        has_applied = Application.objects.filter(
            project=project, applicant=request.user
        ).exists()
        
        context = {
            'project': project,
            'has_applied': has_applied,
            'required_skills': project.get_required_skills_list(),
            'is_owner': project.creator == request.user
        }
        return render(request, self.template_name, context)


class ApplyProjectView(LoginRequiredMixin, View):
    """Apply to a project"""
    template_name = 'projects/apply_project.html'
    
    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        
        if project.creator == request.user:
            messages.warning(request, "You cannot apply to your own project.")
            return redirect('projects:view_project', project_id=project_id)
        
        has_applied = Application.objects.filter(
            project=project, applicant=request.user
        ).exists()
        
        if has_applied:
            messages.warning(request, "You have already applied to this project.")
            return redirect('projects:view_project', project_id=project_id)
        
        form = ApplicationForm()
        return render(request, self.template_name, {'form': form, 'project': project})
    
    def post(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        form = ApplicationForm(request.POST)
        
        if form.is_valid():
            application = form.save(commit=False)
            application.project = project
            application.applicant = request.user
            application.save()
            
            messages.success(request, f"Successfully applied to {project.title}.")
            return redirect('projects:my_contributions')
        
        return render(request, self.template_name, {'form': form, 'project': project})


class ProfileView(LoginRequiredMixin, View):
    """View user profile"""
    template_name = 'accounts/profile.html'
    
    def get(self, request):
        user = request.user
        context = {
            'user': user,
            'tech_stack': user.profile.get_tech_stack_list() if hasattr(user, 'profile') else []
        }
        return render(request, self.template_name, context)


class ViewUserProfileView(LoginRequiredMixin, View):
    """View another user's profile"""
    template_name = 'accounts/view_profile.html'
    
    def get(self, request, user_id):
        user_profile = get_object_or_404(UserProfile, user_id=user_id)
        context = {
            'profile_user': user_profile.user,
            'tech_stack': user_profile.get_tech_stack_list()
        }
        return render(request, self.template_name, context)


class AnalyzeTechStackView(LoginRequiredMixin, View):
    """API view for analyzing tech stack"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            project_description = data.get('description', '')
            
            if not project_description:
                return JsonResponse({'error': 'Project description is required'}, status=400)
            
            # Get API key from environment variables
            api_key = settings.XAI_API_KEY
            if not api_key:
                return JsonResponse({
                    'error': 'API key not configured',
                    'suggestions': []
                }, status=500)
            
            # Initialize OpenAI client
            client = openai.OpenAI(base_url="https://api.x.ai/v1", api_key=api_key)
            
            # Prompt for the model
            prompt = f"""
            Based on the following project description, suggest appropriate skills and technologies 
            that would be needed for this project. Format the response as a JSON array of strings.
            
            Project Description: {project_description}
            
            Example response format:
            ["JavaScript", "React", "Node.js", "Express", "MongoDB"]
            
            Please limit suggestions to 5-10 most relevant technologies.
            """
            
            # Call the model
            response = client.chat.completions.create(
                model="grok-2-1212",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are a tech stack analyzer that suggests appropriate technologies for projects."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract suggestions
            content = response.choices[0].message.content
            suggestions = json.loads(content).get('technologies', [])
            
            return JsonResponse({'suggestions': suggestions})
        except Exception as e:
            return JsonResponse({'error': str(e), 'suggestions': []}, status=500)