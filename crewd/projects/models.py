from django.db import models
from django.utils import timezone
from django.conf import settings

User = settings.AUTH_USER_MODEL

class Project(models.Model):
    """Model for projects"""
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
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_projects')
    members = models.ManyToManyField(User, related_name='member_projects', blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_required_skills_list(self):
        """Return required skills as a list"""
        if not self.required_skills:
            return []
        return [skill.strip() for skill in self.required_skills.split(',') if skill.strip()]
    
    def __str__(self):
        return self.title


class Application(models.Model):
    """Model for project applications"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], default='pending')
    message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('project', 'applicant')
    
    def __str__(self):
        return f"{self.applicant} - {self.project}"


class ProjectInvitation(models.Model):
    """Model for invitations to join projects"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='invitations')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invitations')
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], default='pending')
    message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('project', 'user')
    
    def __str__(self):
        return f"{self.project} invitation to {self.user}"


class Contribution(models.Model):
    """Model for tracking user contributions to projects"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='contributions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contributions')
    description = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.user}'s contribution to {self.project}"


class Group(models.Model):
    """Model for project communication groups"""
    name = models.CharField(max_length=100)
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='group')
    members = models.ManyToManyField(User, related_name='project_groups')
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return self.name


class GroupMessage(models.Model):
    """Model for messages in project groups"""
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Message from {self.sender} in {self.group}"