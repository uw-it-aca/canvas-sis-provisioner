from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.dao.astra import Admins


class Command(SISProvisionerCommand):
    help = "Loads admins for provisioning"

    def handle(self, *args, **options):
        Admins().load_all_admins()
        self.update_job()

