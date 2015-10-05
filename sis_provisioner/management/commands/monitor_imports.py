from django.core.management.base import BaseCommand, CommandError
from sis_provisioner.pidfile import Pidfile, ProcessRunningException
from sis_provisioner.models import Import


class Command(BaseCommand):
    help = "Monitors the status of sis imports to Canvas."

    def handle(self, *args, **options):
        try:
            with Pidfile():
                for imp in Import.objects.filter(canvas_id__isnull=False):
                    imp.update_import_status()
        except ProcessRunningException as err:
            pass
