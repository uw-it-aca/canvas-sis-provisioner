# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.conf import settings
from restclients_core.exceptions import DataFailureException
from sis_provisioner.models.admin import Admin
from sis_provisioner.dao.canvas import (
    get_account_by_id, get_all_sub_accounts, get_admins, delete_admin)
from sis_provisioner.management.commands import SISProvisionerCommand
from logging import getLogger

logger = getLogger(__name__)


class Command(SISProvisionerCommand):
    help = 'Delete Canvas admins not found in ASTRA'

    def add_arguments(self, parser):
        parser.add_argument(
            '-r', '--root-account', action='store', dest='root_account',
            default=settings.RESTCLIENTS_CANVAS_ACCOUNT_ID,
            help='Check sub-accounts at and below root account')
        parser.add_argument(
            '-c', '--commit', action='store_true', dest='commit',
            default=False,
            help='Delete Canvas admins not found in ASTRA')

    def handle(self, *args, **options):
        root_account = get_account_by_id(options.get('root_account'))

        accounts = get_all_sub_accounts(root_account.account_id)
        accounts.append(root_account)

        for account in accounts:
            account_id = account.account_id

            try:
                admins = get_admins(account_id)
            except DataFailureException as ex:
                logger.error(
                    f'get_admins failed for account "{account_id}": {ex}')
                continue

            for admin in admins:
                if not Admin.objects.verify_canvas_admin(admin, account_id):
                    if options.get('commit'):
                        delete_admin(
                            account_id, admin.user.user_id, admin.role)

                    logger.info(
                        f'REMOVE UNAUTHORIZED ADMIN "{admin.user.login_id}", '
                        f'account: "{account_id}", role: "{admin.role}"')

        self.update_job()
