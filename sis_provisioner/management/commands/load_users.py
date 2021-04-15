# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models.user import User


class Command(SISProvisionerCommand):
    help = "Loads users for provisioning, from pre-defined groups"

    def handle(self, *args, **options):
        User.objects.add_all_users()
        self.update_job()
