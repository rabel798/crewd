from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

from .models import UserProfile

# List of technology skills to choose from
TECH_CHOICES = [
    'Python', 'JavaScript', 'TypeScript', 'React', 'Angular', 'Vue', 
    'Django', 'Flask', 'Node.js', 'Express', 'MongoDB', 'PostgreSQL', 
    'MySQL', 'HTML', 'CSS', 'SASS', 'Less', 'AWS', 'Azure', 'GCP',
    'Docker', 'Kubernetes', 'DevOps', 'CI/CD', 'Git', 'Agile', 'Scrum',
    'UI/UX Design', 'Figma', 'Adobe XD', 'Photoshop', 'Illustrator',
    'Data Science', 'Machine Learning', 'AI', 'Data Analysis', 'TensorFlow',
    'PyTorch', 'NLP', 'Computer Vision', 'Big Data', 'Hadoop', 'Spark',
    'Mobile Development', 'iOS', 'Android', 'React Native', 'Flutter',
    'Game Development', 'Unity', 'Unreal Engine'
]

class UserRegisterForm(UserCreationForm):
    """Form for user registration with additional fields"""
    email = forms.EmailField()
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make fields more user-friendly
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username'})
        self.fields['email'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Email'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})

class UserLoginForm(AuthenticationForm):
    """Form for user login with styled fields"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username'})
        self.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})

class UserProfileForm(forms.ModelForm):
    """Form for updating user profile"""
    profile_picture = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    tech_stack = forms.MultipleChoiceField(
        choices=[(tech, tech) for tech in TECH_CHOICES],
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    class Meta:
        model = UserProfile
        fields = ['profile_picture', 'tech_stack']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial values for tech_stack if the user already has them
        if self.instance and self.instance.tech_stack:
            self.initial['tech_stack'] = self.instance.get_tech_stack_list()
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        
        # Process tech stack
        if self.cleaned_data.get('tech_stack'):
            profile.tech_stack = ','.join(self.cleaned_data['tech_stack'])
        
        if commit:
            profile.save()
        
        return profile