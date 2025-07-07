# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models.course import ExpiredCourse, Course, Import
from sis_provisioner.dao.canvas import delete_course
from sis_provisioner.exceptions import EmptyQueueException
from restclients_core.exceptions import DataFailureException
from datetime import datetime, timezone
from logging import getLogger

logger = getLogger(__name__)


class Command(SISProvisionerCommand):
    help = "Delete courses that have expired."

    def add_arguments(self, parser):
        parser.add_argument('-c', '--commit', action='store_true',
                            dest='commit', default=False,
                            help='Delete expired courses')

    def handle(self, *args, **options):
        commit = options.get('commit')
        try:
            imp = ExpiredCourse.objects.queue_by_expiration()
        except EmptyQueueException as ex:
            self.update_job()
            return

        for course in ExpiredCourse.objects.queued(queue_id):
            if commit:
                self.delete_canvas_course(course)
            else:
                logger.debug(f'DELETE (Commit=False) '
                             f'Canvas ID: {course.canvas_course_id}, '
                             f'SIS ID: {course.course_id}, '
                             f'Term ID: {course.term_id}, '
                             f'Created: {course.created_date}, '
                             f'Expires: {course.expiration_date}')

        imp.post_status = 200
        imp.canvas_progress = 100
        imp.delete()

        self.update_job()

    def delete_canvas_course(self, course):
        try:
            delete_course(course.canvas_course_id)
            course.deleted_date = datetime.now(timezone.utc)
            logger.info(f"DELETE course '{course.canvas_course_id}'")

        except DataFailureException as err:
            course.provisioned_error = True
            course.provisioned_status = str(err)
            logger.info(
                f"ERROR DELETE course '{course.canvas_course_id}': {err}")

        course.save()
