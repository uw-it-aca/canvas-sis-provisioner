from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.loader import Loader


class Command(SISProvisionerCommand):
    help = "Loads courses for provisioning."

    def handle(self, *args, **options):
        loader = Loader()
        loader.load_all_courses()
        self.update_job()
