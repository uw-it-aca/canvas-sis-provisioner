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
    help = "Confirm course deletions from a Canvas course provisioning report"

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
        logger.info(f'Term: {term_sis_id}, Commit: {commit}')

        report_data = get_course_report_data(term_sis_id)
        header = report_data.pop(0)
        for row in csv.reader(report_data):
            if not len(row):
                continue

            canvas_course_id = row[0] or None
            course_sis_id = row[1] or None

            try:
                course = Course.objects.find_course(
                    canvas_course_id, course_sis_id)

                if (course.expiration_date is not None and
                        course.expiration_date.year == 2023 and
                        course.expiration_date.month == 12 and
                        course.deleted_date is not None):
                    if commit:
                        course.deleted_date = None
                        course.save()
                    logger.info(f'CONFIRM {canvas_course_id} '
                                f'{course_sis_id}, {err}')

            except Course.MultipleObjectsReturned:
                logger.info(f'ERROR Multiple courses for {canvas_course_id}, '
                            f'{course_sis_id}')
                continue

            except Course.DoesNotExist:
                pass
