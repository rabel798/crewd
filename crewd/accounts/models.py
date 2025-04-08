from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    """Custom user model for the Crewd platform"""
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    tech_stack = models.TextField(blank=True, null=True)  # Comma-separated list of technologies
    role = models.CharField(
        max_length=20,
        choices=[
            ('applicant', 'Applicant'),
            ('leader', 'Team Leader'),
            ('company', 'Company'),
        ],
        default='applicant'
    )
    created_at = models.DateTimeField(default=timezone.now)
    
    def get_tech_stack_list(self):
        """Convert comma-separated tech stack to list"""
        if not self.tech_stack:
            return []
        return [tech.strip() for tech in self.tech_stack.split(',')]
    
    def __str__(self):
        return self.username
