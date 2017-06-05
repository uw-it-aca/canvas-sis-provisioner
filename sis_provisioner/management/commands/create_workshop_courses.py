from django.core.management.base import BaseCommand
from django.conf import settings
from sis_provisioner.dao.user import get_person_by_netid, user_sis_id
from sis_provisioner.dao.canvas import INSTRUCTOR_ENROLLMENT, ENROLLMENT_ACTIVE
from sis_provisioner.exceptions import UserPolicyException
from sis_provisioner.models import Import, PRIORITY_DEFAULT
from sis_provisioner.csv.data import Collector
from sis_provisioner.csv.format import UserCSV, EnrollmentCSV, CourseCSV
from datetime import date
import re
import sys


class Command(BaseCommand):
    help = "Creates a course for each workshop participant from the specified \
            file_path, using the passed <workshop_name> and <term_sis_id>."

    def add_arguments(self, parser):
        parser.add_argument('file_path', help='File path')
        parser.add_argument('workshop_name', help='Workshop name')
        parser.add_argument('term_sis_id', help='Term SIS ID')

    def handle(self, *args, **options):
        file_path = options.get('file_path')
        workshop_name = options.get('workshop_name')
        term_sis_id = options.get('term_sis_id')
        account_sis_id = 'course-request-sandbox'

        with open(file_path, 'r') as infile:
            file_data = infile.read()
        netids = file_data.splitlines()

        csvdata = Collector()

        for netid in netids:
            try:
                person = get_person_by_netid(netid.strip())
            except UserPolicyException as err:
                print("Skipped user %s: %s" % (netid, err))
                continue

            if not csvdata.add(UserCSV(person)):
                continue

            course_sis_id = '%s-%s-%s' % (
                term_sis_id,
                re.sub(r'[^\w]', '-', workshop_name.lower()),
                person.uwnetid)
            short_name = '%s %s' % (workshop_name, date.today().year)
            long_name = '%s Sandbox' % short_name

            csvdata.add(CourseCSV(
                course_id=course_sis_id, short_name=short_name,
                long_name=long_name, account_id=account_sis_id,
                term_id=term_sis_id, status='active'))

            csvdata.add(EnrollmentCSV(
                course_id=course_sis_id, person=person,
                role=INSTRUCTOR_ENROLLMENT, status=ENROLLMENT_ACTIVE))

        csv_path = csvdata.write()

        if csv_path:
            imp = Import(priority=PRIORITY_DEFAULT, csv_type='course',
                         csv_path=csv_path)
            imp.save()
            imp.import_csv()
