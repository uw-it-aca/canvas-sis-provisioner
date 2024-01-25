# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import BaseCommand, CommandError
from sis_provisioner.dao.canvas import (
    get_course_report_data, DataFailureException)
from sis_provisioner.models.course import Course
from datetime import datetime
from logging import getLogger
import csv

logger = getLogger(__name__)


class Command(BaseCommand):
    help = "Insert courses from a Canvas course provisioning report file"

    def add_arguments(self, parser):
        parser.add_argument('-a', '--account-id', action='store',
                            dest='account-id', default=None,
                            help='Account ID')

    def handle(self, *args, **options):
        account_id = options.get('account-id')
        logger.info(f'Account ID: {account_id}')
        curr_year = datetime.now().year

        report_data = get_course_report_data(account_id=account_id)

        outpath = f'/app/{account_id}-expiring-courses-{curr_year}.csv'
        outfile = open(outpath, 'w')
        csv.register_dialect('unix_newline', lineterminator='\n')
        writer = csv.writer(outfile, dialect='unix_newline')

        csv_reader = csv.reader(report_data)
        header = next(csv_reader)
        header.append('expiration_date')
        writer.writerow(header)

        for row in csv_reader:
            if not len(row):
                continue

            canvas_course_id = row[0] or None
            course_sis_id = row[1] or None

            try:
                course = Course.objects.find_course(
                    canvas_course_id, course_sis_id)

            except Course.MultipleObjectsReturned:
                logger.info(f'ERROR Multiple courses for {canvas_course_id}, '
                            f'{course_sis_id}')
                continue

            except Course.DoesNotExist:
                pass

            if course.expiration_date is not None:
                if course.expiration_date.year == curr_year:
                    row.append(course.expiration_date)
                    writer.writerow(row)

        outfile.close()
        print(outpath)
