from django.core.management.base import CommandError
from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models import Course, PRIORITY_DEFAULT, PRIORITY_IMMEDIATE
from sis_provisioner.exceptions import (
    EmptyQueueException, MissingImportPathException)
from sis_provisioner.builders.courses import CourseBuilder
import traceback


class Command(SISProvisionerCommand):
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
            self.update_job()
            return

        include_enrollment = True if (priority > PRIORITY_DEFAULT) else False
        try:
            builder = CourseBuilder(imp.queued_objects())
            imp.csv_path = builder.build(include_enrollment=include_enrollment)
        except:
            imp.csv_errors = traceback.format_exc()

        imp.save()

        try:
            imp.import_csv()
        except MissingImportPathException as ex:
            if not imp.csv_errors:
                imp.delete()

        self.update_job()
