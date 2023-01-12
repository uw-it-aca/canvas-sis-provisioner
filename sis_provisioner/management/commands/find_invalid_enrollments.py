# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models.enrollment import InvalidEnrollment
from logging import getLogger

logger = getLogger(__name__)


class Command(SISProvisionerCommand):
    help = "Find enrollments that are invalid."

    def handle(self, *args, **options):
        try:
            InvalidEnrollment.objects.add_enrollments()
        except Exception as err:
            logger.error("{}".format(err))

        self.update_job()
