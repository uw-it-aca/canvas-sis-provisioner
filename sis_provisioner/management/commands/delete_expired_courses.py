# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models.course import Course, Import
from sis_provisioner.exceptions import (
    EmptyQueueException, MissingImportPathException)
from sis_provisioner.builders.courses import ExpiredCourseBuilder
import traceback
import os


class Command(SISProvisionerCommand):
    help = "Create a csv import file of expired courses for a specified \
            term. The csv file will be used to delete expired courses from \
            Canvas."

    def add_arguments(self, parser):
        parser.add_argument('-t', '--term-sis-id', help='Term SIS ID')

    def handle(self, *args, **options):
        term_sis_id = (
            options.get('term-sis-id') or os.getenv('EXPIRED_COURSES_TERM'))
        if not term_sis_id:
            print('Empty term-sis-id arg not implemented!')
            return

        imp = Import(priority=Course.PRIORITY_DEFAULT,
                     csv_type='expired_course',
                     override_sis_stickiness=True)
        imp.save()

        try:
            imp.csv_path = ExpiredCourseBuilder().build(
                term_sis_id=term_sis_id, queue_id=imp.pk)
        except Exception:
            imp.csv_errors = traceback.format_exc()

        imp.save()

        try:
            imp.import_csv()
        except MissingImportPathException as ex:
            if not imp.csv_errors:
                imp.delete()

        self.update_job()
