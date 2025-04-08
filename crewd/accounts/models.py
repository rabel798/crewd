from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# Define tech stack choices
TECH_CHOICES = [
    'Python', 'Django', 'Flask', 'JavaScript', 'React', 'Vue', 'Angular', 
    'Node.js', 'Express', 'HTML/CSS', 'Bootstrap', 'Tailwind CSS', 
    'PHP', 'Laravel', 'CodeIgniter', 'Ruby', 'Ruby on Rails', 
    'Java', 'Spring', 'C#', '.NET', 'Go', 'Rust', 'Swift', 'Kotlin',
    'SQL', 'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Firebase',
    'Docker', 'Kubernetes', 'AWS', 'Azure', 'Google Cloud',
    'GraphQL', 'REST API', 'WebSockets', 'Microservices', 
    'Machine Learning', 'Data Science', 'UI/UX Design', 'Mobile Development'
]

class User(AbstractUser):
    """Custom user model with additional fields"""
    email = models.EmailField(unique=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    tech_stack = models.TextField(null=True, blank=True)  # Comma-separated list
    role = models.CharField(max_length=20, choices=[
        ('applicant', 'Applicant'),
        ('leader', 'Team Leader'),
        ('company', 'Company'),
    ], null=True, blank=True, default='applicant')
    created_at = models.DateTimeField(default=timezone.now)
    
    def get_tech_stack_list(self):
        """Return tech stack as a list"""
        if not self.tech_stack:
            return []
        return [tech.strip() for tech in self.tech_stack.split(',')]
    
    def __str__(self):
        return self.username