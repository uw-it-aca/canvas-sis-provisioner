from django.core.management.base import CommandError
from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models import (
    CourseMember, PRIORITY_DEFAULT, PRIORITY_IMMEDIATE)
from sis_provisioner.exceptions import (
    EmptyQueueException, MissingImportPathException)
from sis_provisioner.builders.group_enrollments import GroupEnrollmentBuilder
import traceback


class Command(SISProvisionerCommand):
    args = "<priority>"
    help = "Builds csv from group events memberships"

    def handle(self, *args, **options):
        priority = PRIORITY_DEFAULT

        if len(args):
            priority = int(args[0])
            if priority < PRIORITY_DEFAULT or priority > PRIORITY_IMMEDIATE:
                raise CommandError('Invalid priority: %s' % priority)

        try:
            imp = CourseMember.objects.queue_by_priority(priority)
        except EmptyQueueException:
            self.update_job()
            return

        try:
            imp.csv_path = GroupEnrollmentBuilder(imp.queued_objects()).build()
        except:
            imp.csv_errors = traceback.format_exc()

        imp.save()

        try:
            imp.import_csv()
        except MissingImportPathException as ex:
            if not imp.csv_errors:
                imp.delete()

        self.update_job()
