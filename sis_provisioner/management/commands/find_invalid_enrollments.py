# Copyright 2026 UWIT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from logging import getLogger

from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models.enrollment import InvalidEnrollment

logger = getLogger(__name__)


class Command(SISProvisionerCommand):
    help = "Find enrollments that are invalid."

    def handle(self, *args, **options):
        try:
            InvalidEnrollment.objects.add_enrollments()
        except Exception as err:
            logger.error(f"{err}")

        self.update_job()
