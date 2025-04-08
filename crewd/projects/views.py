from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse
from django.views import View
from django.http import JsonResponse
import json
import os

# We'll import dashboard views specifically when needed
# Import User model
from django.contrib.auth import get_user_model
User = get_user_model()

# Import project models
from .models import Project, Application, Invitation, ProjectMembership, Group, Message, TECH_CHOICES

class IndexView(TemplateView):
    """Landing page view"""
    template_name = 'index.html'

    def get(self, request, *args, **kwargs):
        # If user is authenticated, redirect to dashboard
        if request.user.is_authenticated:
            if request.user.role == 'leader':
                return redirect('projects:team_leader_dashboard')
            else:
                return redirect('projects:applicant_dashboard')
                
        return super().get(request, *args, **kwargs)

class ViewProjectView(LoginRequiredMixin, View):
    """View a specific project"""
    
    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        
        # Check if user has already applied to this project
        has_applied = Application.objects.filter(
            project=project, 
            applicant=request.user
        ).exists()
        
        # Check if user is already a member of this project
        is_member = ProjectMembership.objects.filter(
            project=project, 
            user=request.user
        ).exists()
        
        context = {
            'project': project,
            'has_applied': has_applied,
            'is_member': is_member,
            'active_tab': 'projects'
        }
        
        return render(request, 'dashboard/applicant/view_project.html', context)

