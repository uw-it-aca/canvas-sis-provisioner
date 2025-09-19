# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from uw_canvas.reports import Reports
from uw_canvas.courses import Courses
from uw_canvas.files import Files
from uw_canvas.dao import CanvasFileDownload_DAO
from logging import getLogger
import csv
import os

logger = getLogger(__name__)


class Command(BaseCommand):
    help = ("Download course syllabus files, for the specified term.")

    def add_arguments(self, parser):
        parser.add_argument('account_id', help='Account ID')
        parser.add_argument('term_sis_id', help='Term SIS ID')

    def create_file_path(self, account_id, term_sis_id, course_sis_id, name):
        return os.path.join(
            f'Account {account_id} Syllabus Files',
            term_sis_id,
            course_sis_id.replace(f'{term_sis_id}-', ''),
            name)

    def handle(self, *args, **options):
        account_id = options.get('account_id')
        term_sis_id = options.get('term_sis_id')

        report_client = Reports()

        term = report_client.get_term_by_sis_id(term_sis_id)

        course_report = report_client.create_course_sis_export_report(
            account_id, term_id=term.term_id)
        sis_data = report_client.get_report_data(course_report)
        report_client.delete_report(course_report)

        course_client = Courses()
        file_client = Files(per_page=100)
        download_client = CanvasFileDownload_DAO()

        content_types = [
          'application/pdf',
          'application/msword',
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document'  # noqa
        ]
        course_params = {"include": ["syllabus_body"]}
        file_params = {'content_types': content_types, 'sort': 'updated_at'}

        for row in csv.reader(sis_data):
            if not len(row) or row[0] == 'course_id':
                continue

            course_sis_id = row[0]
            course_has_syllabus = False

            course = course_client.get_course_by_sis_id(
                course_sis_id, params=course_params)

            if course.syllabus_body:
                logger.info(f"Found HTML syllabus in {course_sis_id}")

                course_has_syllabus = True
                syllabus_path = self.create_file_path(
                    account_id, term_sis_id, course_sis_id, 'syllabus.html')

                with default_storage.open(syllabus_path, mode='w') as f:
                    f.write(course.syllabus_body)

            seen_files = set()
            for file in file_client.get_course_files_by_sis_id(
                    course_sis_id, params=file_params):

                if 'syl' not in file.filename.lower():
                    continue

                response = download_client.getURL(file.url)
                if response.status == 200:
                    logger.info(
                        f"Found file {file.filename} in {course_sis_id}")

                    course_has_syllabus = True
                    file_path = self.create_file_path(
                        account_id, term_sis_id, course_sis_id, file.filename)

                    if file.filename in seen_files:
                        # Remove previous versions to avoid checksum errors
                        default_storage.delete(file_path)

                    try:
                        with default_storage.open(file_path, mode='wb') as f:
                            f.write(response.data)

                        seen_files.add(file.filename)

                    except Exception as ex:
                        logger.error(ex)

            if not course_has_syllabus:
                logger.info(
                    f"Syllabus not found in {course_sis_id}")

                notfound_path = self.create_file_path(
                    account_id, term_sis_id, course_sis_id, 'Missing syllabus')

                with default_storage.open(notfound_path, mode='w') as f:
                    f.write('A syllabus file could not be identified for '
                            'this course.')
