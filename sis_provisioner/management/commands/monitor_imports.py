from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.pidfile import Pidfile, ProcessRunningException
from sis_provisioner.models import Import


class Command(SISProvisionerCommand):
    help = "Monitors the status of sis imports to Canvas."

    def handle(self, *args, **options):
        try:
            with Pidfile():
                for imp in Import.objects.filter(canvas_id__isnull=False):
                    imp.update_import_status()
                self.update_job()
        except ProcessRunningException as err:
            pass
