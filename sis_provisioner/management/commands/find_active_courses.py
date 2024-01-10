# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import BaseCommand
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
    help = ("Create a report of active (published) courses, for the "
            "specified term.")

    def add_arguments(self, parser):
        parser.add_argument('term_sis_id', help='Term SIS ID')

    def handle(self, *args, **options):
        term_sis_id = options.get('term_sis_id')

        report_client = Reports()

        term = report_client.get_term_by_sis_id(term_sis_id)

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
                print(sis_course_id)
