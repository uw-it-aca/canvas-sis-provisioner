from .base_urls import *
from django.urls import include, re_path
from django.views.i18n import JavaScriptCatalog

urlpatterns += [
    re_path(r'^', include('sis_provisioner.urls')),
    re_path(r'^saml/', include('uw_saml.urls')),
    re_path(r'^blti/', include('blti.urls')),
    re_path(r'^grading_standard/', include('grading_standard.urls')),
    re_path(r'^groups/', include('groups.urls')),
    re_path(r'^roster/', include('course_roster.urls')),
    re_path(r'^users/', include('canvas_users.urls')),
    re_path(r'^libguide/', include('libguide.urls')),
    re_path(r'^feedback/', include('anonymous_feedback.urls')),
    re_path(r'^restclients/', include('rc_django.urls')),
    re_path(r'^jsi18n/$', JavaScriptCatalog.as_view(
            packages=['grade_conversion_calculator', 'grading_standard']),
            name='javascript-catalog'),
]