class ApplyProjectView(LoginRequiredMixin, View):
    """Apply to a project"""
    
    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        
        # Check if user is the project creator
        if project.creator == request.user:
            messages.error(request, "You cannot apply to your own project.")
            return redirect('projects:view_project', project_id=project_id)
        
        # Check if user has already applied
        if Application.objects.filter(project=project, applicant=request.user).exists():
            messages.info(request, "You have already applied to this project.")
            return redirect('projects:view_project', project_id=project_id)
        
        # Check if user is already a member
        if ProjectMembership.objects.filter(project=project, user=request.user).exists():
            messages.info(request, "You are already a member of this project.")
            return redirect('projects:view_project', project_id=project_id)
        
        context = {
            'project': project,
            'active_tab': 'projects'
        }
        
        return render(request, 'dashboard/applicant/apply_project.html', context)
    
    def post(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        message = request.POST.get('message', '').strip()
        
        # Create application
        Application.objects.create(
            project=project,
            applicant=request.user,
            message=message
        )
        
        messages.success(request, f"Your application to '{project.title}' has been sent!")
        return redirect('projects:projects_list')

class ProfileView(LoginRequiredMixin, View):
    """User profile view"""
    
    def get(self, request):
        # Get user tech stack
        user_tech_stack = request.user.get_tech_stack_list()
        
        context = {
            'active_tab': 'profile',
            'tech_choices': TECH_CHOICES,
            'user_tech_stack': user_tech_stack
        }
        
        return render(request, 'dashboard/profile.html', context)
    
    def post(self, request):
        username = request.POST.get('username')
        email = request.POST.get('email')
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        tech_stack = request.POST.getlist('tech_stack')
        profile_picture = request.FILES.get('profile_picture')
        
        user = request.user
        
        # Update username and email
        if username and email:
            # Check if username is already taken by another user
            if User.objects.exclude(id=user.id).filter(username=username).exists():
                messages.error(request, "Username already taken.")
                return redirect('projects:profile')
            
            # Check if email is already taken by another user
            if User.objects.exclude(id=user.id).filter(email=email).exists():
                messages.error(request, "Email already registered.")
                return redirect('projects:profile')
            
            user.username = username
            user.email = email
        
        # Update password if provided
        if current_password and new_password and confirm_password:
            if not user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
                return redirect('projects:profile')
                
            if new_password != confirm_password:
                messages.error(request, "New passwords do not match.")
                return redirect('projects:profile')
                
            user.set_password(new_password)
            messages.success(request, "Password updated successfully.")
        
        # Update tech stack
        user.tech_stack = ','.join(tech_stack) if tech_stack else ''
        
        # Update profile picture if provided
        if profile_picture:
            user.profile_picture = profile_picture
        
        user.save()
        
        messages.success(request, "Profile updated successfully!")
        return redirect('projects:profile')

class ViewUserProfileView(LoginRequiredMixin, View):
    """View another user's profile"""
    
    def get(self, request, user_id):
        profile_user = get_object_or_404(User, id=user_id)
        
        # Don't allow viewing your own profile this way
        if profile_user == request.user:
            return redirect('projects:profile')
            
        projects = Project.objects.filter(creator=profile_user, status='active')
        memberships = ProjectMembership.objects.filter(user=profile_user, project__status='active')
        
        # Get user's tech stack
        tech_stack = profile_user.get_tech_stack_list()
        
        context = {
            'profile_user': profile_user,
            'projects': projects,
            'memberships': memberships,
            'tech_stack': tech_stack,
            'active_tab': 'contributors'
        }
        
        return render(request, 'dashboard/view_profile.html', context)

class AnalyzeTechStackView(LoginRequiredMixin, View):
    """API view for analyzing project description to suggest tech stack"""
    
    def post(self, request):
        description = request.POST.get('description', '')
        
        if not description:
            return JsonResponse({'error': 'No description provided'}, status=400)
        
        try:
            # Try to use Grok API for analysis
            tech_stack = self._analyze_with_grok(description)
        except Exception as e:
            # Fallback to keyword-based analysis
            tech_stack = self._fallback_analyze(description)
        
        return JsonResponse({'tech_stack': tech_stack})
    
    def _analyze_with_grok(self, description):
        """Use Grok API to analyze project description and suggest tech stack"""
        api_key = os.environ.get('XAI_API_KEY')
        
        if not api_key:
            # Fallback if no API key
            return self._fallback_analyze(description)
        
        try:
            from openai import OpenAI
            
            # Create a custom OpenAI client with the X.AI endpoint
            client = OpenAI(base_url="https://api.x.ai/v1", api_key=api_key)
            
            prompt = f"""Analyze the following project description and suggest 
            a suitable tech stack (programming languages, frameworks, databases, etc.) 
            that would be appropriate for implementing it. Return a JSON array with 
            just the technology names, no explanations.
            
            Project description: {description}"""
            
            response = client.chat.completions.create(
                model="grok-2-1212",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Ensure the result is in expected format
            if isinstance(result, dict) and 'technologies' in result:
                return result['technologies']
            elif isinstance(result, list):
                return result
            else:
                # If unexpected format, fallback
                return self._fallback_analyze(description)
                
        except Exception as e:
            # Log error and fallback
            print(f"Error using Grok API: {e}")
            return self._fallback_analyze(description)
    
    def _fallback_analyze(self, description):
        """Fallback method to suggest tech stack based on keywords"""
        description = description.lower()
        suggestions = []
        
        # Map keywords to technologies
        keyword_map = {
            'web': ['JavaScript', 'HTML', 'CSS', 'React', 'Node.js'],
            'frontend': ['JavaScript', 'React', 'Vue.js', 'Angular'],
            'backend': ['Python', 'Node.js', 'Java', 'C#'],
            'mobile': ['React Native', 'Flutter', 'Swift', 'Kotlin'],
            'data': ['Python', 'R', 'SQL', 'Pandas', 'Jupyter'],
            'machine learning': ['Python', 'TensorFlow', 'PyTorch', 'scikit-learn'],
            'ai': ['Python', 'TensorFlow', 'PyTorch', 'NLTK'],
            'game': ['Unity', 'C#', 'C++', 'JavaScript'],
            'database': ['PostgreSQL', 'MySQL', 'MongoDB', 'Redis'],
            'cloud': ['AWS', 'Azure', 'Google Cloud', 'Docker'],
            'enterprise': ['Java', 'C#', '.NET', 'Oracle'],
            'ecommerce': ['Shopify', 'WooCommerce', 'React', 'Node.js'],
            'real-time': ['Node.js', 'Socket.io', 'WebSockets', 'Redis'],
            'blockchain': ['Solidity', 'Web3.js', 'Ethereum', 'React'],
            'iot': ['Python', 'C++', 'MQTT', 'Arduino'],
            'security': ['Python', 'Go', 'Rust', 'C++']
        }
        
        # Check for keywords in description
        for keyword, techs in keyword_map.items():
            if keyword in description:
                suggestions.extend(techs)
        
        # Deduplicate
        suggestions = list(set(suggestions))
        
        # If no matches, suggest generic stack
        if not suggestions:
            suggestions = ['JavaScript', 'Python', 'React', 'Node.js', 'PostgreSQL']
        
        # Limit to reasonable number
        return suggestions[:8]
