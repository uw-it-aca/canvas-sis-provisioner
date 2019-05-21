from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models.external_tools import ExternalTool


class Command(SISProvisionerCommand):
    help = "Sync LTI Manager app with actual external tools in Canvas"

    def handle(self, *args, **options):
        ExternalTool.objects.update_all()
        self.update_job()
