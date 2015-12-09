#from django.core.management.base import BaseCommand, CommandError
from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.loader import Loader


class Command(SISProvisionerCommand):
    help = "Loads users for provisioning"

    def handle(self, *args, **options):
        loader = Loader()
        loader.load_all_users()
