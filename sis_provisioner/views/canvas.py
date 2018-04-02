from django.conf import settings
from django.utils.decorators import method_decorator
from sis_provisioner.models import Course
from sis_provisioner.views import group_required
from sis_provisioner.views.rest_dispatch import RESTDispatch
from sis_provisioner.views.admin import can_view_source_data
from sis_provisioner.dao.canvas import (
    get_account_by_id, get_course_by_id, get_course_by_sis_id)
from logging import getLogger
from bs4 import BeautifulSoup
try:
    from urllib2 import urlopen  # python2.7
except ImportError:
    from urllib.request import urlopen
import re


logger = getLogger(__name__)


@method_decorator(group_required(settings.CANVAS_MANAGER_ADMIN_GROUP),
                  name='dispatch')
class CanvasCourseView(RESTDispatch):
    """ Performs query for Canvas course by sis_id.
        GET returns 200 with Canvas Course model
    """
    def get(self, request, *args, **kwargs):
        try:
            sis_id = kwargs.get('sis_id')
            canvas_id = re.match(r'^\d+$', sis_id)
            if canvas_id:
                course = get_course_by_id(canvas_id.group(0))
            else:
                course = get_course_by_sis_id(sis_id)

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
                    course_rep.update(
                        model.json_data(can_view_source_data(request)))
                except Course.DoesNotExist:
                    pass

            return self.json_response(course_rep)
        except Exception as e:
            return self.error_response(
                400, "Unable to retrieve course data: %s" % e)


@method_decorator(group_required(settings.CANVAS_MANAGER_ADMIN_GROUP),
                  name='dispatch')
class CanvasAccountView(RESTDispatch):
    """ Performs query for Canvas account by account_id
        GET returns 200 with Canvas Course model
    """
    def get(self, request, *args, **kwargs):
        try:
            account = get_account_by_id(kwargs.get('account_id'))
            return self.json_response({
                'account_id': account.account_id,
                'sis_account_id': account.sis_account_id,
                'name': account.name,
                'parent_account_id': account.parent_account_id,
                'root_account_id': account.root_account_id,
                'account_url': "%s/accounts/%s" % (
                    getattr(settings, 'RESTCLIENTS_CANVAS_HOST', ''),
                    account.account_id)
            })

        except Exception as e:
            return self.error_response(
                400, "Unable to retrieve account: %s" % e)


class CanvasStatus(RESTDispatch):
    def get(self, request, *args, **kwargs):
        status_url = 'http://status.instructure.com'
        try:
            page = urlopen(status_url)
            soup = BeautifulSoup(page, 'html.parser')
            components = []
            for x in soup.body.find_all(
                    'div', class_='component-inner-container'):
                name = x.find(
                    'span', class_='name').get_text(strip=True).encode('utf-8')
                status = x.find(
                    'span', class_='component-status').get_text(
                        strip=True).encode('utf-8')
                state = 'status-unknown'

                for c in x['class']:
                    if 'status-' in c:
                        state = c
                        break

                try:
                    name = re.sub(r'Support:', '', name)
                    name = re.sub(r'[^\/\w\s]', '', name)
                    name = name.strip()
                except (TypeError, AttributeError):
                    pass

                components.append({
                    'url': status_url,
                    'component': name,
                    'status': status,
                    'state': state
                })

        except Exception as err:
            components = [{
                'component': 'Canvas',
                'status': 'Unknown',
                'state': 'status-unknown',
                'url': status_url
            }, {
                'component': 'Status currently unavailable',
                'status': 'Unknown',
                'state': 'status-unknown',
                'url': status_url
            }]

        return self.json_response(components)
