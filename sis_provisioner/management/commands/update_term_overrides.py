# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models.term import Term


class Command(SISProvisionerCommand):
    help = "Updates term override dates in Canvas."

    def handle(self, *args, **options):
        Term.objects.update_override_dates()
        self.update_job()
