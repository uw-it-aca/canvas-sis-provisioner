from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models import Enrollment, PRIORITY_DEFAULT
from sis_provisioner.exceptions import (
    EmptyQueueException, MissingImportPathException)
from sis_provisioner.builders.enrollments import EnrollmentBuilder
import traceback


class Command(SISProvisionerCommand):
    help = "Builds import files for enrollments."

    def handle(self, *args, **options):
        priority = PRIORITY_DEFAULT

        try:
            imp = Enrollment.objects.queue_by_priority(priority)
        except EmptyQueueException as ex:
            self.update_job()
            return

        try:
            imp.csv_path = EnrollmentBuilder(imp.queued_objects()).build()
        except:
            imp.csv_errors = traceback.format_exc()

        imp.save()

        try:
            imp.import_csv()
        except MissingImportPathException as ex:
            if not imp.csv_errors:
                imp.delete()

        self.update_job()
