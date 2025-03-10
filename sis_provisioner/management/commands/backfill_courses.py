# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.dao.canvas import (
    get_course_report_data, get_course_by_id, DataFailureException)
from sis_provisioner.dao.course import valid_academic_course_sis_id
from sis_provisioner.models.course import Course
from sis_provisioner.exceptions import CoursePolicyException
from logging import getLogger
import csv

logger = getLogger(__name__)


class Command(SISProvisionerCommand):
    help = "Insert courses from a Canvas course provisioning report file"

    def add_arguments(self, parser):
        parser.add_argument('-t', '--term-sis-id', action='store',
                            dest='term-sis-id', default=None,
                            help='Term SIS ID')
        parser.add_argument('-c', '--commit', action='store_true',
                            dest='commit', default=False,
                            help='Insert/update course models')

    def handle(self, *args, **options):
        term_sis_id = options.get('term-sis-id')
        commit = options.get('commit')
        logger.debug(f'Term: {term_sis_id}, Commit: {commit}')

        report_data = get_course_report_data(term_sis_id)
        header = report_data.pop(0)
        for row in csv.reader(report_data):
            if not len(row):
                continue

            canvas_course_id = row[0] or None
            course_sis_id = row[1] or None
            term_sis_id = row[8] or 'default'
            needs_save = False

            try:
                course = Course.objects.find_course(
                    canvas_course_id, course_sis_id)

                # Check for out-of-date properties in the model
                if course.canvas_course_id != canvas_course_id:
                    logger.info(f'Change canvas_course_id, '
                                f'Old: {course.canvas_course_id}, '
                                f'New: {canvas_course_id}')
                    course.canvas_course_id = canvas_course_id
                    needs_save = True

                if course.course_id != course_sis_id:
                    logger.info(f'Change course_sis_id, '
                                f'Old: {course.course_id}, '
                                f'New: {course_sis_id}')
                    course.course_id = course_sis_id
                    needs_save = True

                if course.term_id != term_sis_id:
                    logger.info(f'Change term_sis_id, '
                                f'Old: {course.term_id}, '
                                f'New: {term_sis_id}')
                    course.term_id = term_sis_id
                    needs_save = True

                if course.deleted_date is not None:
                    logger.info(f'Course is not deleted, '
                                f'{canvas_course_id}, {course_sis_id}')
                    course.deleted_date = None
                    needs_save = True

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

            if course.expiration_date is None:
                # API request to get course.created_at
                try:
                    canvas_course = get_course_by_id(canvas_course_id)
                    course.created_date = canvas_course.created_at
                    course.expiration_date = course.default_expiration_date
                    needs_save = True
                except DataFailureException as err:
                    logger.error(f'ERROR {canvas_course_id} '
                                 f'{course_sis_id}, {err}')
                    continue

            if needs_save and commit:
                course.save()
                logger.debug(f'BACKFILL Canvas ID: {course.canvas_course_id}, '
                             f'SIS ID: {course.course_id}, '
                             f'Term ID: {course.term_id}, '
                             f'Created: {course.created_date}, '
                             f'Expires: {course.expiration_date}')

        self.update_job()
