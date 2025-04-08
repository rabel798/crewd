from django import forms
from .models import Project, Application

class ProjectForm(forms.ModelForm):
    """Form for creating a new project"""
    title = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Enter a descriptive title for your project'
        }),
        max_length=100
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'placeholder': 'Describe your project in detail including goals, challenges, and expected outcomes'
        })
    )
    team_size = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Number of team members needed'
        })
    )
    duration = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'e.g., 2 weeks, 3 months'
        })
    )
    
    class Meta:
        model = Project
        fields = ('title', 'description', 'team_size', 'duration')

class ApplicationForm(forms.ModelForm):
    """Form for submitting an application to a project"""
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'placeholder': 'Introduce yourself, explain why you\'re interested in this project, and describe how your skills and experience make you a good fit...'
        })
    )
    
    class Meta:
        model = Application
        fields = ('message',)