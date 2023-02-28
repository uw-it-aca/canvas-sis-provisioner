from .base_urls import *
from django.conf.urls import include
from django.urls import re_path

urlpatterns += [
    re_path(r'^', include('sis_provisioner.urls')),
    re_path(r'^blti/', include('blti.urls')),
    re_path(r'^restclients/', include('rc_django.urls')),
]
