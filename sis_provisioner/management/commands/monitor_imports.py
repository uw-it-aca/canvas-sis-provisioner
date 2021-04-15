# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models import Import


class Command(SISProvisionerCommand):
    help = "Monitors the status of sis imports to Canvas."

    def handle(self, *args, **options):
        for imp in Import.objects.find_by_requires_update():
            imp.update_import_status()
        self.update_job()
