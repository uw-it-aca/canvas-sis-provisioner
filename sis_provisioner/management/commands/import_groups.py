# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models.group import Group
from sis_provisioner.exceptions import (
    EmptyQueueException, MissingImportPathException)
from sis_provisioner.builders.groups import GroupBuilder
import traceback


class Command(SISProvisionerCommand):
    help = 'Builds csv files for group membership.'

    def add_arguments(self, parser):
        parser.add_argument(
            'priority', type=int, default=Group.PRIORITY_DEFAULT,
            choices=[Group.PRIORITY_DEFAULT,
                     Group.PRIORITY_HIGH,
                     Group.PRIORITY_IMMEDIATE],
            help='Import groups with priority <priority>')

    def handle(self, *args, **options):
        priority = options.get('priority')
        try:
            imp = Group.objects.queue_by_priority(priority)
        except EmptyQueueException:
            self.update_job()
            return

        try:
            imp.csv_path = GroupBuilder(imp.queued_objects()).build()
        except Exception:
            imp.csv_errors = traceback.format_exc()

        imp.save()

        try:
            imp.import_csv()
        except MissingImportPathException as ex:
            if not imp.csv_errors:
                imp.delete()

        self.update_job()
