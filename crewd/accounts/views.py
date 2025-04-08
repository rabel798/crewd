from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import login, authenticate
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import FormView
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from django.contrib.auth.models import User
from .models import UserProfile
from .forms import UserRegisterForm, UserProfileForm, UserLoginForm


class RegisterView(FormView):
    """User registration view"""
    template_name = 'accounts/register.html'
    form_class = UserRegisterForm
    success_url = reverse_lazy('projects:switch_role')
    
    def form_valid(self, form):
        # Create new user
        user = form.save()
        
        # Log the user in
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password1')
        user = authenticate(username=username, password=password)
        login(self.request, user)
        
        messages.success(self.request, f'Account created for {username}! Please select your role.')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hide_nav'] = True  # Hide navbar for cleaner auth pages
        return context


class LoginView(FormView):
    """User login view"""
    template_name = 'accounts/login.html'
    form_class = UserLoginForm
    success_url = reverse_lazy('projects:switch_role')
    
    def form_valid(self, form):
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = authenticate(username=username, password=password)
        
        if user is not None:
            login(self.request, user)
            messages.success(self.request, f'Welcome back, {username}!')
            
            # Redirect to previous page if available
            next_page = self.request.GET.get('next')
            if next_page:
                return redirect(next_page)
        
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hide_nav'] = True  # Hide navbar for cleaner auth pages
        return context


class ProfileView(LoginRequiredMixin, View):
    """User profile view"""
    template_name = 'accounts/profile.html'
    
    def get(self, request):
        user_form = UserProfileForm(instance=request.user.profile)
        return render(request, self.template_name, {'form': user_form})
    
    def post(self, request):
        user_form = UserProfileForm(request.POST, request.FILES, instance=request.user.profile)
        
        if user_form.is_valid():
            user_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('projects:profile')
        
        return render(request, self.template_name, {'form': user_form})