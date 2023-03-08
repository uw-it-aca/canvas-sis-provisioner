# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from sis_provisioner.dao.course import (
    valid_academic_course_sis_id, valid_adhoc_course_sis_id,
    valid_canvas_course_id)
from sis_provisioner.models.course import Course
from sis_provisioner.models.user import User
from sis_provisioner.views.admin import OpenRESTDispatch, AdminView
from sis_provisioner.exceptions import CoursePolicyException
from uw_saml.utils import get_user
from django.utils.timezone import utc, localtime
from django.conf import settings
from datetime import datetime
from logging import getLogger
import json

logger = getLogger(__name__)


class CourseExpirationView(OpenRESTDispatch):
    """ API to return Course expiration_date at
          /api/v1/course/<course id>/expiration.
        Public GET returns 200 with Course expiration date.
        Authenticated PUT updates expiration date.
        Authenticated DELETE resets expiration date.
    """
    def get(self, request, *args, **kwargs):
        try:
            course_id = kwargs['course_id']
            course_ref = self._normalize(course_id)
            course = Course.objects.get(**course_ref)
            expiration_date = course.expiration_date if (
                course.expiration_date) else course.default_expiration_date

            return self.json_response({
                "course_id": course_id,
                "expiration_date": localtime(
                    expiration_date).isoformat() if (
                        expiration_date is not None) else None})

        except CoursePolicyException as ex:
            return self.error_response(404, "{}".format(ex))
        except Course.DoesNotExist:
            return self.error_response(404, "Course not found")

    def put(self, request, *args, **kwargs):
        login_name = get_user(request)
        if not (login_name and
                AdminView.can_manage_course_expirations(request)):
            return self.error_response(401, "Not permitted")

        try:
            course_id = kwargs['course_id']
            course_ref = self._normalize(course_id)
            course = Course.objects.get(**course_ref)
            if course.primary_id:
                raise CoursePolicyException('Section expiration not permitted')

            user = User.objects.get(net_id=login_name)

        except CoursePolicyException as ex:
            return self.error_response(400, "{}".format(ex))
        except Course.DoesNotExist:
            return self.error_response(404, "Course not found")
        except User.DoesNotExist:
            return self.error_response(404, "User not found")

        try:
            put_data = json.loads(request.body)
        except Exception as ex:
            return self.error_response(400, "Unable to parse JSON: {}".format(
                ex))

        exp = course.default_expiration_date
        course.expiration_date = exp.replace(year=exp.year + 1)
        course.expiration_exc_granted_date = datetime.utcnow().replace(
            tzinfo=utc)
        course.expiration_exc_granted_by = user
        course.expiration_exc_desc = put_data.get('expiration_exc_desc')
        course.save()

        logger.info('Course {} exception granted by {}'.format(
            course_id, login_name))

        return self.json_response(course.json_data())

    def delete(self, request, *args, **kwargs):
        login_name = get_user(request)
        if not (login_name and
                AdminView.can_manage_course_expirations(request)):
            return self.error_response(401, "Not permitted")

        try:
            course_id = kwargs['course_id']
            course_ref = self._normalize(course_id)
            course = Course.objects.get(**course_ref)
            if course.primary_id:
                raise CoursePolicyException('Section expiration not permitted')

        except CoursePolicyException as ex:
            return self.error_response(400, "{}".format(ex))
        except Course.DoesNotExist:
            return self.error_response(404, "Course not found")

        course.expiration_date = course.default_expiration_date
        course.expiration_exc_granted_date = None
        course.expiration_exc_granted_by = None
        course.expiration_exc_desc = None
        course.save()

        logger.info('Course {} exception cleared by {}'.format(
            course_id, login_name))

        return self.json_response(course.json_data())

    def _normalize(self, course):
        """ normalize course id case
        """
        course_key = 'course_id'
        course = course.strip()
        try:
            valid_academic_course_sis_id(course)
        except CoursePolicyException:
            try:
                valid_adhoc_course_sis_id(course)
                course = course.lower()
            except CoursePolicyException:
                valid_canvas_course_id(course)
                course_key = 'canvas_course_id'

        return {course_key: course}
