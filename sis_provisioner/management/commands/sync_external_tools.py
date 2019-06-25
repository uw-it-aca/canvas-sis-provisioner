from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models.external_tools import ExternalTool
from sis_provisioner.pidfile import Pidfile, ProcessRunningException


class Command(SISProvisionerCommand):
    help = "Sync LTI Manager app with actual external tools in Canvas"

    def handle(self, *args, **options):
        try:
            with Pidfile():
                ExternalTool.objects.import_all()
                self.update_job()
        except ProcessRunningException:
            pass
