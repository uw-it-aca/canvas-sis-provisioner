# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.conf import settings
from sis_provisioner.models.course import Course
from sis_provisioner.views.admin import RESTDispatch
from sis_provisioner.dao.canvas import (
    valid_canvas_id, get_account_by_id, get_course_by_id, get_course_by_sis_id)
from restclients_core.exceptions import DataFailureException
from logging import getLogger
from bs4 import BeautifulSoup
from urllib.request import urlopen
import re


logger = getLogger(__name__)


class CanvasCourseView(RESTDispatch):
    """ Performs query for Canvas course by sis_id.
        GET returns 200 with Canvas Course model
    """
    def get(self, request, *args, **kwargs):
        course_id = kwargs.get('course_id')
        params = {'state': ['all']}
        try:
            if valid_canvas_id(course_id):
                course = get_course_by_id(course_id, params)
            else:
                course = get_course_by_sis_id(course_id, params)

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
                'course_url': self.course_url(course.course_id),
                'workflow_state': course.workflow_state,
                'public_syllabus': course.public_syllabus,
                'syllabus_body': course.syllabus_body
            }

            try:
                model = Course.objects.get(canvas_course_id=course.course_id)
                course_rep.update(model.json_data(
                    include_sws_url=self.can_view_source_data(request)))
                if model.xlist_id:
                    course_rep['xlist_url'] = self.course_url(
                        'sis_course_id:{}'.format(model.xlist_id))
            except Course.DoesNotExist:
                pass

            return self.json_response(course_rep)
        except DataFailureException as ex:
            if ex.status == 404:
                return self.error_response(
                    404, "Course not found in Canvas: {}".format(ex.msg))
            return self.error_response(
                400, "Unable to retrieve course data: {}".format(ex.msg))

    def course_url(self, course_id):
        return '{host}/courses/{course_id}'.format(
            host=getattr(settings, 'RESTCLIENTS_CANVAS_HOST', ''),
            course_id=course_id)


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
                'account_url': "{host}/accounts/{account_id}".format(
                    host=getattr(settings, 'RESTCLIENTS_CANVAS_HOST', ''),
                    account_id=account.account_id)
            })

        except Exception as e:
            return self.error_response(
                400, "Unable to retrieve account: {}".format(e))


class CanvasStatus(RESTDispatch):
    def get(self, request, *args, **kwargs):
        status_url = 'http://status.instructure.com'
        try:
            page = urlopen(status_url)
            soup = BeautifulSoup(page, 'html.parser')
            components = []
            for x in soup.body.find_all(
                    'div', class_='component-inner-container'):
                name = x.find('span', class_='name').get_text(strip=True)
                status = x.find('span', class_='component-status').get_text(
                    strip=True)
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
