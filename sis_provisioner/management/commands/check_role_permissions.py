from django.conf import settings
from sis_provisioner.management.commands import (
    SISProvisionerCommand, CommandError)
from sis_provisioner.models import RoleCache


class Command(SISProvisionerCommand):
    help = 'Check accounts for role/permission changes'

    def handle(self, *args, **options):
        notify_accounts = []
        for account_id in getattr(settings, 'PERMISSIONS_CHECK_ACCOUNTS', []):
            try:
                if RoleCache.objects.check_roles_for_account(account_id):
                    notify_accounts.append(account_id)
            except Exception as ex:
                raise CommandError(ex)

        self.update_job()

        if len(notify_accounts):
            raise CommandError(
                'Permissions changed for accounts: {}'.format(
                    ', '.join(notify_accounts)))