from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models import Enrollment, EmptyQueueException,\
    MissingImportPathException, PRIORITY_DEFAULT
from sis_provisioner.csv_builder import CSVBuilder
import traceback


class Command(SISProvisionerCommand):
    help = "Builds csv files for enrollments."

    def handle(self, *args, **options):
        priority = PRIORITY_DEFAULT

        try:
            imp = Enrollment.objects.queue_by_priority(priority)
        except EmptyQueueException as ex:
            self.update_job()
            return

        try:
            imp.csv_path = CSVBuilder().generate_csv_for_enrollment_events(
                imp.queued_objects())
        except:
            imp.csv_errors = traceback.format_exc()

        imp.save()

        try:
            imp.import_csv()
        except MissingImportPathException as ex:
            if not imp.csv_errors:
                imp.delete()

        self.update_job()
