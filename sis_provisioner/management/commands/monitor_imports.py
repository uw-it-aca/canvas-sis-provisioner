# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.core.management.base import CommandError
from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models import Import
from logging import getLogger

logger = getLogger(__name__)


class Command(SISProvisionerCommand):
    help = "Monitors the status of sis imports to Canvas."

    def handle(self, *args, **options):
        try:
            for imp in Import.objects.find_by_requires_update():
                imp.update_import_status()
            self.update_job()
        except Exception as err:
            logger.error("{}".format(err))
            raise CommandError(err)
