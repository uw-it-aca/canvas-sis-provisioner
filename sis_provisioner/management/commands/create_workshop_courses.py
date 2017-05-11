from django.core.management.base import BaseCommand, CommandError
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
    args = "<file_path> <workshop_name> <term_sis_id>"
    help = "Creates a course for each workshop participant from the specified \
            file_path, using the passed <workshop_name> and <term_sis_id>."

    def handle(self, *args, **options):

        if not len(args):
            raise CommandError("Usage: create_workshop_courses <path> "
                               "<workshop_name><term_sis_id>")

        file_path = args[0]
        workshop_name = args[1]
        term_sis_id = args[2]
        account_sis_id = 'course-request-sandbox'

        with open(file_path, 'r') as infile:
            file_data = infile.read()
        netids = file_data.splitlines()

        csvdata = Collector()

        for netid in netids:
            try:
                person = get_person_by_netid(netid.strip())
            except UserPolicyException as err:
                print "Skipped user %s: %s" % (netid, err)
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
