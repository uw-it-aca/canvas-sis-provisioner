from logging import getLogger
from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models import Account
from restclients_core.exceptions import DataFailureException


class Command(SISProvisionerCommand):
    help = "Load Canvas Accounts"

    def handle(self, *args, **options):
        try:
            Account.objects.add_all_accounts()
            self.update_job()
        except DataFailureException as err:
            getLogger(__name__).error('Account request failed: {}'.format(err))
