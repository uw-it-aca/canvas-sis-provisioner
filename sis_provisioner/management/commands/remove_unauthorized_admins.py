from django.conf import settings
from sis_provisioner.models import Admin
from sis_provisioner.dao.canvas import (
    get_account, get_all_sub_accounts, get_admins, delete_admin)
from sis_provisioner.management.commands import SISProvisionerCommand
from logging import getLogger

logger = getLogger('astra')


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
        # Create a reverse lookup for Canvas roles
        self.canvas_role_mapping = dict((v, k) for (
            k, v in settings.ASTRA_ROLE_MAPPING.items()))

        root_account = get_account(options.get('root_account'))

        accounts = get_all_sub_accounts(root_account.account_id)
        accounts.append(root_account)

        for account in accounts:
            account_id = account.account_id

            for admin in get_admins(account_id):
                if not self.verify_admin(admin, account_id):
                    if options.get('commit'):
                        delete_admin(
                            account_id, admin.user.user_id, admin.role)

                    logger.info((
                        'REMOVE UNAUTHORIZED ADMIN "{}", account: "{}", '
                        'role: "{}"').format(
                            admin.user.login_id, account_id, admin.role))

        self.update_job()

    def verify_admin(self, admin, account_id):
        astra_role = self.canvas_role_mapping[admin.role]

        # Verify whether this role is ASTRA-defined
        if Admin.objects.has_role_in_account(
                admin.user.login_id, account_id, astra_role):
            return True

        # Otherwise, verify whether this is a valid ancillary role
        for parent_role, data in settings.ANCILLARY_CANVAS_ROLES.items():
            if 'root' == data['account']:
                ancillary_account_id = settings.RESTCLIENTS_CANVAS_ACCOUNT_ID
            else:
                ancillary_account_id = account_id

            if (ancillary_account_id == account_id and
                    data['canvas_role'] == admin.role):
                if Admin.objects.has_role(admin.user.login_id, parent_role):
                    return True

        return False
