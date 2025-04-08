from django import forms
from .models import Project, Application
from accounts.forms import TECH_CHOICES

class ProjectForm(forms.ModelForm):
    """Form for creating and updating projects"""
    required_skills = forms.MultipleChoiceField(
        choices=[(tech, tech) for tech in TECH_CHOICES],
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    class Meta:
        model = Project
        fields = ['title', 'description', 'required_skills', 'team_size', 'duration']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'team_size': forms.NumberInput(attrs={'class': 'form-control'}),
            'duration': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 2 weeks, 3 months'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set initial values for required_skills if the project has them
        instance = kwargs.get('instance')
        if instance and instance.required_skills:
            self.initial['required_skills'] = instance.get_required_skills_list()
    
    def save(self, commit=True):
        project = super().save(commit=False)
        
        # Process required skills
        if self.cleaned_data.get('required_skills'):
            project.required_skills = ','.join(self.cleaned_data['required_skills'])
        
        if commit:
            project.save()
        
        return project


class ApplicationForm(forms.ModelForm):
    """Form for project applications"""
    class Meta:
        model = Application
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Why are you a good fit for this project?'}),
        }