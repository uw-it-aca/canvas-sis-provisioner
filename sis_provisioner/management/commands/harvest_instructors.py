# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import BaseCommand
from sis_provisioner.models.course import Course
from restclients_core.exceptions import DataFailureException
from uw_canvas.enrollments import Enrollments
from uw_gws import GWS
from logging import getLogger
import csv
import sys


logger = getLogger(__name__)


DEFAULT_BATCH_SIZE = 500
EMPLOYEE_GROUP = 'uw_employee'


class Command(BaseCommand):
    help = "List teacher of courses expiring in given year"
    enrollments = Enrollments()
    gws = GWS()

    def add_arguments(self, parser):
        parser.add_argument(
            'expiration_year', type=int, help='Expiration year for harvest')
        parser.add_argument(
            '--start', nargs='?', type=int, const=0,
            help='index of first id sorted list of course to evaluate')
        parser.add_argument(
            '--end', nargs='?', type=int, const=-1,
            help='index of last id sorted list of course to evaluate')

    def handle(self, *args, **options):
        # fetch course queryset
        course_filter = {
            'expiration_date__year': options['expiration_year']
        }

        courses = Course.objects.filter(**course_filter).order_by('id')

        # setup course output range
        total = courses.count()
        end = total if (options['end'] is None) else (
            max(min(options['end'], total), 0)) if (
                options['end'] >= 0) else max(total + options['end'], 0)
        start = 0 if (options['start'] is None) else (
            min(max(0, options['start']), end)) if (
                options['start'] >= 0) else max(end + options['start'], 0)

        # dump currently employed teachers for each course
        seen = set()
        writer = csv.writer(sys.stdout, dialect='unix')
        for qs in self.batch(courses, start, end):
            for course in qs:
                for teacher in self._get_teachers(course):
                    if teacher.login_id not in seen:
                        seen.add(teacher.login_id)
                        if self._is_employee(teacher.login_id):
                            writer.writerow([teacher.name,
                                             "{}@uw.edu".format(
                                                 teacher.login_id)])
                        else:
                            print("Separated Teacher: {}".format(
                                teacher.login_id), file=sys.stderr)

    def _is_employee(self, login_id):
        try:
            return self.gws.is_effective_member(EMPLOYEE_GROUP, login_id)
        except Exception as ex:
            print("GWS exception: {}".format(ex), file=sys.stderr)

    def _get_teachers(self, course):
        try:
            return self.enrollments.get_enrollments_for_course(
                course.canvas_course_id, {'type': 'TeacherEnrollment'})
        except DataFailureException as ex:
            if ex.status == 404:
                print('enrollment: unknown course {} ({})'.format(
                    course.course_id, course.canvas_course_id),
                      file=sys.stderr)
            else:
                print('enrollment: exception referencing {} ({}): {}'.format(
                    course.course_id, ex), file=sys.stderr)

        return []

    def batch(self, qs, begin, end, batch_size=DEFAULT_BATCH_SIZE):
        for first in range(begin, end, batch_size):
            last = min(first + batch_size, end)
            yield qs[first:last]
