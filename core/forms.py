from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Project, Application, UserProfile, TECH_CHOICES

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class UserLoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

class UserProfileForm(forms.ModelForm):
    profile_picture = forms.ImageField(required=False)
    tech_stack = forms.MultipleChoiceField(
        choices=[(tech, tech) for tech in TECH_CHOICES],
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    class Meta:
        model = UserProfile
        fields = ['profile_picture']
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.cleaned_data.get('tech_stack'):
            profile.tech_stack = ','.join(self.cleaned_data.get('tech_stack'))
        if commit:
            profile.save()
        return profile

class ProjectForm(forms.ModelForm):
    required_skills = forms.MultipleChoiceField(
        choices=[(tech, tech) for tech in TECH_CHOICES],
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    class Meta:
        model = Project
        fields = ['title', 'description', 'team_size', 'duration']
    
    def save(self, commit=True):
        project = super().save(commit=False)
        if self.cleaned_data.get('required_skills'):
            project.required_skills = ','.join(self.cleaned_data.get('required_skills'))
        if commit:
            project.save()
        return project

class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 5}),
        }
