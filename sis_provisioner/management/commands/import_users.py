from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models import User, PRIORITY_DEFAULT, PRIORITY_IMMEDIATE
from sis_provisioner.exceptions import (
    EmptyQueueException, MissingImportPathException)
from sis_provisioner.builders.users import UserBuilder
import traceback


class Command(SISProvisionerCommand):
    help = "Imports csv files for users."

    def add_arguments(self, parser):
        parser.add_argument(
            'priority', type=int, default=PRIORITY_DEFAULT,
            choices=[PRIORITY_DEFAULT, PRIORITY_HIGH, PRIORITY_IMMEDIATE],
            help='Import users with priority <priority>')

    def handle(self, *args, **options):
        priority = options.get('priority')
        try:
            imp = User.objects.queue_by_priority(priority)
        except EmptyQueueException:
            self.update_job()
            return

        try:
            imp.csv_path = UserBuilder(imp.queued_objects()).build()
        except:
            imp.csv_errors = traceback.format_exc()

        imp.save()

        try:
            imp.import_csv()
        except MissingImportPathException as ex:
            if not imp.csv_errors:
                imp.delete()

        self.update_job()
