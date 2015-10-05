from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from django.utils.timezone import utc
from sis_provisioner.models import Group, EmptyQueueException,\
    MissingImportPathException, PRIORITY_DEFAULT, PRIORITY_IMMEDIATE
from sis_provisioner.csv_builder import CSVBuilder
from dateutil.parser import parse
from datetime import datetime, timedelta
import traceback
import re


class Command(BaseCommand):
    args = "<priority>"
    help = "Builds csv files for group membership."

    option_list = BaseCommand.option_list + (
        make_option('-m', '--mtime', dest='mtime', default=None, help='membership modified since, e.g., 2015-12-31T14:30+8 or -30m or -1d or '),
        make_option('-a', '--all-enrollments', action='store_true', dest='all_enrollments',
                    default=False, help='Generate complete CSV (default is only changes since last import)'),
    )

    def handle(self, *args, **options):
        priority = PRIORITY_DEFAULT
        delta = (not options['all_enrollments'])
        modified_since = None

        if len(args):
            priority = int(args[0])
            if priority < PRIORITY_DEFAULT or priority > PRIORITY_IMMEDIATE:
                raise CommandError('Invalid priority: %s' % priority)

        if priority > PRIORITY_DEFAULT:
            delta = False

        if options['mtime']:
            match = re.match(r'^(\d+)([smhdw])$', options['mtime'])
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
                modified_since = parse(options['mtime'])

        try:
            if modified_since:
                imp = Group.objects.queue_by_modified_date(modified_since)
            else:
                imp = Group.objects.queue_by_priority(priority)
        except EmptyQueueException:
            return

        try:
            imp.csv_path = CSVBuilder().generate_csv_for_group_memberships(
                imp.queued_objects().values_list('course_id', flat=True),
                delta=delta)
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
