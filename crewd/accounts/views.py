from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import login, authenticate
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse
from django.views.generic import CreateView
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from .models import User
from projects.models import TECH_CHOICES
from .forms import UserRegisterForm, UserProfileForm

class RegisterView(View):
    """Registration view for creating a new user account"""
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('projects:applicant_dashboard')
            
        form = UserRegisterForm()
        return render(request, 'accounts/register.html', {'form': form})
    
    def post(self, request):
        form = UserRegisterForm(request.POST, request.FILES)
        
        if form.is_valid():
            # Create user but don't save password yet
            user = form.save(commit=False)
            # Set password correctly (handles hashing)
            user.set_password(form.cleaned_data['password1'])
            
            # Set default role
            user.role = 'applicant'
            
            # Save tech stack if provided
            tech_stack = request.POST.getlist('tech_stack')
            if tech_stack:
                user.tech_stack = ','.join(tech_stack)
            
            # Handle profile picture
            if 'profile_picture' in request.FILES:
                profile_pic = request.FILES['profile_picture']
                user.profile_picture = profile_pic
                
            user.save()
            
            # Log the user in
            login(request, user)
            messages.success(request, f"Account created for {user.username}!")
            return redirect('projects:applicant_dashboard')
        
        return render(request, 'accounts/register.html', {'form': form})

class ProfileUpdateView(LoginRequiredMixin, View):
    """View for updating user profile"""
    
    def get(self, request):
        form = UserProfileForm(instance=request.user)
        user_tech_stack = request.user.get_tech_stack_list()
        
        context = {
            'form': form,
            'tech_choices': TECH_CHOICES,
            'user_tech_stack': user_tech_stack
        }
        
        return render(request, 'accounts/profile.html', context)
    
    def post(self, request):
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        
        if form.is_valid():
            user = form.save(commit=False)
            
            # Handle tech stack selections
            tech_stack = request.POST.getlist('tech_stack')
            user.tech_stack = ','.join(tech_stack) if tech_stack else ''
            
            # Save changes
            user.save()
            messages.success(request, "Your profile has been updated!")
            return redirect('projects:profile')
        
        user_tech_stack = request.user.get_tech_stack_list()
        context = {
            'form': form,
            'tech_choices': TECH_CHOICES,
            'user_tech_stack': user_tech_stack
        }
        
        return render(request, 'accounts/profile.html', context)
