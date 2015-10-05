from django.core.management.base import BaseCommand, CommandError
from sis_provisioner.models import Import
from sis_provisioner.csv_builder import CSVBuilder
import traceback


class Command(BaseCommand):
    help = "Builds csv files for Canvas accounts."

    def handle(self, *args, **options):
        imp = Import(csv_type="account")
        try:
            imp.csv_path = CSVBuilder().generate_account_csv()
        except:
            imp.csv_errors = traceback.format_exc()

        imp.save()

        if imp.csv_path:
            imp.import_csv()
