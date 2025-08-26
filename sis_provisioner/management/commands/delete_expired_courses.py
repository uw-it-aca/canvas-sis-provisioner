# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models.course import ExpiredCourse, Import
from sis_provisioner.exceptions import EmptyQueueException
from logging import getLogger

logger = getLogger(__name__)


class Command(SISProvisionerCommand):
    help = 'Delete courses that have expired.'

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

        for course in imp.queued_objects():
            if commit:
                course.archive_canvas_course()

            logger.info(f'ARCHIVE course (Commit={commit}), '
                        f'Canvas ID: {course.canvas_course_id}, '
                        f'SIS ID: {course.course_id}, '
                        f'Created: {course.created_date}, '
                        f'Expired: {course.expiration_date}')

        imp.post_status = 200
        imp.canvas_progress = 100
        imp.delete()

        self.update_job()
