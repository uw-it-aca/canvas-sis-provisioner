from .base_urls import *
from django.urls import include, re_path


urlpatterns += [
    re_path(r'^', include('sis_provisioner.urls')),
    re_path(r'^blti/', include('blti.urls')),
    re_path(r'^restclients/', include('rc_django.urls')),
]
