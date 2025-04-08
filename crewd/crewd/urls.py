"""
URL Configuration for the Crewd project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from projects.views import IndexView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', IndexView.as_view(), name='index'),
    path('projects/', include('projects.urls', namespace='projects')),
    path('accounts/', include('accounts.urls', namespace='accounts')),
]

# Add media URL patterns if in debug mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
