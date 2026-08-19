# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


import csv
from datetime import datetime, timedelta, timezone

from django.core.management.base import BaseCommand

from sis_provisioner.dao.user import valid_gmail_id, valid_reg_id
from sis_provisioner.exceptions import UserPolicyException


class Command(BaseCommand):
    help = "Creates a report of users in Canvas."

    def add_arguments(self, parser):
        parser.add_argument(
            'last_access_report', help='last_access_report_path')
        parser.add_argument(
            'enrollment_report', help='enrollment_report_path')

    def handle(self, *args, **options):
        last_access_report = options.get('last_access_report')
        enrollment_report = options.get('enrollment_report')

        users_all = 0
        users_uw = 0
        users_google = 0
        users_unknown = 0
        users_no_sisid = 0

        users_uw_login_one_year = 0
        users_google_login_one_year = 0

        users_uw_login_never = 0
        users_google_login_never = 0

        users_uw_no_enrollments = 0
        users_google_no_enrollments = 0

        enrollments = {}
        with open(enrollment_report, 'rb') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                sis_user_id = row[3]
                if len(sis_user_id):
                    if sis_user_id in enrollments:
                        enrollments[sis_user_id] += 1
                    else:
                        enrollments[sis_user_id] = 1

        with open(last_access_report, 'rb') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                sis_user_id = row[1]
                if len(sis_user_id):
                    last_access = row[3]
                    try:
                        valid_reg_id(sis_user_id)
                        users_all += 1
                        users_uw += 1
                        if len(last_access):
                            if not self.logged_in_past_year(last_access):
                                users_uw_login_one_year += 1
                        else:
                            users_uw_login_never += 1

                        if sis_user_id not in enrollments:
                            users_uw_no_enrollments += 1

                    except UserPolicyException:
                        try:
                            valid_gmail_id(sis_user_id)
                            users_all += 1
                            users_google += 1
                            if len(last_access):
                                if not self.logged_in_past_year(last_access):
                                    users_google_login_one_year += 1
                            else:
                                users_google_login_never += 1

                            if sis_user_id not in enrollments:
                                users_google_no_enrollments += 1

                        except UserPolicyException:
                            users_unknown += 1
                else:
                    if row[2] != 'Student, Test':
                        users_no_sisid += 1

        print('\n\n')
        print(f'All users: {users_all}')
        print(f'UW users: {users_uw}')
        print(f'UW users with 0 enrollments: {users_uw_no_enrollments}')
        print(f'UW users with 0 logins: {users_uw_login_never}')
        print(f'UW users who have not logged in the past year: {users_uw_login_one_year}')
        print('\n\n')
        print(f'Google users: {users_google}')
        print(f'Google users with 0 enrollments: {users_google_no_enrollments}')
        print(f'Google users with 0 logins: {users_google_login_never}')
        print(f'Google users who have not logged in the past year: {users_google_login_one_year}')
        print('\n\n')
        print(f'No SIS ID users: {users_no_sisid}')
        print(f'Bad SIS ID users: {users_unknown}')
        print('\n\n')

    def logged_in_past_year(self, last_access_str):
        last_access_dt = datetime.strptime(
            last_access_str[:-6], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
        return last_access_dt < (datetime.now(timezone.utc) - timedelta(days=365))
