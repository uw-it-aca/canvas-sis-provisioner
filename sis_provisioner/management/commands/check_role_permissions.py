# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.conf import settings
from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models.admin import RoleCache
from logging import getLogger

logger = getLogger(__name__)


class Command(SISProvisionerCommand):
    help = 'Check accounts for role/permission changes'

    def handle(self, *args, **options):
        notify_accounts = []
        for account_id in getattr(settings, 'PERMISSIONS_CHECK_ACCOUNTS', []):
            try:
                if RoleCache.objects.check_roles_for_account(account_id):
                    notify_accounts.append(account_id)
            except Exception as ex:
                logger.info(
                    f'Role check failed for account {account_id}: {ex}')

        if len(notify_accounts):
            log_accounts = ', '.join(notify_accounts)
            logger.info(f'Permissions changed for accounts: {log_accounts}')

        self.update_job()
