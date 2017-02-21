from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models import User


class Command(SISProvisionerCommand):
    args = "<priority>"
    help = "Imports csv files for users."

    def handle(self, *args, **options):
        if len(args):
            priority = int(args[0])

        User.objects.import_by_priority(priority)
        self.update_job()
