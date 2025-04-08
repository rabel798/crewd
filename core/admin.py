from django.contrib import admin
from .models import UserProfile, Project, Application

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'created_at')
    search_fields = ('user__username', 'user__email')
    list_filter = ('role', 'created_at')

class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'creator', 'team_size', 'status', 'created_at')
    search_fields = ('title', 'description', 'creator__username')
    list_filter = ('status', 'created_at')

class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('applicant', 'project', 'status', 'created_at')
    search_fields = ('applicant__username', 'project__title')
    list_filter = ('status', 'created_at')

admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(Application, ApplicationAdmin)
