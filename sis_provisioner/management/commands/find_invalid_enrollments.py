# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models.enrollments import InvalidEnrollment


class Command(SISProvisionerCommand):
    help = "Find enrollments that are invalid."

    def handle(self, *args, **options):
        InvalidEnrollment.objects.add_enrollments()
        self.update_job()
