# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


import traceback

from sis_provisioner.builders.enrollments import InvalidEnrollmentBuilder
from sis_provisioner.exceptions import EmptyQueueException, MissingImportPathException
from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models.enrollment import InvalidEnrollment


class Command(SISProvisionerCommand):
    help = "Builds import files for invalid enrollments."

    def handle(self, *args, **options):
        priority = InvalidEnrollment.PRIORITY_DEFAULT
        try:
            imp = InvalidEnrollment.objects.queue_by_priority(priority)
        except EmptyQueueException:
            self.update_job()
            return

        try:
            imp.csv_path = InvalidEnrollmentBuilder(
                imp.queued_objects()).build()
        except Exception:
            imp.csv_errors = traceback.format_exc()

        imp.save()

        try:
            imp.import_csv()
        except MissingImportPathException:
            if not imp.csv_errors:
                imp.delete()

        self.update_job()
