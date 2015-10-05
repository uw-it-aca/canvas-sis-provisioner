from django.core.management.base import BaseCommand, CommandError
from sis_provisioner.loader import Loader


class Command(BaseCommand):
    help = "Loads users for provisioning"

    def handle(self, *args, **options):
        loader = Loader()
        loader.load_all_users()
