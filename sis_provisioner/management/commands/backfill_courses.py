# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import BaseCommand, CommandError
from sis_provisioner.dao.canvas import get_course_report_data, get_course_by_id
from sis_provisioner.models.course import Course
from logging import getLogger
import csv

logger = getLogger(__name__)


class Command(BaseCommand):
    help = "Insert courses from a Canvas course provisioning report file"

    def add_arguments(self, parser):
        parser.add_argument('-t', '--term-sis-id', help='Term SIS ID')
        parser.add_argument('-c', '--commit', action='store_true',
                            dest='commit', default=False,
                            help='Insert/update course models')

    def _log(self, action, course):
        logger.info(
            f'{action}, Canvas ID: {course.canvas_course_id}, '
            f'SIS ID: {course.course_id}, Created: {course.created_date}, '
            f'Expires: {course.expiration_date}')

    def handle(self, *args, **options):
        term_sis_id = options.get('term-sis-id')
        commit = options.get('commit')

        report_data = get_course_report_data(term_sis_id)
        header = report_data.pop(0)
        for row in csv.reader(report_data):
            if not len(row):
                continue

            canvas_course_id = row[0]
            course_sis_id = row[1]
            term_sis_id = row[8]
            course = None

            try:
                course = Course.objects.find_course(
                    canvas_course_id, course_sis_id)
                if course.expiration_date is None:
                    # Backfill sis course with new attrs
                    course.course_id = course_sis_id
                    course.canvas_course_id = canvas_course_id

                    # API request to get course.created_at
                    try:
                        canvas_course = get_course_by_id(canvas_course_id)
                        course.created_date = canvas_course.created_at
                        course.expiration_date = course.default_expiration_date
                    except DataFailureException as err:
                        self._log(f'ERROR {canvas_course_id} {course_sis_id}',
                                  course)
                        continue

                    if commit:
                        course.save()
                    else:
                        self._log('UPDATE', course)
                else:
                    if not commit:
                        self._log('SKIP', course)

            except Course.MultipleObjectsReturned:
                self._log(f'ERROR {canvas_course_id} {course_sis_id}', course)
                break
            except Course.DoesNotExist:
                course = Course(course_id=course_sis_id,
                                canvas_course_id=canvas_course_id,
                                course_type=Course.ADHOC_TYPE,
                                term_id=term_sis_id,
                                priority=Course.PRIORITY_NONE)

                # API request to get course.created_at
                try:
                    canvas_course = get_course_by_id(canvas_course_id)
                    course.created_date = canvas_course.created_at
                    course.expiration_date = course.default_expiration_date
                except DataFailureException as err:
                    self._log(f'ERROR {canvas_course_id} {course_sis_id}',
                              course)
                    continue

                    # Temporary logic for first round of expirations
                    if expiration_date.year == 2023:
                        expiration_date = expiration_date.replace(
                            month=12, day=18)

                    if commit:
                        course.save()
                    else:
                        self._log('INSERT', course)
