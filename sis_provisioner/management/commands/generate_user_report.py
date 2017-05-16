from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from sis_provisioner.dao.user import valid_reg_id, valid_gmail_id
from sis_provisioner.exceptions import UserPolicyException
from datetime import datetime, timedelta
import csv


class Command(BaseCommand):
    help = "Creates a report of users in Canvas."

    def handle(self, *args, **options):
        last_access_report = '/home/jlaney/Downloads/last_user_access_csv_29_Feb_2016_507320160229-22874-1e0l09o.csv'
        enrollment_report = '/home/jlaney/Downloads/provisioning_csv_29_Feb_2016_507420160229-30814-ftbhlm.csv'

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
                            #print sis_user_id
                else:
                    if row[2] != 'Student, Test':
                        users_no_sisid += 1


        print '\n\n'
        print 'All users: %s' % users_all
        print 'UW users: %s' % users_uw
        print 'UW users with 0 enrollments: %s' % users_uw_no_enrollments
        print 'UW users with 0 logins: %s' % users_uw_login_never
        print 'UW users who have not logged in the past year: %s' % users_uw_login_one_year
        print '\n\n'
        print 'Google users: %s' % users_google
        print 'Google users with 0 enrollments: %s' % users_google_no_enrollments
        print 'Google users with 0 logins: %s' % users_google_login_never
        print 'Google users who have not logged in the past year: %s' % users_google_login_one_year
        print '\n\n'
        print 'No SIS ID users: %s' % users_no_sisid
        print 'Bad SIS ID users: %s' % users_unknown
        print '\n\n'
    
    def logged_in_past_year(self, last_access_str):
        last_access_dt = datetime.strptime(last_access_str[:-6],
                                           '%Y-%m-%dT%H:%M:%S')
        return last_access_dt < datetime.utcnow() - timedelta(days=365)