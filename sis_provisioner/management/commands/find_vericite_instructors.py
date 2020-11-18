from django.core.management.base import BaseCommand
from django.conf import settings
from uw_canvas.reports import Reports
from uw_canvas.assignments import Assignments
from uw_canvas.models import ReportType
from restclients_core.exceptions import InvalidRegID, DataFailureException
from sis_provisioner.exceptions import CoursePolicyException
from sis_provisioner.dao.course import valid_academic_course_sis_id
from sis_provisioner.dao.user import get_person_by_regid
from time import sleep
import csv
import sys
import re


class Command(BaseCommand):
    args = "<term_sis_id>"
    help = (
        "Create a report of instructors for courses with assigments using "
        "Vericite, for the specified term.")

    def add_arguments(self, parser):
        parser.add_argument('term_sis_id', help='Term to search')

    def handle(self, *args, **options):
        sis_term_id = options.get('term_sis_id')

        report_client = Reports()

        term = report_client.get_term_by_sis_id(sis_term_id)

        user_report = report_client.create_report(
            ReportType.SIS_EXPORT, settings.RESTCLIENTS_CANVAS_ACCOUNT_ID,
            term_id=term.term_id, params={"enrollments": True})

        sis_data = report_client.get_report_data(user_report)

        report_client.delete_report(user_report)

        vericite_courses = {}
        non_vericite_courses = {}

        client = Assignments(per_page=100)

        row_count = sum(1 for row in csv.reader(sis_data))
        curr_row = 0
        for row in csv.reader(sis_data):
            curr_row += 1
            if not len(row):
                continue

            sis_course_id = row[0]
            uwregid = row[1]
            role = row[2]

            if role != 'teacher':
                continue

            if sis_course_id in non_vericite_courses:
                continue
            elif sis_course_id in vericite_courses:
                vericite_courses[sis_course_id].append(uwregid)
                continue

            try:
                valid_academic_course_sis_id(sis_course_id)
            except CoursePolicyException:
                continue

            try:
                vericite_enabled = False
                for a in client.get_assignments_by_sis_id(sis_course_id):
                    if a.vericite_enabled:
                        vericite_enabled = True
                        break
                if vericite_enabled:
                    vericite_courses[sis_course_id] = [uwregid]
                else:
                    non_vericite_courses[sis_course_id] = None

            except DataFailureException as ex:
                print(ex)
                continue

            print("Remaining: {}".format(row_count - curr_row))
            #sleep(0.2)

        outfile = open("vericite-instructors-{}.csv".format(sis_term_id), "w")
        csv.register_dialect('unix_newline', lineterminator='\n')
        writer = csv.writer(outfile, dialect='unix_newline')
        writer.writerow(["sis_course_id", "instructor_uwnetid"])
        for sis_course_id in vericite_courses:
            for uwregid in vericite_courses[sis_course_id]:
                try:
                    uwnetid = get_person_by_regid(uwregid).uwnetid
                    writer.writerow([
                        sis_course_id, "{}@uw.edu".format(uwnetid)])
                    #print("Found: {}, {}".format(sis_course_id, uwnetid))
                except InvalidRegID:
                    writer.writerow([sis_course_id, uwregid])
                except DataFailureException as ex:
                    print(ex)

        outfile.close()
