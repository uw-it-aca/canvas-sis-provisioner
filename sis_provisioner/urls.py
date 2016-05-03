from django.conf.urls import patterns, url, include
from django.views.generic.base import TemplateView
from sis_provisioner.views.course import CourseView, CourseListView
from sis_provisioner.views.enrollment import EnrollmentListView
from sis_provisioner.views.group import GroupListView
from sis_provisioner.views.user import UserView
from sis_provisioner.views.canvas import CanvasCourseView, CanvasAccountView
from sis_provisioner.views.imports import ImportView, ImportListView
from sis_provisioner.views.jobs import JobView, JobListView
from astra.views import AdminSearch, AccountSearch, AccountSoC
from events.views import EventListView


urlpatterns = patterns(
    '',
    url(r'^$', TemplateView.as_view(template_name='index.html')),
    url(r'^robots\.txt$', TemplateView.as_view(template_name='robots.txt',
                                               content_type='text/plain')),
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
)
