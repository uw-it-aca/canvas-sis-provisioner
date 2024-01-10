# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models.course import Course
from sis_provisioner.exceptions import (
    EmptyQueueException, MissingImportPathException)
from sis_provisioner.builders.courses import CourseBuilder
import traceback


class Command(SISProvisionerCommand):
    help = "Builds csv files for courses."

    def add_arguments(self, parser):
        parser.add_argument(
            'priority', type=int, default=Course.PRIORITY_DEFAULT,
            choices=[Course.PRIORITY_DEFAULT,
                     Course.PRIORITY_HIGH,
                     Course.PRIORITY_IMMEDIATE],
            help='Import courses with priority <priority>')

    def handle(self, *args, **options):
        priority = options.get('priority')
        try:
            imp = Course.objects.queue_by_priority(priority)
        except EmptyQueueException as ex:
            self.update_job()
            return

        include_enrollment = (priority > Course.PRIORITY_DEFAULT)
        try:
            builder = CourseBuilder(imp.queued_objects())
            imp.csv_path = builder.build(include_enrollment=include_enrollment)
        except Exception:
            imp.csv_errors = traceback.format_exc()

        imp.save()

        try:
            imp.import_csv()
        except MissingImportPathException as ex:
            if not imp.csv_errors:
                imp.delete()

        self.update_job()
