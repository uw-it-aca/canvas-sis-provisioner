from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.loader import Loader


class Command(SISProvisionerCommand):
    help = "Re-queue active courses for the current term."

    def handle(self, *args, **options):
        Loader().queue_active_courses()
        self.update_job()
