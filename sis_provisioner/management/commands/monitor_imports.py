from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.pidfile import Pidfile, ProcessRunningException
from sis_provisioner.models import Import


class Command(SISProvisionerCommand):
    help = "Monitors the status of sis imports to Canvas."

    def process(self, *args, **options):
        try:
            with Pidfile():
                for imp in Import.objects.find_by_requires_update():
                    imp.update_import_status()
                self.update_job()
        except ProcessRunningException as err:
            pass
