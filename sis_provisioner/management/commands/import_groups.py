from django.utils.timezone import utc
from optparse import make_option
from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models import (
    Group, PRIORITY_DEFAULT, PRIORITY_HIGH, PRIORITY_IMMEDIATE)
from sis_provisioner.exceptions import (
    EmptyQueueException, MissingImportPathException)
from sis_provisioner.builders.groups import GroupBuilder
from dateutil.parser import parse
from datetime import datetime, timedelta
import traceback
import re


class Command(SISProvisionerCommand):
    help = "Builds csv files for group membership."

    def add_arguments(self, parser):
        parser.add_argument(
            '--priority', type=int, default=PRIORITY_DEFAULT,
            choices=[PRIORITY_DEFAULT, PRIORITY_HIGH, PRIORITY_IMMEDIATE],
            help='Import groups with priority <priority>')
        parser.add_argument(
            '-m', '--mtime', dest='mtime', default=None,
            help='Membership modified since, e.g., 2015-12-31T14:30+8 or -30m or -1d or ')
        parser.add_argument(
            '-a', '--all-enrollments', action='store_true',
            dest='all_enrollments', default=False,
            help='Generate complete CSV (default is only changes since last import)')

    def handle(self, *args, **options):
        priority = options.get('priority')
        delta = (not options.get('all_enrollments'))
        modified_since = None

        if priority > PRIORITY_DEFAULT:
            delta = False

        if options.get('mtime'):
            match = re.match(r'^(\d+)([smhdw])$', options.get('mtime'))
            if match:
                offset = {
                    {
                        'w': 'weeks',
                        'd': 'days',
                        'h': 'hours',
                        'm': 'minutes',
                        's': 'seconds'
                    }[match.group(2)]: int(match.group(1))
                }

                modified_since = datetime.now() - timedelta(**offset)
            else:
                modified_since = parse(options.get('mtime'))

        try:
            if modified_since:
                imp = Group.objects.queue_by_modified_date(modified_since)
            else:
                imp = Group.objects.queue_by_priority(priority)
        except EmptyQueueException:
            self.update_job()
            return

        try:
            imp.csv_path = GroupBuilder(imp.queued_objects().values_list(
                    'course_id', flat=True)).build(delta=delta)
        except:
            imp.csv_errors = traceback.format_exc()

        imp.save()

        try:
            imp.import_csv()
        except MissingImportPathException as ex:
            if not imp.csv_errors:
                Group.objects.dequeue(imp.pk,
                    provisioned_date=datetime.utcnow().replace(tzinfo=utc))
                imp.delete()

        self.update_job()
