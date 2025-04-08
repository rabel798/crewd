from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# List of technology choices for tech stack selection
TECH_CHOICES = [
    'Python', 'JavaScript', 'TypeScript', 'Java', 'C#', 'C++',
    'PHP', 'Ruby', 'Swift', 'Kotlin', 'Go', 'Rust',
    'React', 'Angular', 'Vue', 'Node.js', 'Django', 'Flask',
    'Spring', 'Express', 'Laravel', 'Ruby on Rails',
    'MongoDB', 'PostgreSQL', 'MySQL', 'Redis', 'SQLite',
    'Docker', 'Kubernetes', 'AWS', 'Azure', 'Google Cloud',
    'HTML/CSS', 'TailwindCSS', 'Bootstrap', 'SASS',
    'Git', 'CI/CD', 'Agile', 'Scrum',
    'Mobile Development', 'Web Development', 'Desktop Applications',
    'Machine Learning', 'AI', 'Data Science', 'DevOps', 'UI/UX Design'
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
    ], null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def get_tech_stack_list(self):
        """Return tech stack as a list"""
        if not self.tech_stack:
            return []
        return [tech.strip() for tech in self.tech_stack.split(',') if tech.strip()]
    
    def __str__(self):
        return self.username