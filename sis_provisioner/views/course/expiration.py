# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from sis_provisioner.dao.course import (
    valid_academic_course_sis_id, valid_adhoc_course_sis_id,
    valid_canvas_course_id)
from sis_provisioner.models.course import Course
from sis_provisioner.views.admin import OpenRESTDispatch
from sis_provisioner.exceptions import CoursePolicyException
from django.utils.timezone import localtime
from logging import getLogger


logger = getLogger(__name__)


class CourseExpirationView(OpenRESTDispatch):
    """ Open API to return Course expiration_date at 
            /api/v1/course/<course id>/expiration.
        GET returns 200 with Course expiration date.
    """
    def get(self, request, *args, **kwargs):
        try:
            course_id = kwargs['course_id']
            course_ref = self._normalize(course_id)
            course = Course.objects.get(**course_ref)
            expiration_date = course.get_expiration_date()

            return self.json_response({
                "course": course_id,
                "expiration_date": localtime(
                    expiration_date).isoformat() if (
                        expiration_date is not None) else None})

        except CoursePolicyException as ex:
            return self.error_response(404, "{}".format(ex))
        except Course.DoesNotExist:
            return self.error_response(404, "Course not found")

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


