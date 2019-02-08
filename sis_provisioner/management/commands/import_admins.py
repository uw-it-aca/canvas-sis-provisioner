from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models import Admin
from sis_provisioner.exceptions import (
    EmptyQueueException, MissingImportPathException)
from sis_provisioner.builders.admins import AdminBuilder
from sis_provisioner.dao.astra import Admins as AstraAdmins
import traceback


class Command(SISProvisionerCommand):
    help = "Reconcile ASTRA / Canvas Administrators"

    def add_arguments(self, parser):
        parser.add_argument(
            '-r', '--root-account', action='store', dest='root_account',
            default=settings.RESTCLIENTS_CANVAS_ACCOUNT_ID,
            help='Reconcile at and below root account (default: {})'.format(
                settings.RESTCLIENTS_CANVAS_ACCOUNT_ID))
        parser.add_argument(
            '-c', '--commit', action='store_true', dest='commit',
            default=False,
            help='update Canvas with ASTRA admins and roles')
        parser.add_argument(
            '-a', '--astra-is-authoritative', action='store_true',
            dest='remove_non_astra', default=False,
            help='Remove Canvas admins not found in ASTRA')

    def handle(self, *args, **options):
        try:
            imp = Admin.objects.queue_all()
        except EmptyQueueException as ex:
            self.update_job()
            return

        try:
            AstraAdmins().load_all_admins(imp.pk)

            imp.csv_path = AdminBuilder().build(
                root_account=options.get('root_account'),
                remove_non_astra=options.get('remove_non_astra'))
        except Exception:
            imp.csv_errors = traceback.format_exc()

        imp.save()

        if options.get('commit'):
            try:
                imp.import_csv()
            except MissingImportPathException as ex:
                if not imp.csv_errors:
                    imp.delete()

        self.update_job()
