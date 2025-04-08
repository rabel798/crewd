from django.db import models
from django.utils import timezone
from django.conf import settings

class Project(models.Model):
    """Model for storing project information"""
    title = models.CharField(max_length=100)
    description = models.TextField()
    required_skills = models.TextField(null=True, blank=True)  # Comma-separated list
    team_size = models.IntegerField()
    duration = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=[
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], default='active')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='projects')
    created_at = models.DateTimeField(default=timezone.now)
    
    def get_required_skills_list(self):
        """Return required skills as a list"""
        if not self.required_skills:
            return []
        return [skill.strip() for skill in self.required_skills.split(',')]
    
    def __str__(self):
        return self.title


class Application(models.Model):
    """Model for storing project applications"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='applications')
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], default='pending')
    message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.applicant.username}'s application for {self.project.title}"