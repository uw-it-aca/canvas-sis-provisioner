# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import BaseCommand, CommandError
from uw_canvas.users import Users
from restclients_core.exceptions import DataFailureException
import csv


class Command(BaseCommand):
    help = ''

    def add_arguments(self, parser):
        parser.add_argument('file_path', help='CSV file')

    def handle(self, *args, **options):
        file_path = options.get('file_path')

        outfile = open('gmail_enrollments.csv', 'wb')
        csv.register_dialect('unix_newline', lineterminator='\n')
        writer = csv.writer(outfile, dialect='unix_newline')

        client = Enrollments()

        with open(file_path, 'rb') as csvfile:
            writer.writerow([
                'canvas_user_id', 'sis_user_id', 'login_id', 'role',
                'section_id', 'sis_section_id', 'course_id', 'sis_course_id'])

            reader = csv.reader(csvfile)
            for row in reader:
                if not len(row):
                    continue

                canvas_user_id = row[0]
                sis_user_id = row[1]
                login_id = row[2]

                print(sis_user_id)
