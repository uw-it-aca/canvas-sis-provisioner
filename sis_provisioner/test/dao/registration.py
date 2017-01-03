from django.test import TestCase
from django.conf import settings
from restclients.models.sws import Registration
from sis_provisioner.dao.course import get_section_by_label
from sis_provisioner.dao.registration import *
from datetime import datetime


class RegistrationsBySectionTest(TestCase):
    def test_get_registrations_by_section(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            section = get_section_by_label('2013,winter,DROP_T,100/B')
            registrations = get_registrations_by_section(section)

            self.assertEquals(len(registrations), 2)


class EnrollmentStatusForRegistrationTest(TestCase):
    def test_status_from_registration(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            section = get_section_by_label('2013,winter,DROP_T,100/B')

            reg = Registration(section=section,
                               is_active=True)
            self.assertEquals(enrollment_status_from_registration(reg), 'active')

            reg = Registration(section=section,
                               is_active=False,
                               request_date=section.term.grade_submission_deadline)
            self.assertEquals(enrollment_status_from_registration(reg), 'inactive')

            reg = Registration(section=section,
                               is_active=False,
                               request_status='Added to Standby')
            self.assertEquals(enrollment_status_from_registration(reg), 'active')

            reg = Registration(section=section,
                               is_active=False,
                               request_status='PENDING ADDED TO CLASS')
            self.assertEquals(enrollment_status_from_registration(reg), 'active')

            # request_date equals term.first_day bod
            reg = Registration(section=section,
                               is_active=False,
                               request_date=section.term.get_bod_first_day())
            self.assertEquals(enrollment_status_from_registration(reg), 'deleted')

            # request_date equals term.census_day bod
            reg = Registration(section=section,
                               is_active=False,
                               request_date = datetime(section.term.census_day.year,
                                                       section.term.census_day.month,
                                                       section.term.census_day.day))
            self.assertEquals(enrollment_status_from_registration(reg), 'deleted')
