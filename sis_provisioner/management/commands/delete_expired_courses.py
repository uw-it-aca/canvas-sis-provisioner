# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from sis_provisioner.management.commands import SISProvisionerCommand
from sis_provisioner.models.course import Course, Import
from sis_provisioner.exceptions import (
    EmptyQueueException, MissingImportPathException)
from sis_provisioner.dao.term import get_term_by_year_and_quarter
from sis_provisioner.builders.courses import ExpiredCourseBuilder
import traceback


class Command(SISProvisionerCommand):
    help = "Create a csv import file of expired courses for a specified \
            term. The csv file will be used to delete expired courses from \
            Canvas."

    def add_arguments(self, parser):
        parser.add_argument('-t', '--term-sis-id', help='Term SIS ID')

    def handle(self, *args, **options):
        term_sis_id = options.get('term-sis-id')
        if term_sis_id:
            (year, quarter) = term_sis_id.split('-')
            target_term = get_term_by_year_and_quarter(year, quarter)

        else:
            print('Empty term-sis-id arg not implemented!')
            return

        term_sis_id = target_term.canvas_sis_id()
        imp = Import(priority=Course.PRIORITY_DEFAULT, csv_type='course')

        try:
            imp.csv_path = ExpiredCourseBuilder().build(
                term_sis_id=term_sis_id, queue_id=imp.queue_id)
        except Exception:
            imp.csv_errors = traceback.format_exc()

        imp.save()

        try:
            imp.import_csv()
        except MissingImportPathException as ex:
            if not imp.csv_errors:
                imp.delete()

        self.update_job()
