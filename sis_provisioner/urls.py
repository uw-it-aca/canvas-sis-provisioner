from django.conf.urls import url, include
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
    url(r'^$', TemplateView.as_view(template_name='index.html')),
    url(r'^robots\.txt$', TemplateView.as_view(template_name='robots.txt',
                                               content_type='text/plain')),
    url(r'^$', ImportStatus, name='ImportStatus'),
    url(r'^users$', ManageUsers, name='ManageUsers'),
    url(r'^courses$', ManageCourses, name='ManageCourses'),
    url(r'^groups$', ManageGroups, name='ManageGroups'),
    url(r'^admins$', ManageAdmins, name='ManageAdmins'),
    url(r'^jobs$', ManageJobs, name='ManageJobs'),
    url(r'^external_tools$', ManageExternalTools,
        name='admin_manage_external_tools'),

    # API urls
    url(r'api/v1/canvas$', CanvasStatus().run)
    url(r'api/v1/canvas/course/(?P<sis_id>[a-zA-Z0-9 &-]+)$',
        CanvasCourseView().run),
    url(r'api/v1/canvas/account/(?P<account_id>[0-9]+)$',
        CanvasAccountView().run),
    url(r'api/v1/course/(?P<course_id>[a-zA-Z0-9\-_ &]+)$', CourseView().run),
    url(r'api/v1/courses/?$', CourseListView().run),
    url(r'api/v1/users/?$', UserView().run),
    url(r'api/v1/import/(?P<import_id>[0-9]+)?$', ImportView().run),
    url(r'api/v1/imports/?$', ImportListView().run),
    url(r'api/v1/groups/?$', GroupListView().run),
    url(r'api/v1/terms/?$', TermListView().run),
    url(r'api/v1/enrollments/?$', EnrollmentListView().run),
    url(r'api/v1/events/?(?P<begin>[0-9\-:TZtz]+)'
        r'?(?P<end>[0-9\-:TZtz]+)'
        r'?(?P<on>[0-9\-:TZtz]+)'
        r'?(?P<type>\w+)?$', EventListView().run),
    url(r'api/v1/admins/?$', AdminSearch().run),
    url(r'api/v1/accounts/?$', AccountSearch().run),
    url(r'api/v1/soc/?$', AccountSoC().run),
    url(r'api/v1/job/(?P<job_id>[0-9]+)?$', JobView().run),
    url(r'api/v1/jobs/?$', JobListView().run),
    url(r'api/v1/external_tool/(?P<canvas_id>[0-9]+)?$',
        ExternalToolView().run),
    url(r'api/v1/external_tools/?$', ExternalToolListView().run),
]
