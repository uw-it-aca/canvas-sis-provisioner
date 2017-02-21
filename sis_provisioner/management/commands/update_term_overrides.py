from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models import Term


class Command(SISProvisionerCommand):
    help = "Updates term override dates in Canvas."

    def handle(self, *args, **options):
        Term.objects.update_override_dates()
        self.update_job()
