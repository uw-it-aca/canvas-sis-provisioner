from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models import Admin
from sis_provisioner.exceptions import (
    EmptyQueueException, MissingImportPathException)
from sis_provisioner.builders.admins import AdminBuilder
from sis_provisioner.dao.admin import Admins
import traceback


class Command(SISProvisionerCommand):
    help = "Reconcile ASTRA / Canvas Administrators"

    def add_arguments(self, parser):
        parser.add_argument(
            '-c', '--commit', action='store_true', dest='commit',
            default=False,
            help='update Canvas with ASTRA admins and roles')

    def handle(self, *args, **options):
        try:
            imp = Admin.objects.queue_all()
        except EmptyQueueException as ex:
            self.update_job()
            return

        try:
            Admins().load_all_admins(imp.pk)

            builder = AdminBuilder(imp.queued_objects())
            imp.csv_path = builder.build()
        except Exception:
            imp.csv_errors = traceback.format_exc()

        imp.save()

        if options.get('commit'):
            try:
                imp.import_csv()
            except MissingImportPathException as ex:
                if not imp.csv_errors:
                    imp.delete()
        else:
            print('CSV Path: {}'.format(imp.csv_path))
            print('Error: {}'.format(imp.csv_errors))
            imp.delete()

        self.update_job()
