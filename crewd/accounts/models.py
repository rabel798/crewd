from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """Extended user profile model"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    tech_stack = models.TextField(null=True, blank=True)  # Comma-separated list
    role = models.CharField(max_length=20, choices=[
        ('applicant', 'Applicant'),
        ('leader', 'Team Leader'),
        ('company', 'Company'),
    ], default='applicant')
    created_at = models.DateTimeField(default=timezone.now)

    def get_tech_stack_list(self):
        """Convert comma-separated tech stack to list"""
        if not self.tech_stack:
            return []
        return [tech.strip() for tech in self.tech_stack.split(',') if tech.strip()]

    def __str__(self):
        return f"{self.user.username}'s Profile"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a profile when a new user is created"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the profile when the user is saved"""
    instance.profile.save()