from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models import (
    CourseMember, PRIORITY_DEFAULT, PRIORITY_HIGH, PRIORITY_IMMEDIATE)
from sis_provisioner.exceptions import (
    EmptyQueueException, MissingImportPathException)
from sis_provisioner.builders.group_enrollments import GroupEnrollmentBuilder
import traceback


class Command(SISProvisionerCommand):
    help = "Builds csv from group events memberships"

    def add_arguments(self, parser):
        parser.add_argument(
            '--priority', type=int, default=PRIORITY_DEFAULT,
            choices=[PRIORITY_DEFAULT, PRIORITY_HIGH, PRIORITY_IMMEDIATE],
            help='Import group members with priority <priority>')

    def handle(self, *args, **options):
        priority = options.get('priority')
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
