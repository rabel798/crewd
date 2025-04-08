from django.db import models
from django.utils import timezone
from django.conf import settings

# List of technology choices for projects and user profiles
TECH_CHOICES = [
    'JavaScript', 'TypeScript', 'React', 'Vue.js', 'Angular', 'Node.js',
    'Python', 'Django', 'Flask', 'FastAPI', 'PHP', 'Laravel', 'Symfony',
    'Ruby', 'Ruby on Rails', 'Java', 'Spring Boot', 'C#', '.NET', 'Go',
    'Rust', 'Swift', 'Kotlin', 'Flutter', 'React Native', 'HTML', 'CSS',
    'SASS/SCSS', 'Tailwind CSS', 'Bootstrap', 'PostgreSQL', 'MySQL',
    'MongoDB', 'Redis', 'Firebase', 'AWS', 'Azure', 'Google Cloud',
    'Docker', 'Kubernetes', 'GraphQL', 'REST API', 'TensorFlow', 'PyTorch',
    'Machine Learning', 'Data Science', 'Blockchain', 'Solidity', 'Web3',
    'DevOps', 'CI/CD', 'Testing', 'Mobile Development', 'Game Development',
    'Unity', 'UI/UX Design', 'WordPress', 'Shopify', 'Linux', 'Git'
]

class Project(models.Model):
    """Project model for team leaders to create projects"""
    title = models.CharField(max_length=100)
    description = models.TextField()
    required_skills = models.TextField(blank=True, null=True)  # Comma-separated list of skills
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
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='projects'
    )
    created_at = models.DateTimeField(default=timezone.now)
    
    def get_required_skills_list(self):
        """Convert comma-separated skills to list"""
        if not self.required_skills:
            return []
        return [skill.strip() for skill in self.required_skills.split(',')]
    
    def __str__(self):
        return self.title

class ProjectMembership(models.Model):
    """Relationship between users and projects"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    role = models.CharField(
        max_length=20,
        choices=[
            ('admin', 'Admin'),
            ('member', 'Member'),
        ],
        default='member'
    )
    joined_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('user', 'project')
    
    def __str__(self):
        return f"{self.user.username} in {self.project.title}"

class Application(models.Model):
    """Application from a user to join a project"""
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected'),
        ],
        default='pending'
    )
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('project', 'applicant')
    
    def __str__(self):
        return f"{self.applicant.username}'s application to {self.project.title}"

class Invitation(models.Model):
    """Invitation from a team leader to a user to join a project"""
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='invitations'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_invitations'
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_invitations'
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected'),
        ],
        default='pending'
    )
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('project', 'recipient')
    
    def __str__(self):
        return f"Invitation to {self.recipient.username} for {self.project.title}"

class Group(models.Model):
    """Group chat for project members"""
    name = models.CharField(max_length=100)
    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name='group'
    )
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return self.name

class Message(models.Model):
    """Message in a group chat"""
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='messages',
        null=True,
        blank=True
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        group_name = self.group.name if self.group else "No Group"
        return f"Message from {self.sender.username} in {group_name}"
