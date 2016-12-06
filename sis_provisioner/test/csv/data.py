from django.test import TestCase
from restclients.pws import PWS
from restclients.sws.registration import get_all_registrations_by_section
from sis_provisioner.models import Curriculum
from sis_provisioner.dao.course import get_section_by_label
from sis_provisioner.csv.data import Collector
from sis_provisioner.csv.format import *


class CSVDataTest(TestCase):
    def test_accounts(self):
        formatter = AccountCSV('account_id', 'parent_id', Curriculum())

        csv = Collector()
        self.assertEquals(len(csv.accounts), 0)
        self.assertEquals(csv.add(formatter), True)
        self.assertEquals(len(csv.accounts), 1)
        self.assertEquals(csv.add(formatter), False)

    def test_terms(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            section = get_section_by_label('2013,summer,TRAIN,101/A')
            formatter = TermCSV(section)

            csv = Collector()
            self.assertEquals(len(csv.terms), 0)
            self.assertEquals(csv.add(formatter), True)
            self.assertEquals(len(csv.terms), 1)
            self.assertEquals(csv.add(formatter), False)

    def test_courses(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File',
                LMS_OWNERSHIP_SUBACCOUNT={'PCE_NONE': 'pce_none_account'}):

            section = get_section_by_label('2013,spring,TRAIN,101/A')
            section.course_campus = 'PCE'
            formatter = CourseCSV(section=section)

            csv = Collector()
            self.assertEquals(len(csv.courses), 0)
            self.assertEquals(csv.add(formatter), True)
            self.assertEquals(len(csv.courses), 1)
            self.assertEquals(csv.add(formatter), False)

    def test_sections(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            section = get_section_by_label('2013,spring,TRAIN,101/A')
            formatter = SectionCSV(section=section)

            csv = Collector()
            self.assertEquals(len(csv.sections), 0)
            self.assertEquals(csv.add(formatter), True)
            self.assertEquals(len(csv.sections), 1)
            self.assertEquals(csv.add(formatter), False)
            self.assertEquals(csv.add(SectionCSV(section_id='abc', course_id='abc',
                name='abc', status='active')), True)
            self.assertEquals(len(csv.sections), 2)

    def test_enrollments(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            user = PWS().get_person_by_netid('javerage')

            csv = Collector()
            self.assertEquals(len(csv.enrollments), 0)
            self.assertEquals(csv.add(EnrollmentCSV(section_id='abc', person=user,
                role='Student', status='active')), True)
            self.assertEquals(len(csv.enrollments), 1)

            section = get_section_by_label('2013,winter,DROP_T,100/B')

            for registration in get_all_registrations_by_section(section):
                self.assertEquals(csv.add(EnrollmentCSV(registration=registration)), True)

            section = get_section_by_label('2013,spring,TRAIN,101/A')

            for user in section.get_instructors():
                self.assertEquals(csv.add(EnrollmentCSV(section=section,
                    instructor=user, status='active')), True)

            self.assertEquals(len(csv.enrollments), 4)

    def test_xlists(self):
        csv = Collector()
        self.assertEquals(len(csv.xlists), 0)
        self.assertEquals(csv.add(XlistCSV('abc', 'def')), True)
        self.assertEquals(len(csv.xlists), 1)

    def test_users(self):
        with self.settings(
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):
            
            user = PWS().get_person_by_netid('javerage')

            csv = Collector()
            self.assertEquals(len(csv.users), 0)
            self.assertEquals(csv.add(UserCSV(user, 'active')), True)
            self.assertEquals(len(csv.users), 1)
            self.assertEquals(csv.add(UserCSV(user, 'active')), False)

    def test_write_files(self):
        pass
