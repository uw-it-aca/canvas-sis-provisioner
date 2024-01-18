# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import BaseCommand, CommandError
from sis_provisioner.dao.canvas import (
    get_course_report_data, get_course_by_id, DataFailureException)
from sis_provisioner.dao.course import valid_academic_course_sis_id
from sis_provisioner.models.course import Course
from sis_provisioner.exceptions import CoursePolicyException
from logging import getLogger
import csv

logger = getLogger(__name__)


class Command(BaseCommand):
    help = "Insert courses from a Canvas course provisioning report file"

    def add_arguments(self, parser):
        parser.add_argument('-t', '--term-sis-id', action='store',
                            dest='term-sis-id', default=None,
                            help='Term SIS ID')
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
        logger.info(f'Term: {term_sis_id}, Commit: {commit}')

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
                        logger.info(f'ERROR {canvas_course_id} {course_sis_id}'
                                    f', {err}')
                        continue

                    if commit:
                        course.save()
                    else:
                        self._log('UPDATE', course)
                else:
                    if not commit:
                        self._log('SKIP', course)

            except Course.MultipleObjectsReturned:
                logger.info(f'ERROR Multiple courses for {canvas_course_id}, '
                            f'{course_sis_id}')
                break
            except Course.DoesNotExist:
                course = Course(course_id=course_sis_id,
                                canvas_course_id=canvas_course_id,
                                term_id=term_sis_id)

                try:
                    valid_academic_course_sis_id(course_sis_id)
                    course.course_type = Course.SDB_TYPE
                    course.priority = Course.PRIORITY_DEFAULT
                except CoursePolicyException:
                    course.course_type = Course.ADHOC_TYPE
                    course.priority = Course.PRIORITY_NONE

                # API request to get course.created_at
                try:
                    canvas_course = get_course_by_id(canvas_course_id)
                    course.created_date = canvas_course.created_at
                    course.expiration_date = course.default_expiration_date
                except DataFailureException as err:
                    logger.info(f'ERROR {canvas_course_id} {course_sis_id}'
                                f', {err}')
                    continue

                # Temporary logic for first round of expirations
                if course.expiration_date.year == 2023:
                    course.expiration_date = course.expiration_date.replace(
                        month=12, day=18)

                if commit:
                    course.save()
                else:
                    self._log('INSERT', course)
