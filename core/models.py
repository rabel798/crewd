from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Tech stack choices
TECH_CHOICES = [
    'Python', 'JavaScript', 'React', 'Angular', 'Vue', 'Node.js', 
    'Django', 'Flask', 'Ruby', 'Java', 'PHP', 'C#', 'Swift', 'Kotlin',
    'HTML/CSS', 'UI/UX Design', 'Database', 'DevOps', 'Mobile', 'AI/ML'
]

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    tech_stack = models.TextField(null=True, blank=True)  # Comma-separated list
    role = models.CharField(max_length=20, choices=[
        ('applicant', 'Applicant'),
        ('leader', 'Team Leader'),
        ('company', 'Company'),
    ], null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def get_tech_stack_list(self):
        return self.tech_stack.split(',') if self.tech_stack else []
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

class Project(models.Model):
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
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    created_at = models.DateTimeField(default=timezone.now())
    
    def get_required_skills_list(self):
        return self.required_skills.split(',') if self.required_skills else []
    
    def __str__(self):
        return self.title

class Application(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], default='pending')
    message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Application from {self.applicant.username} for {self.project.title}"

# Create signal handlers to create UserProfile when User is created
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()
