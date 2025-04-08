from django.db import models
from django.utils import timezone
from django.conf import settings

# Tech stack choices
TECH_CHOICES = [
    'Python', 'JavaScript', 'TypeScript', 'Java', 'C#', 'PHP', 'C++', 'Ruby', 'Swift',
    'Go', 'Rust', 'Kotlin', 'Scala', 'React', 'Angular', 'Vue.js', 'Node.js', 'Django',
    'Flask', 'Spring', 'Express', 'Laravel', 'Ruby on Rails', 'ASP.NET', 'PostgreSQL',
    'MySQL', 'MongoDB', 'Redis', 'Firebase', 'AWS', 'Azure', 'Google Cloud', 'Docker',
    'Kubernetes', 'Jenkins', 'Git', 'HTML', 'CSS', 'Bootstrap', 'Tailwind CSS', 'jQuery'
]

class Project(models.Model):
    """Project model representing team projects"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    title = models.CharField(max_length=100)
    description = models.TextField()
    required_skills = models.TextField(null=True, blank=True)  # Comma-separated list
    team_size = models.IntegerField()
    duration = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_projects')
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through='ProjectMembership', related_name='member_projects')
    created_at = models.DateTimeField(default=timezone.now)

    def get_required_skills_list(self):
        """Return required skills as a list"""
        if not self.required_skills:
            return []
        return [skill.strip() for skill in self.required_skills.split(',')]

    def __str__(self):
        return self.title


class ProjectMembership(models.Model):
    """Membership model for users and projects"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('removed', 'Removed'),
    ]

    ROLE_CHOICES = [
        ('contributor', 'Contributor'),
        ('leader', 'Team Leader'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='contributor')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('project', 'user')

    def __str__(self):
        return f"{self.user.username} - {self.project.title}"


class Application(models.Model):
    """Application model for applying to projects"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='applications')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('project', 'applicant')

    def __str__(self):
        return f"Application for {self.project.title} by {self.applicant.username}"


class Invitation(models.Model):
    """Invitation model for inviting users to projects"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='invitations')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_invitations')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_invitations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('project', 'recipient')

    def __str__(self):
        return f"Invitation to {self.project.title} for {self.recipient.username}"


class Group(models.Model):
    """Group model for project teams"""
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='group')
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through='GroupMembership', related_name='project_groups')
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name


class GroupMembership(models.Model):
    """Membership model for users and groups"""
    ROLE_CHOICES = [
        ('member', 'Member'),
        ('admin', 'Admin'),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('group', 'user')

    def __str__(self):
        return f"{self.user.username} - {self.group.name}"


class Message(models.Model):
    """Message model for group communication"""
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message by {self.sender.username} in {self.group.name}"


class TechStackAnalysis(models.Model):
    """Model to store Grok AI tech stack analysis results"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tech_stack_analyses')
    description = models.TextField()
    analysis_result = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Tech Stack Analysis for {self.project.title}"