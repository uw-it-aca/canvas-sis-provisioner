# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.core.management.base import BaseCommand
from django.conf import settings
from uw_canvas.reports import Reports
from uw_canvas.courses import Courses, COURSES_API
from restclients_core.exceptions import DataFailureException
from sis_provisioner.dao.course import valid_academic_course_sis_id
from sis_provisioner.exceptions import CoursePolicyException
from logging import getLogger
import csv
import os

logger = getLogger(__name__)
course_client = Courses()
pretext = "ARCHIVED: "


class Command(BaseCommand):
    help = ("Updates all SIS course titles.")

    def add_arguments(self, parser):
        parser.add_argument("term_sis_id", help="Term SIS ID")

    def update_course_title(self, course_id, name, course_code):
        url = COURSES_API.format(course_id)
        body = {"course": {"name": name, "course_code": course_code}}
        return course_client._put_resource(url, body)

    def handle(self, *args, **options):
        term_sis_id = options.get("term_sis_id")

        report_client = Reports()

        term = report_client.get_term_by_sis_id(term_sis_id)

        course_report = report_client.create_course_provisioning_report(
            settings.RESTCLIENTS_CANVAS_ACCOUNT_ID, term_id=term.term_id)

        course_data = report_client.get_report_data(course_report)
        course_csv_data = csv.reader(course_data)

        header = next(course_csv_data)
        canvas_course_id_idx = header.index("canvas_course_id")
        sis_course_id_idx = header.index("course_id")
        long_name_idx = header.index("long_name")
        short_name_idx = header.index("short_name")

        course_client = Courses()
        for row in course_csv_data:
            if not len(row):
                continue

            sis_course_id = row[sis_course_id_idx]
            try:
                valid_academic_course_sis_id(sis_course_id)
            except CoursePolicyException:
                continue

            course_id = row[canvas_course_id_idx]
            long_name = row[long_name_idx].removeprefix(pretext)
            short_name = row[short_name_idx].removeprefix(pretext)
            new_long_name = f"{pretext}{long_name}"
            new_short_name = f"{pretext}{short_name}"

            try:
                data = self.update_course_title(
                    course_id, new_long_name, new_short_name)
                print(data)
            except DataFailureException as ex:
                print(ex)

        report_client.delete_report(course_report)
