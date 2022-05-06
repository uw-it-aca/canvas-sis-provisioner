# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.core.management.base import BaseCommand
from django.conf import settings
from uw_pws import PWS
from uw_canvas.accounts import Accounts
from uw_canvas.reports import Reports
from restclients_core.exceptions import DataFailureException, InvalidRegID
from os.path import dirname
import csv
import sys


class Command(BaseCommand):
    help = ("Create a list of active teacher email addresses for a "
            "sub-account and term. Used for creating the recipient list for "
            "the ACA Canvas newsletter.")

    def add_arguments(self, parser):
        parser.add_argument('subaccount_id', help='Subaccount ID')
        parser.add_argument('term_id', help='SIS Term ID')

    def handle(self, *args, **options):
        subaccount_id = options.get('subaccount_id')
        sis_term_id = options.get('term_id')

        accounts = Accounts()
        reports = Reports()
        pws = PWS()

        outpath = "{}/{}-{}-{}.csv".format(
            dirname(__file__), "active-instructors", subaccount_id,
            sis_term_id)
        outfile = open(outpath, "w")
        csv.register_dialect('unix_newline', lineterminator='\n')
        writer = csv.writer(outfile, dialect='unix_newline')
        writer.writerow(['email', 'first_name', 'last_name'])

        account = accounts.get_account(subaccount_id)
        term = reports.get_term_by_sis_id(sis_term_id)

        enrollment_report = reports.create_enrollments_provisioning_report(
            account.account_id, term.term_id)
        enrollment_data = reports.get_report_data(enrollment_report)

        all_instructors = {}

        enrollment_csv_data = csv.reader(enrollment_data)
        header = next(enrollment_csv_data)
        course_id_idx = header.index("course_id")
        sis_user_id_idx = header.index("user_id")
        role_idx = header.index("role")
        status_idx = header.index("status")

        for row in enrollment_csv_data:
            if not len(row):
                continue

            course_id = row[course_id_idx]
            sis_user_id = row[sis_user_id_idx]
            role = row[role_idx]
            status = row[status_idx]

            if (sis_user_id != "" and role.lower() == "teacher" and
                    status.lower() == "active"):
                if course_id not in all_instructors:
                    all_instructors[course_id] = []

                all_instructors[course_id].append(sis_user_id)

        course_report = reports.create_course_provisioning_report(
            account.account_id, term.term_id)
        course_data = reports.get_report_data(course_report)

        course_csv_data = csv.reader(course_data)
        header = next(course_csv_data)
        course_id_idx = header.index("course_id")
        sis_account_id_idx = header.index("account_id")
        status_idx = header.index("status")

        active_instructors = {}
        for row in course_csv_data:
            if not len(row):
                continue

            course_id = row[course_id_idx]
            sis_account_id = row[sis_account_id_idx]
            status = row[status_idx]

            if (sis_account_id != "" and status.lower() == "active" and
                    course_id in all_instructors):
                for sis_user_id in all_instructors[course_id]:
                    if sis_user_id in active_instructors:
                        continue

                    try:
                        person = pws.get_person_by_regid(sis_user_id)
                        active_instructors[sis_user_id] = [
                            person.uwnetid + "@uw.edu",
                            person.preferred_first_name or person.first_name,
                            person.preferred_surname or person.surname]
                    except InvalidRegID:
                        continue
                    except DataFailureException as err:
                        if err.status == 404:
                            continue
                        else:
                            raise

        for csv_data in active_instructors.values():
            writer.writerow(csv_data)
        outfile.close()

        reports.delete_report(enrollment_report)
        reports.delete_report(course_report)

        print(outpath)
