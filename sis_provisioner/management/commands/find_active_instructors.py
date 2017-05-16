from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from uw_pws import PWS
from uw_canvas.accounts import Accounts
from uw_canvas.reports import Reports
from restclients_core.exceptions import DataFailureException, InvalidRegID
from os.path import dirname
import csv
import sys


class Command(BaseCommand):
    args = "<subaccount_id> <term_id>"
    help = "Create a list of active teacher email addresses for a sub-account \
            and term. Used for creating the recipient list for the ACA Canvas \
            newsletter."

    def handle(self, *args, **options):
        if len(args) == 2:
            subaccount_id = args[0]
            sis_term_id = args[1]
        else:
            raise CommandError("find_active_instructors <subaccount_id> <term_id>")

        accounts = Accounts()
        reports = Reports()
        pws = PWS()

        account = accounts.get_account(subaccount_id)
        term = reports.get_term_by_sis_id(sis_term_id)

        enrollment_report = reports.create_enrollments_provisioning_report(
            account.account_id, term.term_id)
        enrollment_data = reports.get_report_data(enrollment_report)

        all_instructors = {}

        enrollment_csv_data = csv.reader(enrollment_data)
        header = enrollment_csv_data.next()
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
        header = course_csv_data.next()
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
                    if sis_user_id not in active_instructors:
                        try:
                            person = pws.get_person_by_regid(sis_user_id)
                            email = person.uwnetid + "@uw.edu"
                            active_instructors[sis_user_id] = email
                        except InvalidRegID:
                            continue
                        except DataFailureException as err:
                            if err.status == 404:
                                continue
                            else:
                                raise

        filename = "-".join(["active-instructors", subaccount_id, sis_term_id])
        outpath = dirname(__file__) + "/" + filename + ".txt"

        f = open(outpath, "w")
        data = active_instructors.values()
        data.sort()
        f.write("\n".join(data))
        f.close()

        reports.delete_report(enrollment_report)
        reports.delete_report(course_report)

        print outpath