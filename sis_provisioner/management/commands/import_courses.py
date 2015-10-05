from django.core.management.base import BaseCommand, CommandError
from sis_provisioner.models import Course, EmptyQueueException,\
    MissingImportPathException, PRIORITY_DEFAULT, PRIORITY_IMMEDIATE
from sis_provisioner.csv_builder import CSVBuilder
import traceback


class Command(BaseCommand):
    args = "<priority>"
    help = "Builds csv files for courses."

    def handle(self, *args, **options):
        priority = PRIORITY_DEFAULT

        if len(args):
            priority = int(args[0])
            if priority < PRIORITY_DEFAULT or priority > PRIORITY_IMMEDIATE:
                raise CommandError('Invalid priority: %s' % priority)

        try:
            imp = Course.objects.queue_by_priority(priority)
        except EmptyQueueException as ex:
            return

        include_enrollment = True if (priority > PRIORITY_DEFAULT) else False
        try:
            imp.csv_path = CSVBuilder().generate_course_csv(
                imp.queued_objects(), include_enrollment)
        except:
            imp.csv_errors = traceback.format_exc()

        imp.save()

        try:
            imp.import_csv()
        except MissingImportPathException as ex:
            if not imp.csv_errors:
                imp.delete()
