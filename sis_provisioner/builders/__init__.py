# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from sis_provisioner.models import User, Course
from sis_provisioner.csv.data import Collector
from sis_provisioner.csv.format import UserCSV, EnrollmentCSV
from sis_provisioner.dao.user import (
    valid_net_id, get_person_by_netid, get_person_by_gmail_id)
from sis_provisioner.dao.course import (
    get_section_by_id, get_registrations_by_section)
from sis_provisioner.dao.canvas import ENROLLMENT_ACTIVE
from sis_provisioner.exceptions import (
    UserPolicyException, CoursePolicyException, InvalidLoginIdException)
from restclients_core.exceptions import DataFailureException
from logging import getLogger


class Builder(object):
    def __init__(self, items=[]):
        self.data = Collector()
        self.queue_id = None
        self.invalid_users = {}
        self.items = items
        self.logger = getLogger(__name__)

    def _init_build(self, **kwargs):
        return

    def _process(self, item):
        raise NotImplementedError

    def _write(self):
        return self.data.write_files()

    def build(self, **kwargs):
        self._init_build(**kwargs)
        for item in self.items:
            self._process(item)
        return self._write()

    def add_user_data_for_person(self, person, force=False):
        """
        Creates a line of user data for the passed person.  If force is not
        true, the data will only be created if the person has not been
        provisioned. Returns True for valid users, False otherwise.
        """
        if person.uwregid in self.invalid_users:
            return False

        try:
            valid_net_id(person.uwnetid)
        except UserPolicyException as err:
            self.invalid_users[person.uwregid] = True
            self.logger.info("Skip user {}: {}".format(person.uwregid, err))
            return False

        if force is True:
            self.data.add(UserCSV(person))
        else:
            user = User.objects.get_user(person)
            if user.provisioned_date is None:
                if (self.data.add(UserCSV(person)) and user.queue_id is None):
                    user.queue_id = self.queue_id
                    user.save()
        return True

    def add_teacher_enrollment_data(self, section, person, status='active'):
        """
        Generates one teacher enrollment for the passed section and person.
        """
        if self.add_user_data_for_person(person):
            self.data.add(EnrollmentCSV(
                section=section, instructor=person, status=status))

    def add_student_enrollment_data(self, registration):
        """
        Generates one student enrollment for the passed registration.
        """
        if self.add_user_data_for_person(registration.person):
            self.data.add(EnrollmentCSV(registration=registration))

    def add_group_enrollment_data(self, login_id, section_id, role, status):
        """
        Generates one enrollment for the passed group member.
        """
        try:
            person = get_person_by_netid(login_id)
            if self.add_user_data_for_person(person):
                self.data.add(EnrollmentCSV(
                    section_id=section_id, person=person, role=role,
                    status=status))

        except InvalidLoginIdException:
            try:
                person = get_person_by_gmail_id(login_id)
                if status == ENROLLMENT_ACTIVE:
                    self.data.add(UserCSV(person))

                self.data.add(EnrollmentCSV(
                    section_id=section_id, person=person, role=role,
                    status=status))
            except InvalidLoginIdException as ex:
                self.logger.info("Skip group member {}: {}".format(
                    login_id, ex))

    def add_registrations_by_section(self, section):
        try:
            for registration in get_registrations_by_section(section):
                self.add_student_enrollment_data(registration)

        except DataFailureException as ex:
            self.logger.info("Skip enrollments for section {}: {}".format(
                section.section_label(), ex))

    def get_section_resource_by_id(self, section_id):
        """
        Fetch the section resource for the passed section ID, and add to queue.
        """
        try:
            section = get_section_by_id(section_id)
            Course.objects.add_to_queue(section, self.queue_id)
            return section

        except (ValueError, CoursePolicyException, DataFailureException) as ex:
            Course.objects.remove_from_queue(section_id, ex)
            self.logger.info("Skip section {}: {}".format(section_id, ex))
            raise
