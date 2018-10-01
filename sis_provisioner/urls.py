from django.urls import re_path
from django.views.generic.base import TemplateView
from sis_provisioner.views.admin import (
    ImportStatus, ManageUsers, ManageCourses, ManageGroups, ManageAdmins,
    ManageJobs, ManageExternalTools)
from sis_provisioner.views.course import CourseView, CourseListView
from sis_provisioner.views.enrollment import EnrollmentListView
from sis_provisioner.views.group import GroupListView
from sis_provisioner.views.user import UserView
from sis_provisioner.views.terms import TermListView
from sis_provisioner.views.canvas import (
    CanvasCourseView, CanvasAccountView, CanvasStatus)
from sis_provisioner.views.imports import ImportView, ImportListView
from sis_provisioner.views.jobs import JobView, JobListView
from sis_provisioner.views.events import EventListView
from sis_provisioner.views.astra import AdminSearch, AccountSearch, AccountSoC
from sis_provisioner.views.external_tools import (
    ExternalToolView, ExternalToolListView)


urlpatterns = [
    re_path(r'^$', TemplateView.as_view(template_name='index.html')),
    re_path(r'^robots\.txt$', TemplateView.as_view(
        template_name='robots.txt', content_type='text/plain')),
    re_path(r'^admin/?$', ImportStatus, name='ImportStatus'),
    re_path(r'^admin/users$', ManageUsers, name='ManageUsers'),
    re_path(r'^admin/courses$', ManageCourses, name='ManageCourses'),
    re_path(r'^admin/groups$', ManageGroups, name='ManageGroups'),
    re_path(r'^admin/admins$', ManageAdmins, name='ManageAdmins'),
    re_path(r'^admin/jobs$', ManageJobs, name='ManageJobs'),
    re_path(r'^admin/external_tools$', ManageExternalTools,
            name='ManageExternalTools'),

    # API urls
    re_path(r'api/v1/canvas$', CanvasStatus.as_view()),
    re_path(r'api/v1/canvas/course/(?P<sis_id>[a-zA-Z0-9 &-]+)$',
            CanvasCourseView.as_view()),
    re_path(r'api/v1/canvas/account/(?P<account_id>[0-9]+)$',
            CanvasAccountView.as_view()),
    re_path(r'api/v1/course/(?P<course_id>[a-zA-Z0-9\-_ &]+)$',
            CourseView.as_view()),
    re_path(r'api/v1/courses/?$', CourseListView.as_view()),
    re_path(r'api/v1/users/?$', UserView.as_view()),
    re_path(r'api/v1/import/(?P<import_id>[0-9]+)?$', ImportView.as_view()),
    re_path(r'api/v1/imports/?$', ImportListView.as_view()),
    re_path(r'api/v1/groups/?$', GroupListView.as_view()),
    re_path(r'api/v1/terms/?$', TermListView.as_view()),
    re_path(r'api/v1/enrollments/?$', EnrollmentListView.as_view()),
    re_path(r'api/v1/events/?(?P<begin>[0-9\-:TZtz]+)'
            r'?(?P<end>[0-9\-:TZtz]+)'
            r'?(?P<on>[0-9\-:TZtz]+)'
            r'?(?P<type>\w+)?$', EventListView.as_view()),
    re_path(r'api/v1/admins/?$', AdminSearch.as_view()),
    re_path(r'api/v1/accounts/?$', AccountSearch.as_view()),
    re_path(r'api/v1/soc/?$', AccountSoC.as_view()),
    re_path(r'api/v1/job/(?P<job_id>[0-9]+)?$', JobView.as_view()),
    re_path(r'api/v1/jobs/?$', JobListView.as_view()),
    re_path(r'api/v1/external_tool/(?P<canvas_id>[0-9]+)?$',
            ExternalToolView.as_view()),
    re_path(r'api/v1/external_tools/?$', ExternalToolListView.as_view()),
]
