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
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through='ProjectMembership', related_name='member_projects')
    
    def get_required_skills_list(self):
        """Return required skills as a list"""
        if not self.required_skills:
            return []
        return [skill.strip() for skill in self.required_skills.split(',')]
    
    def __str__(self):
        return self.title


class ProjectMembership(models.Model):
    """Model for tracking membership in projects"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(default=timezone.now)
    role = models.CharField(max_length=50, default='member')  # e.g., member, admin, etc.
    
    class Meta:
        unique_together = ('user', 'project')
        
    def __str__(self):
        return f"{self.user.username} in {self.project.title}"


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


class Invitation(models.Model):
    """Model for storing project invitations sent to users"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='invitations')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='invitations')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_invitations')
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], default='pending')
    message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Invitation to {self.recipient.username} for {self.project.title}"


class Group(models.Model):
    """Model for project group chats"""
    name = models.CharField(max_length=100)
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='group')
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return self.name


class Message(models.Model):
    """Model for messages in group chats or direct messages"""
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='messages', null=True, blank=True)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                                 related_name='received_messages', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        if self.group:
            return f"Message in {self.group.name} from {self.sender.username}"
        return f"Message to {self.recipient.username} from {self.sender.username}"