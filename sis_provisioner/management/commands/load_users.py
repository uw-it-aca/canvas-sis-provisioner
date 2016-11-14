from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models import User


class Command(SISProvisionerCommand):
    help = "Loads users for provisioning, from pre-defined groups"

    def handle(self, *args, **options):
        User.objects.add_all_users()
        self.update_job()
