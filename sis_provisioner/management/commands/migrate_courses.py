# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

# ruff: noqa

import csv
from logging import getLogger

from django.core.management.base import BaseCommand
from restclients_core.exceptions import DataFailureException
from uw_canvas.accounts import Accounts
from uw_canvas.courses import Courses

from sis_provisioner.csv.data import Collector
from sis_provisioner.csv.format import CourseCSV

logger = getLogger(__name__)


class Command(BaseCommand):
    help = ('Migrate courses to another subaccount.')

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            help='CSV file containing the subaccount migration mapping.')

    def handle(self, *args, **options):
        file_path = options.get('file_path')
        aclient = Accounts()
        client = Courses(per_page=200)
        targets = {}
        source_account_ids = set()
        missing_account_targets = set()

        # Read migration map file and collect source and target subaccount ids
        with open(file_path, 'r') as infile:
            for row in csv.reader(infile):
                if not len(row) or 'subaccount' in row[0]:
                    continue

                source_account_sis_id = row[0].strip()
                target_account_sis_id = row[2].strip()

                try:
                    account = aclient.get_account_by_sis_id(
                        source_account_sis_id)
                    source_account_ids.add(account.account_id)
                    targets[source_account_sis_id] = target_account_sis_id
                except DataFailureException as ex:
                    logger.info(
                        f'Migration skipped for account {source_account_sis_id}: {ex}')
                    continue

        csvdata = Collector()
        # For each source subaccount, fetch the course provisioning report
        for account_sis_id in targets:
            try:
                courses = client.get_courses_in_account_by_sis_id(
                    account_sis_id, params={
                        'state': ['all'], 'include': ['term']})
            except DataFailureException as ex:
                logger.info(
                    f'Migration skipped for account {account_sis_id}: {ex}')
                continue

            # For each course in the account, create a csv row using the target
            # subaccount, all other values remain the same
            for course in courses:
                sis_course_id = course.sis_course_id
                target_account_id = targets[account_sis_id]
                status = 'deleted' if (
                    course.workflow_state == 'deleted') else 'active'

                if course.account_id not in source_account_ids:
                    missing_account_targets.add(course.account_id)
                    logger.info(
                        f'Migration skipped for course {course.course_id}: Missing account in '
                        f'target {target_account_id} for account {course.account_id} in source {account_sis_id}')
                    continue

                if sis_course_id is None or not len(sis_course_id):
                    sis_course_id = f'course_{course.course_id}'
                    try:
                        client.update_sis_id(course.course_id, sis_course_id)
                    except DataFailureException as ex:
                        logger.info(
                            f'Migration skipped for course {course.course_id}: {ex}')
                        continue

                csvdata.add(CourseCSV(
                    course_id=sis_course_id,
                    short_name=course.code,
                    long_name=course.name,
                    account_id=target_account_id,
                    term_id=course.term.sis_term_id,
                    status=status))

        csv_path = csvdata.write_files()
        if csv_path:
            if len(missing_account_targets):
                print(f'Not migrated: {missing_account_targets}')
            print(f'SIS Import file path: {csv_path}')
            # imp = Import(priority=Course.PRIORITY_DEFAULT, csv_type='course',
            #              csv_path=csv_path)
            # imp.save()
            # imp.import_csv()
