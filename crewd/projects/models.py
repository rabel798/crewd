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
    title = models.CharField(max_length=100)
    description = models.TextField()
    required_skills = models.TextField(null=True, blank=True)
    team_size = models.IntegerField()
    duration = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='active'
    )
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_projects')
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through='ProjectMembership', related_name='member_projects')
    created_at = models.DateTimeField(default=timezone.now)

    def get_required_skills_list(self):
        if not self.required_skills:
            return []
        return [skill.strip() for skill in self.required_skills.split(',')]

    def __str__(self):
        return self.title

class ProjectMembership(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=20,
        choices=[
            ('contributor', 'Contributor'),
            ('leader', 'Team Leader'),
        ],
        default='contributor'
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('removed', 'Removed'),
        ],
        default='active'
    )
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('project', 'user')

    def __str__(self):
        return f"{self.user.username} - {self.project.title}"

class Application(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='applications')
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected'),
        ],
        default='pending'
    )
    message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('project', 'applicant')

    def __str__(self):
        return f"Application for {self.project.title} by {self.applicant.username}"

class Group(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='group')
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through='GroupMembership', related_name='project_groups')
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name

class GroupMembership(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=20,
        choices=[
            ('member', 'Member'),
            ('admin', 'Admin'),
        ],
        default='member'
    )
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('group', 'user')

    def __str__(self):
        return f"{self.user.username} - {self.group.name}"

class TechStackAnalysis(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    description = models.TextField()
    analysis_result = models.JSONField()  
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

class Message(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message by {self.sender.username} in {self.group.name}"

class Invitation(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='invitations')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_invitations')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_invitations')
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected'),
        ],
        default='pending'
    )
    message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('project', 'recipient')

    def __str__(self):
        return f"Invitation for {self.recipient.username} to {self.project.title}"
