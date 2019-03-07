from django.conf import settings
from sis_provisioner.models import Admin
from sis_provisioner.dao.canvas import (
    get_account_by_id, get_all_sub_accounts, get_admins, delete_admin)
from sis_provisioner.management.commands import SISProvisionerCommand
from logging import getLogger

logger = getLogger('sis_provisioner.dao.astra')


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

            for admin in get_admins(account_id):
                if not Admin.objects.verify_canvas_admin(admin, account_id):
                    if options.get('commit'):
                        delete_admin(
                            account_id, admin.user.user_id, admin.role)

                    logger.info((
                        'REMOVE UNAUTHORIZED ADMIN "{}", account: "{}", '
                        'role: "{}"').format(
                            admin.user.login_id, account_id, admin.role))

        self.update_job()
