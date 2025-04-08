from django.shortcuts import render, redirect
from django.views.generic import FormView, TemplateView, UpdateView
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings

from .forms import LoginForm, RegisterForm, ProfileForm
from .models import User, TECH_CHOICES

class LoginView(FormView):
    """View for user login"""
    template_name = 'accounts/auth.html'
    form_class = LoginForm
    success_url = reverse_lazy('projects:dashboard')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_login'] = True
        return context
    
    def form_valid(self, form):
        email = form.cleaned_data['username']  # Using username field for email
        password = form.cleaned_data['password']
        user = authenticate(self.request, username=email, password=password)
        
        if user is not None:
            login(self.request, user)
            messages.success(self.request, f"Welcome back, {user.username}!")
            
            # Redirect based on whether user has selected a role
            if user.role:
                return redirect(self.get_success_url())
            else:
                return redirect('accounts:role_selection')
        else:
            messages.error(self.request, "Invalid email or password.")
            return self.form_invalid(form)


class RegisterView(FormView):
    """View for user registration"""
    template_name = 'accounts/auth.html'
    form_class = RegisterForm
    success_url = reverse_lazy('accounts:role_selection')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_login'] = False
        return context
    
    def form_valid(self, form):
        user = form.save()
        
        # Handle profile picture
        if 'profile_picture' in self.request.FILES:
            user.profile_picture = self.request.FILES['profile_picture']
            user.save()
            
        # Authenticate and log in the user
        email = form.cleaned_data['email']
        password = form.cleaned_data['password1']
        user = authenticate(self.request, username=email, password=password)
        
        if user is not None:
            login(self.request, user)
            messages.success(self.request, f"Account created successfully! Welcome, {user.username}!")
            return redirect(self.success_url)
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, "There was an error with your registration. Please check the form and try again.")
        return super().form_invalid(form)


class RoleSelectionView(LoginRequiredMixin, TemplateView):
    """View for selecting user role"""
    template_name = 'accounts/role_selection.html'
    
    def post(self, request, *args, **kwargs):
        role = request.POST.get('role')
        
        if role in ['applicant', 'leader', 'company']:
            user = request.user
            user.role = role
            user.save()
            
            messages.success(request, f"Role updated to {role.title()}!")
            return redirect('projects:dashboard')
        else:
            messages.error(request, "Invalid role selection.")
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
        context['user_tech_stack'] = self.request.user.get_tech_stack_list()
        return context
    
    def form_valid(self, form):
        user = form.save(commit=False)
        
        # Handle tech stack
        tech_stack = self.request.POST.getlist('tech_stack')
        if tech_stack:
            user.tech_stack = ','.join(tech_stack)
        
        # Handle profile picture
        if 'profile_picture' in self.request.FILES:
            user.profile_picture = self.request.FILES['profile_picture']
            
        user.save()
        messages.success(self.request, "Profile updated successfully!")
        return super().form_valid(form)