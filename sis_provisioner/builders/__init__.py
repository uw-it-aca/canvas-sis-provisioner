from sis_provisioner.csv.data import Collector
from sis_provisioner.csv.format import UserCSV, EnrollmentCSV
from sis_provisioner.models import User, Course, Enrollment
from sis_provisioner.dao.user import (
    valid_net_id, get_person_by_netid, get_person_by_gmail_id)
from sis_provisioner.dao.course import get_section_by_id
from sis_provisioner.exceptions import UserPolicyException
from restclients.exceptions import DataFailureException
from logging import getLogger
import json


class Builder(object):
    def __init__(self):
        self.data = Collector()
        self.queue_id = None
        self.invalid_users = {}
        self.logger = getLogger(__name__)

    def write(self):
        return self.data.write_files()

    def build(self):
        raise NotImplementedError

    def add_user_data_for_person(self, person, force=False):
        """
        Creates a line of user data for the passed person.  If force is not
        true, the data will only be created if the person has not been
        provisioned.
        """
        if person.uwregid in self.invalid_users:
            return

        try:
            valid_net_id(person.uwnetid)
        except UserPolicyException as err:
            self.invalid_users[person.uwregid] = True
            self.logger.info("Skip user %s: %s" % (person.uwregid, err))
            return

        if force is True:
            self.data.add(UserCSV(person))
        else:
            user = User.objects.add_user(person)
            if user.provisioned_date is None:
                if (self.data.add(UserCSV(person)) and user.queue_id is None):
                    user.queue_id = self.queue_id
                    user.save()

    def add_teacher_enrollment_data(self, section, person, status='active'):
        """
        Generates one teacher enrollment for the passed section and person.
        """
        self.add_user_data_for_person(person)

        if person.uwregid not in self.invalid_users:
            self.data.add(EnrollmentCSV(
                section=section, instructor=person, status=status))

    def add_student_enrollment_data(self, registration):
        """
        Generates one student enrollment for the passed registration.
        """
        self.add_user_data_for_person(registration.person)

        if registration.person.uwregid not in self.invalid_users:
            self.data.add(EnrollmentCSV(registration=registration))

    def add_group_enrollment_data(self, member, section_id, role, status):
        """
        Generates one enrollment for the passed group member.
        """
        if member.is_uwnetid():
            person = get_person_by_netid(member.name)
            self.add_user_data_for_person(person)

            if person.uwregid not in self.invalid_users:
                self.data.add(EnrollmentCSV(
                    section_id=section_id, person=person, role=role,
                    status=status))

        elif member.is_eppn():
            if status == Enrollment.ACTIVE_STATUS and hasattr(member, 'login'):
                person = get_person_by_gmail_id(member.login)
                self.data.add(UserCSV(person))
            else:
                person = get_person_by_gmail_id(member.name)

            self.data.add(EnrollmentCSV(
                section_id=section_id, person=person, role=role,
                status=status))

    def get_section_resource_by_id(self, section_id):
        """
        Fetch the section resource for the passed section ID.
        """
        try:
            return get_section_by_id(section_id)

        except DataFailureException as err:
            data = json.loads(err.msg)
            Course.objects.remove_from_queue(section_id, "%s: %s %s" % (
                err.url, err.status, data["StatusDescription"]))
            self.logger.info("Skip section %s: %s %s" % (
                section_id, err.status, data["StatusDescription"]))
            raise

        except ValueError as err:
            Course.objects.remove_from_queue(section_id, err)
            self.logger.info("Skip section %s: %s" % (section_id, err))
            raise