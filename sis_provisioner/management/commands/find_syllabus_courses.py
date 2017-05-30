from django.core.management.base import BaseCommand
from django.conf import settings
from uw_canvas.reports import Reports
from uw_canvas.courses import Courses
from restclients_core.exceptions import DataFailureException
from sis_provisioner.exceptions import CoursePolicyException
from sis_provisioner.dao.course import valid_academic_course_sis_id
from time import sleep
import csv
import sys
import re


class Command(BaseCommand):
    args = "<term_sis_id>"
    help = "Create a report of courses containing non-empty syllabus \
            descriptions, for the specified term."

    def add_arguments(self, parser):
        parser.add_argument('term_sis_id', help='Term to search')

    def handle(self, *args, **options):
	sis_term_id = options.get('term_sis_id')

        report_client = Reports()

        term = report_client.get_term_by_sis_id(sis_term_id)

        user_report = report_client.create_course_sis_export_report(
            settings.RESTCLIENTS_CANVAS_ACCOUNT_ID, term_id=term.term_id)

        sis_data = report_client.get_report_data(user_report)

        report_client.delete_report(user_report)

        ind_study_regexp = re.compile("-[A-F0-9]{32}$")
        course_client = Courses()
        print(["course_id","name","published","public_syllabus"])

        row_count = sum(1 for row in csv.reader(sis_data))
        curr_row = 0
        for row in csv.reader(sis_data):
            curr_row += 1
            if not len(row):
                continue

            sis_course_id = row[0]
            course_name = row[1]

            try:
                valid_academic_course_sis_id(sis_course_id)
            except CoursePolicyException:
                continue

            if ind_study_regexp.match(sis_course_id):
                continue

            try:
                course = course_client.get_course_by_sis_id(sis_course_id,
                    params={"include": "syllabus_body"})
            except DataFailureException as ex:
                print(ex)
                continue

            if course.syllabus_body is None:
                continue

            csv_line = [
                sis_course_id,
                course_name,
                str(course.workflow_state),
                course.public_syllabus,
            ]

            print(csv_line)
            print("Remaining: %s" % (row_count - curr_row))
            print(csv_line)
            sleep(1)
