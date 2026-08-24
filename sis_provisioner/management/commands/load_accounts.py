# Copyright 2026 UWIT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from logging import getLogger

from restclients_core.exceptions import DataFailureException

from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models.account import Account


class Command(SISProvisionerCommand):
    help = "Load Canvas Accounts"

    def handle(self, *args, **options):
        try:
            Account.objects.add_all_accounts()
            self.update_job()
        except DataFailureException as err:
            getLogger(__name__).error(f'Account request failed: {err}')
