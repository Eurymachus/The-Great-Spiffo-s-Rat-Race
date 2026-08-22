"""
URL configuration for config project.

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
from django.shortcuts import redirect
from django.urls import include, path

from . import health
from .media import persistent_media
from .staging import robots_txt


def admin_home(request):
    if request.user.is_authenticated and request.user.has_perm(
        "registry.view_participant"
    ):
        return redirect("admin:registry_participant_changelist")
    if request.user.is_authenticated and request.user.has_perm(
        "branding.view_sitebranding"
    ):
        return redirect("admin:branding_sitebranding_change", object_id="1")
    if request.user.is_authenticated and request.user.has_perm(
        "zomboid_catalogue.view_catalogueentry"
    ):
        return redirect("admin:zomboid_catalogue_catalogueentry_changelist")
    return redirect("admin:index")

urlpatterns = [
    path("robots.txt", robots_txt, name="robots-txt"),
    path("health/live/", health.liveness, name="health-live"),
    path("health/ready/", health.readiness, name="health-ready"),
    path(
        'admin/',
        admin_home,
        name='admin-home',
    ),
    path('admin/', admin.site.urls),
    path("media/<path:media_path>", persistent_media, name="persistent-media"),
    path('', include('registry.urls')),
]
