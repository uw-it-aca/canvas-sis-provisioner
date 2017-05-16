from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from uw_canvas.reports import Reports
from uw_canvas.courses import Courses
from restclients_core.exceptions import DataFailureException
from sis_provisioner.dao.course import valid_academic_course_sis_id
from sis_provisioner.exceptions import CoursePolicyException
from time import sleep
import csv
import sys
import re


class Command(BaseCommand):
    args = "<term_sis_id>"
    help = "Create a report of active (published) courses, for the specified term."

    def handle(self, *args, **options):

        if len(args):
            sis_term_id = args[0]
        else:
            raise CommandError("term_sis_id is required")

        report_client = Reports()

        term = report_client.get_term_by_sis_id(sis_term_id)

        user_report = report_client.create_course_provisioning_report(
            settings.RESTCLIENTS_CANVAS_ACCOUNT_ID, term_id=term.term_id)

        sis_data = report_client.get_report_data(user_report)

        report_client.delete_report(user_report)

        ind_study_regexp = re.compile("-[A-F0-9]{32}$")
        course_client = Courses()

        for row in csv.reader(sis_data):
            if not len(row):
                continue

            sis_course_id = row[1]
            status = row[8]

            try:
                valid_academic_course_sis_id(sis_course_id)
            except CoursePolicyException:
                continue

            if ind_study_regexp.match(sis_course_id):
                continue

            if status is not None and status == "active":
                print sis_course_id