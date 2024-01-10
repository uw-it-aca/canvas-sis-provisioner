# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models.group import Group


class Command(SISProvisionerCommand):
    help = "Prioritize groups for importing"

    def handle(self, *args, **options):
        Group.objects.update_priority_by_modified_date()
        self.update_job()
