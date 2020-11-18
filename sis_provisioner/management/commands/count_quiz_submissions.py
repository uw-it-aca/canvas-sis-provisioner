from django.core.management.base import BaseCommand
from django.conf import settings
from uw_canvas.reports import Reports
from uw_canvas.courses import Courses
from uw_canvas.quizzes import Quizzes
from sis_provisioner.dao.course import valid_academic_course_sis_id
from sis_provisioner.exceptions import CoursePolicyException
import csv
import re


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('term_sis_id', help='Term SIS ID')

    def handle(self, *args, **options):
        term_sis_id = options.get('term_sis_id')

        report_client = Reports()
        term = report_client.get_term_by_sis_id(term_sis_id)

        course_report = report_client.create_course_provisioning_report(
            settings.RESTCLIENTS_CANVAS_ACCOUNT_ID, term_id=term.term_id)

        sis_data = report_client.get_report_data(course_report)
        report_client.delete_report(course_report)

        ind_study_regexp = re.compile("-[A-F0-9]{32}$")

        quiz_submission_total = 0

        course_client = Courses()
        quiz_client = Quizzes()
        for row in csv.reader(sis_data):
            if not len(row):
                continue

            sis_course_id = row[1]
            status = row[9]
            course_submission_total = 0

            try:
                valid_academic_course_sis_id(sis_course_id)
            except CoursePolicyException:
                continue

            if ind_study_regexp.match(sis_course_id):
                continue

            if status is not None and status == "active":
                for quiz in quiz_client.get_quizzes_by_sis_id(sis_course_id):
                    subs = quiz_client.get_submissions_for_sis_course_id_and_quiz_id(
                        sis_course_id, quiz.quiz_id)

                    course_submission_total += len(subs)

            print("{} submissions: {}".format(
                sis_course_id, course_submission_total))
            quiz_submission_total += course_submission_total

        print("Total quiz submissions for {}: {}".format(
            term_sis_id, quiz_submission_total))
