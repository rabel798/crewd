from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import FormView, TemplateView
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import uuid

from .forms import RegisterForm, LoginForm, ProfileForm
from .models import User, TECH_CHOICES

class LoginView(FormView):
    """View for user login"""
    template_name = 'accounts/auth.html'
    form_class = LoginForm
    redirect_authenticated_user = True
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['login_form'] = self.get_form()
        context['register_form'] = RegisterForm()
        context['tech_choices'] = TECH_CHOICES
        return context
    
    def post(self, request, *args, **kwargs):
        form = LoginForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            # Try authenticating with email as username
            user = authenticate(request, username=username, password=password)
            if user is None:
                # Try getting user by email and authenticate with username
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    user = None
            
            if user is not None:
                login(request, user)
                messages.success(request, 'Login successful!')
                return redirect('accounts:role_selection')
            else:
                messages.error(request, 'Invalid email or password combination')
        
        return render(request, self.template_name, {
            'login_form': form,
            'register_form': RegisterForm(),
            'tech_choices': TECH_CHOICES
        })

class RegisterView(FormView):
    """View for user registration"""
    template_name = 'accounts/auth.html'
    form_class = RegisterForm
    redirect_authenticated_user = True
    success_url = reverse_lazy('accounts:role_selection')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['login_form'] = LoginForm()
        context['register_form'] = self.get_form()
        context['tech_choices'] = TECH_CHOICES
        return context
    
    def form_valid(self, form):
        # Save the user object
        user = form.save(commit=False)
        
        # Handle profile picture upload
        if self.request.FILES.get('profile_picture'):
            profile_pic = self.request.FILES['profile_picture']
            filename = f"{uuid.uuid4()}_{profile_pic.name}"
            path = default_storage.save(f'profile_pics/{filename}', ContentFile(profile_pic.read()))
            user.profile_picture = path
        
        # Process tech stack selection
        tech_stack = self.request.POST.getlist('tech_stack')
        user.tech_stack = ','.join(tech_stack) if tech_stack else ''
        
        user.save()
        login(self.request, user)
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Registration failed. Please check the form errors.')
        return self.render_to_response(self.get_context_data(form=form))

class RoleSelectionView(LoginRequiredMixin, TemplateView):
    """View for selecting user role"""
    template_name = 'accounts/role_selection.html'
    
    def post(self, request, *args, **kwargs):
        role = request.POST.get('role')
        if role in ['applicant', 'leader', 'company']:
            request.user.role = role
            request.user.save()
            if role == 'applicant':
                return redirect('projects:dashboard_applicant')
            elif role == 'leader':
                return redirect('projects:dashboard_leader')
            elif role == 'company':
                return redirect('projects:dashboard')
        messages.error(request, 'Invalid role selected')
        return self.get(request, *args, **kwargs)

class ProfileView(LoginRequiredMixin, FormView):
    """View for user profile management"""
    template_name = 'accounts/profile.html'
    form_class = ProfileForm
    success_url = reverse_lazy('accounts:profile')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tech_choices'] = TECH_CHOICES
        context['user'] = self.request.user
        return context
    
    def form_valid(self, form):
        user = form.save(commit=False)
        
        # Handle profile picture upload
        if self.request.FILES.get('profile_picture'):
            # Delete old profile picture if it exists
            if user.profile_picture:
                default_storage.delete(user.profile_picture.name)
            
            profile_pic = self.request.FILES['profile_picture']
            filename = f"{uuid.uuid4()}_{profile_pic.name}"
            path = default_storage.save(f'profile_pics/{filename}', ContentFile(profile_pic.read()))
            user.profile_picture = path
        
        # Process tech stack selection
        tech_stack = self.request.POST.getlist('tech_stack')
        user.tech_stack = ','.join(tech_stack) if tech_stack else ''
        
        user.save()
        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)

def logout_view(request):
    """View for user logout"""
    logout(request)
    return redirect('index')