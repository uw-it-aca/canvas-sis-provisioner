import json
from django.utils.log import getLogger
from django.conf import settings
from sis_provisioner.models import Course
from sis_provisioner.views.rest_dispatch import RESTDispatch
from restclients.canvas.courses import Courses
from restclients.models.canvas import CanvasAccount
from restclients.canvas.accounts import Accounts
from canvas_admin.views import can_view_source_data
import re


class CanvasCourseView(RESTDispatch):
    """ Performs query for Canvas course by sis_id.
        GET returns 200 with Canvas Course model
    """
    def __init__(self):
        self._log = getLogger(__name__)

    def GET(self, request, **kwargs):
        try:
            sis_id = kwargs.get('sis_id')
            canvas_id = re.match(r'^\d+$', sis_id)
            if canvas_id:
                course = Courses().get_course(canvas_id.group(0))
            else:
                course = Courses().get_course_by_sis_id(sis_id)

            course_rep = {
                'course_id': course.course_id,
                'sis_course_id': course.sis_course_id,
                'sws_course_id': course.sws_course_id(),
                'account_id': course.account_id,
                'term': {
                    'term_id': course.term.term_id,
                    'sis_term_id': course.term.sis_term_id,
                    'name': course.term.name
                },
                'course_name': course.name,
                'course_url': "%s/courses/%s" % (
                    getattr(settings, 'RESTCLIENTS_CANVAS_HOST', ''),
                    course.course_id),
                'workflow_state': course.workflow_state,
                'public_syllabus': course.public_syllabus,
                'syllabus_body': course.syllabus_body
            }

            if course.sis_course_id is not None:
                try:
                    model = Course.objects.get(course_id=course.sis_course_id)
                    course_rep.update(model.json_data(can_view_source_data()))
                except Course.DoesNotExist:
                    pass

            return self.json_response(json.dumps(course_rep))
        except Exception as e:
            return self.json_response(
                '{"error": "Unable to retrieve course data: %s"' % (e) + ' }',
                status=400)


class CanvasAccountView(RESTDispatch):
    """ Performs query for Canvas account by account_id
        GET returns 200 with Canvas Course model
    """
    def __init__(self):
        self._log = getLogger(__name__)

    def GET(self, request, **kwargs):
        try:
            account = Accounts().get_account(kwargs.get('account_id'))
            return self.json_response(json.dumps({
                'account_id': account.account_id,
                'sis_account_id': account.sis_account_id,
                'name': account.name,
                'parent_account_id': account.parent_account_id,
                'root_account_id': account.root_account_id,
                'account_url': "%s/accounts/%s" % (
                    getattr(settings, 'RESTCLIENTS_CANVAS_HOST', ''),
                    account.account_id)
            }))

        except Exception as e:
            return self.json_response(
                '{"error": "Unable to retrieve account: %s"' % (e) + ' }',
                status=400)
