"""
URL configuration for foodie_robot project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from api.urls import api
from api.admin.template_campaign import TemplateCampaignAdminSite

# Extend admin site with custom URLs
_original_get_urls = admin.site.get_urls

def custom_get_urls():
    custom_urls = [
        path(
            'api/send-template/',
            admin.site.admin_view(TemplateCampaignAdminSite.send_template_view),
            name='send_template'
        ),
        path(
            'api/send-template/preview/',
            admin.site.admin_view(TemplateCampaignAdminSite.preview_users_api),
            name='send_template_preview'
        ),
    ]
    return custom_urls + _original_get_urls()

admin.site.get_urls = custom_get_urls

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", api.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
