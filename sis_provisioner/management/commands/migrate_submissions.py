# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from uw_canvas.submissions import Submissions
from uw_canvas.courses import Courses
from restclients_core.exceptions import DataFailureException
import csv
import sys


class Command(BaseCommand):
    help = ''

    def add_arguments(self, parser):
        parser.add_argument('file_path', help='CSV file')

    def handle(self, *args, **options):
        file_path = options.get('file_path')

        outfile = open('submissions.csv', 'wb')
        csv.register_dialect('unix_newline', lineterminator='\n')
        writer = csv.writer(outfile, dialect='unix_newline')

        course_client = Courses()
        sub_client = Submissions()

        file_total = 0
        with open(file_path, 'rb') as csvfile:
            writer.writerow(['course_id', 'assignment_id', 'term_id',
                             'filename', 'content_type', 'size', 'url'])

            reader = csv.reader(csvfile)
            for row in reader:
                if not len(row):
                    continue

                course_id = row[0]
                assignment_id = row[1]
                assignment_total = 0

                if course_id == 'course_id':
                    continue

                try:
                    course = course_client.get_course(course_id)

                    if course.term.sis_term_id is None:  # Default term
                        print('Skipping: %s' % course.name)
                        continue

                    subs = sub_client.get_submissions_by_course_and_assignment(
                        course_id, assignment_id)

                except DataFailureException as ex:
                    if ex.status == 404:
                        continue
                    else:
                        raise

                for submission in subs:
                    for attachment in submission.attachments:
                        writer.writerow([
                            course_id,
                            assignment_id,
                            course.term.sis_term_id,
                            attachment.display_name.encode('utf-8'),
                            attachment.content_type,
                            attachment.size,
                            attachment.url])
                        assignment_total += 1

                file_total += assignment_total
                print('%s: %s, total: %s' % (
                    course.sis_course_id, assignment_total, file_total))

        outfile.close()
