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
    def test_with_section(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File',
                LMS_OWNERSHIP_SUBACCOUNT={'PCE_NONE': 'pce_none_account'}):

            section = get_section_by_label('2013,spring,TRAIN,101/A')
            self.assertRaises(CoursePolicyException, CourseCSV, section=section)

            section.course_campus = 'PCE'
            self.assertEquals(str(CourseCSV(section=section)), '2013-spring-TRAIN-101-A,TRAIN 101 A,TRAIN 101 A: Intro Train,pce_none_account,2013-spring,active,,\n')

    def test_with_kwargs(self):
        data = {'course_id': '2013-spring-TRAIN-101-A',
                'short_name': 'TRAIN 101 A',
                'long_name': 'TRAIN 101 A: Intro Train',
                'account_id': None,
                'term_id': '2013-spring',
                'status': 'deleted'}

        self.assertEquals(str(CourseCSV(**data)), '2013-spring-TRAIN-101-A,TRAIN 101 A,TRAIN 101 A: Intro Train,,2013-spring,deleted,,\n')

        self.assertRaises(KeyError, CourseCSV, **{})


class SectionCSVTest(TestCase):
    def test_with_section(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            section = get_section_by_label('2013,spring,TRAIN,101/A')

            self.assertEquals(str(SectionCSV(section=section)), '2013-spring-TRAIN-101-A--,2013-spring-TRAIN-101-A,TRAIN 101 A,active,,\n')

    def test_with_kwargs(self):
        data = {'section_id': '2013-spring-TRAIN-101-A--',
                'course_id': '2013-spring-TRAIN-101-A',
                'name': 'TRAIN 101 A'}
        self.assertEquals(str(SectionCSV(**data)), '2013-spring-TRAIN-101-A--,2013-spring-TRAIN-101-A,TRAIN 101 A,active,,\n')


        data = {'section_id': 'abc-groups',
                'course_id': 'abc',
                'name': 'UW Group members'}

        self.assertEquals(str(SectionCSV(**data)), 'abc-groups,abc,UW Group members,active,,\n')
        data['status'] = 'deleted'
        self.assertEquals(str(SectionCSV(**data)), 'abc-groups,abc,UW Group members,deleted,,\n')


class EnrollmentCSVTest(TestCase):
    def test_with_kwargs(self):
        with self.settings(
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            user = PWS().get_person_by_netid('javerage')

            data = {'section_id': 'abc',
                    'role': 'Student',
                    'person': user}

            # No status
            self.assertRaises(EnrollmentPolicyException, EnrollmentCSV, **data)

            # Invalid status
            data['status'] = 'status'
            self.assertRaises(EnrollmentPolicyException, EnrollmentCSV, **data)

    
            data['status'] = 'active'
            self.assertEquals(str(EnrollmentCSV(**data)), ',,9136CCB8F66711D5BE060004AC494FFE,Student,,abc,active,\n')
            
            data['status'] = 'deleted'
            self.assertEquals(str(EnrollmentCSV(**data)), ',,9136CCB8F66711D5BE060004AC494FFE,Student,,abc,deleted,\n')

    def test_student_enrollment_csv(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            section = get_section_by_label('2013,winter,DROP_T,100/B')

            for registration in get_all_registrations_by_section(section):
                self.assertEquals(str(EnrollmentCSV(registration=registration)), ',,%s,Student,,2013-winter-DROP_T-100-B--,active,\n' % registration.person.uwregid)


    def test_instructor_enrollment_csv(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            section = get_section_by_label('2013,spring,TRAIN,101/A')

            for user in section.get_instructors():
                self.assertEquals(str(EnrollmentCSV(section=section, instructor=user, status='active')), ',,%s,Teacher,,2013-spring-TRAIN-101-A--,active,\n' % user.uwregid)


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
