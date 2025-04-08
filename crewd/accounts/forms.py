from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

from projects.models import TECH_CHOICES

User = get_user_model()

class UserRegisterForm(UserCreationForm):
    """Form for user registration"""
    email = forms.EmailField()
    tech_stack = forms.MultipleChoiceField(
        choices=[(tech, tech) for tech in TECH_CHOICES],
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    profile_picture = forms.ImageField(required=False)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'profile_picture', 'tech_stack']

class UserProfileForm(forms.ModelForm):
    """Form for updating user profile"""
    tech_stack = forms.MultipleChoiceField(
        choices=[(tech, tech) for tech in TECH_CHOICES],
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'profile_picture']
