from django.conf.urls import url, include
from django.views.generic.base import TemplateView
from sis_provisioner.views.admin import (
    ImportStatus, ManageUsers, ManageCourses, ManageGroups, ManageAdmins,
    ManageJobs, ManageExternalTools, user_login)
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
    url(r'^$', TemplateView.as_view(template_name='index.html')),
    url(r'^robots\.txt$', TemplateView.as_view(template_name='robots.txt',
                                               content_type='text/plain')),
    url(r'^login/?$', user_login),
    url(r'^admin/?$', ImportStatus, name='ImportStatus'),
    url(r'^admin/users$', ManageUsers, name='ManageUsers'),
    url(r'^admin/courses$', ManageCourses, name='ManageCourses'),
    url(r'^admin/groups$', ManageGroups, name='ManageGroups'),
    url(r'^admin/admins$', ManageAdmins, name='ManageAdmins'),
    url(r'^admin/jobs$', ManageJobs, name='ManageJobs'),
    url(r'^admin/external_tools$', ManageExternalTools,
        name='ManageExternalTools'),

    # API urls
    url(r'api/v1/canvas$', CanvasStatus.as_view()),
    url(r'api/v1/canvas/course/(?P<sis_id>[a-zA-Z0-9 &-]+)$',
        CanvasCourseView.as_view()),
    url(r'api/v1/canvas/account/(?P<account_id>[0-9]+)$',
        CanvasAccountView.as_view()),
    url(r'api/v1/course/(?P<course_id>[a-zA-Z0-9\-_ &]+)$',
        CourseView.as_view()),
    url(r'api/v1/courses/?$', CourseListView.as_view()),
    url(r'api/v1/users/?$', UserView.as_view()),
    url(r'api/v1/import/(?P<import_id>[0-9]+)?$', ImportView.as_view()),
    url(r'api/v1/imports/?$', ImportListView.as_view()),
    url(r'api/v1/groups/?$', GroupListView.as_view()),
    url(r'api/v1/terms/?$', TermListView.as_view()),
    url(r'api/v1/enrollments/?$', EnrollmentListView.as_view()),
    url(r'api/v1/events/?(?P<begin>[0-9\-:TZtz]+)'
        r'?(?P<end>[0-9\-:TZtz]+)'
        r'?(?P<on>[0-9\-:TZtz]+)'
        r'?(?P<type>\w+)?$', EventListView.as_view()),
    url(r'api/v1/admins/?$', AdminSearch.as_view()),
    url(r'api/v1/accounts/?$', AccountSearch.as_view()),
    url(r'api/v1/soc/?$', AccountSoC.as_view()),
    url(r'api/v1/job/(?P<job_id>[0-9]+)?$', JobView.as_view()),
    url(r'api/v1/jobs/?$', JobListView.as_view()),
    url(r'api/v1/external_tool/(?P<canvas_id>[0-9]+)?$',
        ExternalToolView.as_view()),
    url(r'api/v1/external_tools/?$', ExternalToolListView.as_view()),
]
