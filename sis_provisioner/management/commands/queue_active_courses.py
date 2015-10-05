from django.core.management.base import BaseCommand, CommandError
from sis_provisioner.loader import Loader


class Command(BaseCommand):
    help = "Re-queue active courses for the current term."

    def handle(self, *args, **options):
        loader = Loader()
        loader.queue_active_courses()
