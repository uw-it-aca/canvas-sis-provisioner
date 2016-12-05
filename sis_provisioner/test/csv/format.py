from django.test import TestCase
from restclients.pws import PWS
from restclients.sws.registration import get_all_registrations_by_section
from sis_provisioner.models import Curriculum
from sis_provisioner.dao.course import get_section_by_label
from sis_provisioner.exceptions import (CoursePolicyException,
    EnrollmentPolicyException)
from sis_provisioner.csv.format import *


class CSVHeaderTest(TestCase):
    def test_csv_headers(self):
        self.assertEquals(str(AccountHeader()), 'account_id,parent_account_id,name,status\n')
        self.assertEquals(str(TermHeader()), 'term_id,name,status,start_date,end_date\n')
        self.assertEquals(str(CourseHeader()), 'course_id,short_name,long_name,account_id,term_id,status,start_date,end_date\n')
        self.assertEquals(str(SectionHeader()), 'section_id,course_id,name,status,start_date,end_date\n')
        self.assertEquals(str(EnrollmentHeader()), 'course_id,root_account,user_id,role,role_id,section_id,status,associated_user_id\n')
        self.assertEquals(str(UserHeader()), 'user_id,login_id,password,first_name,last_name,full_name,sortable_name,short_name,email,status\n')
        self.assertEquals(str(XlistHeader()), 'xlist_course_id,section_id,status\n')


class AccountCSVTest(TestCase):
    def test_account_csv(self):
        context = Curriculum(full_name='CSV Test')
        self.assertEquals(str(AccountCSV('abc', 'def', context, 'active')), 'abc,def,Csv Test,active\n')


class TermCSVTest(TestCase):
    def test_term_csv(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            section = get_section_by_label('2013,summer,TRAIN,101/A')

            self.assertEquals(str(TermCSV(section, 'active')), '2013-summer,Summer 2013,active,2013-06-24T00:00:00-0800,2013-08-28T00:00:00-0800\n')
            self.assertEquals(str(TermCSV(section, 'deleted')), '2013-summer,Summer 2013,deleted,2013-06-24T00:00:00-0800,2013-08-28T00:00:00-0800\n')
            self.assertEquals(str(TermCSV(section)), '2013-summer,Summer 2013,active,2013-06-24T00:00:00-0800,2013-08-28T00:00:00-0800\n')


class CourseCSVTest(TestCase):
    def test_course_csv(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File',
                LMS_OWNERSHIP_SUBACCOUNT={'PCE_NONE': 'pce_none_account'}):

            section = get_section_by_label('2013,spring,TRAIN,101/A')
            self.assertRaises(CoursePolicyException, CourseCSV, section)

            section.course_campus = 'PCE'
            self.assertEquals(str(CourseCSV(section)), '2013-spring-TRAIN-101-A,TRAIN 101 A,TRAIN 101 A: Intro Train,pce_none_account,2013-spring,active,,\n')


    def test_canvas_course_csv(self):
        data = {'course_sis_id': '2013-spring-TRAIN-101-A',
                'short_name': 'TRAIN 101 A',
                'long_name': 'TRAIN 101 A: Intro Train',
                'account_sis_id': None,
                'term_sis_id': '2013-spring',
                'status': 'deleted'}

        self.assertEquals(str(CanvasCourseCSV(**data)), '2013-spring-TRAIN-101-A,TRAIN 101 A,TRAIN 101 A: Intro Train,,2013-spring,deleted,,\n')

        self.assertRaises(KeyError, CanvasCourseCSV, **{})


class SectionCSVTest(TestCase):
    def test_section_csv(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            section = get_section_by_label('2013,spring,TRAIN,101/A')

            self.assertEquals(str(SectionCSV(section)), '2013-spring-TRAIN-101-A--,2013-spring-TRAIN-101-A,TRAIN 101 A,active,,\n')


class GroupSectionCSVTest(TestCase):
    def test_group_section_csv(self):
        self.assertEquals(str(GroupSectionCSV('abc', 'active')), 'abc-groups,abc,UW Group members,active,,\n')
        self.assertEquals(str(GroupSectionCSV('abc', 'deleted')), 'abc-groups,abc,UW Group members,deleted,,\n')
        self.assertEquals(str(GroupSectionCSV('abc')), 'abc-groups,abc,UW Group members,active,,\n')


class EnrollmentCSVTest(TestCase):
    def test_enrollment_csv(self):
        with self.settings(
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            user = PWS().get_person_by_netid('javerage')

            self.assertEquals(str(EnrollmentCSV('abc', user, 'Student', 'active')), ',,9136CCB8F66711D5BE060004AC494FFE,Student,,abc,active,\n')
            self.assertEquals(str(EnrollmentCSV('abc', user, 'Student', 'deleted')), ',,9136CCB8F66711D5BE060004AC494FFE,Student,,abc,deleted,\n')

            self.assertRaises(TypeError, EnrollmentCSV, 'abc', user, 'Student')
            self.assertRaises(EnrollmentPolicyException, EnrollmentCSV, 'abc', user, 'Student', 'status')

    def test_student_enrollment_csv(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            section = get_section_by_label('2013,winter,DROP_T,100/B')

            for registration in get_all_registrations_by_section(section):
                self.assertEquals(str(StudentEnrollmentCSV(registration)), ',,%s,Student,,2013-winter-DROP_T-100-B--,active,\n' % registration.person.uwregid)


    def test_instructor_enrollment_csv(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):
            
            section = get_section_by_label('2013,spring,TRAIN,101/A')

            for user in section.get_instructors():
                self.assertEquals(str(InstructorEnrollmentCSV(section, user, 'active')), ',,%s,Teacher,,2013-spring-TRAIN-101-A--,active,\n' % user.uwregid)


class UserCSVTest(TestCase):
    def test_user_csv(self):
        with self.settings(
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            user = PWS().get_person_by_netid('javerage')
            self.assertEquals(str(UserCSV(user, 'active')), '9136CCB8F66711D5BE060004AC494FFE,javerage,,,,James Student,,,javerage@uw.edu,active\n')


class XlistCSVTest(TestCase):
    def test_xlist_csv(self):
        self.assertEquals(str(XlistCSV('abc', 'def', 'active')), 'abc,def,active\n')
        self.assertEquals(str(XlistCSV('abc', 'def', 'deleted')), 'abc,def,deleted\n')
        self.assertEquals(str(XlistCSV('abc', 'def')), 'abc,def,active\n')
