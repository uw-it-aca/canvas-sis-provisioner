# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.test import TestCase, override_settings
from uw_pws import PWS
from uw_pws.util import fdao_pws_override
from uw_sws.util import fdao_sws_override
from sis_provisioner.models.account import Curriculum
from sis_provisioner.dao.course import (
    get_section_by_label, get_registrations_by_section)
from sis_provisioner.exceptions import (
    CoursePolicyException, EnrollmentPolicyException, AccountPolicyException)
from sis_provisioner.csv.format import *


class CSVHeaderTest(TestCase):
    def test_init(self):
        csv_format = CSVFormat()
        self.assertEqual(csv_format.key, None)
        self.assertEqual(csv_format.data, [])

    def test_csv_headers(self):
        self.assertEquals(
            str(AccountHeader()), 'account_id,parent_account_id,name,status\n')
        self.assertEquals(
            str(AdminHeader()), 'user_id,account_id,role,status\n')
        self.assertEquals(
            str(TermHeader()), 'term_id,name,status,start_date,end_date\n')
        self.assertEquals(
            str(CourseHeader()), (
                'course_id,short_name,long_name,account_id,term_id,status,'
                'start_date,end_date\n'))
        self.assertEquals(
            str(SectionHeader()),
            'section_id,course_id,name,status,start_date,end_date\n')
        self.assertEquals(
            str(EnrollmentHeader()), (
                'course_id,root_account,user_id,role,role_id,section_id,'
                'status,associated_user_id\n'))
        self.assertEquals(
            str(UserHeader()), (
                'user_id,login_id,password,first_name,last_name,full_name,'
                'sortable_name,short_name,email,pronouns,status\n'))
        self.assertEquals(
            str(XlistHeader()), 'xlist_course_id,section_id,status\n')


class AccountCSVTest(TestCase):
    def test_account_csv(self):
        context = Curriculum(full_name='CSV Test')
        self.assertEquals(
            str(AccountCSV('abc', 'def', context, 'active')),
            'abc,def,Csv Test,active\n')


@fdao_sws_override
@fdao_pws_override
class TermCSVTest(TestCase):
    def test_term_csv(self):
        section = get_section_by_label('2013,summer,TRAIN,101/A')

        self.assertEquals(
            str(TermCSV(section, 'active')), (
                '2013-summer,Summer 2013,active,2013-06-24T00:00:00-0800,'
                '2013-08-28T00:00:00-0800\n'))
        self.assertEquals(
            str(TermCSV(section, 'deleted')), (
                '2013-summer,Summer 2013,deleted,2013-06-24T00:00:00-0800,'
                '2013-08-28T00:00:00-0800\n'))
        self.assertEquals(
            str(TermCSV(section)), (
                '2013-summer,Summer 2013,active,2013-06-24T00:00:00-0800,'
                '2013-08-28T00:00:00-0800\n'))


@fdao_sws_override
@fdao_pws_override
class CourseCSVTest(TestCase):
    @override_settings(
        LMS_OWNERSHIP_SUBACCOUNT={'PCE_NONE': 'pce_none_account'})
    def test_with_section(self):
        section = get_section_by_label('2013,spring,TRAIN,101/A')
        self.assertRaises(
            AccountPolicyException, CourseCSV, section=section)

        section.course_campus = 'PCE'
        self.assertEquals(
            str(CourseCSV(section=section)), (
                '2013-spring-TRAIN-101-A,TRAIN 101 A,TRAIN 101 A Sp 13: '
                'Intro Train,pce_none_account,2013-spring,active,,\n'))

    def test_with_kwargs(self):
        data = {'course_id': '2013-spring-TRAIN-101-A',
                'short_name': 'TRAIN 101 A',
                'long_name': 'TRAIN 101 A Sp 13: Intro Train',
                'account_id': None,
                'term_id': '2013-spring',
                'status': 'deleted'}

        self.assertEquals(
            str(CourseCSV(**data)), (
                '2013-spring-TRAIN-101-A,TRAIN 101 A,TRAIN 101 A Sp 13: '
                'Intro Train,,2013-spring,deleted,,\n'))

        self.assertRaises(KeyError, CourseCSV, **{})


@fdao_sws_override
@fdao_pws_override
class SectionCSVTest(TestCase):
    def test_with_section(self):
        section = get_section_by_label('2013,spring,TRAIN,101/A')

        self.assertEquals(
            str(SectionCSV(section=section)), (
                '2013-spring-TRAIN-101-A--,2013-spring-TRAIN-101-A,'
                'TRAIN 101 A,active,,\n'))

    def test_with_kwargs(self):
        data = {'section_id': '2013-spring-TRAIN-101-A--',
                'course_id': '2013-spring-TRAIN-101-A',
                'name': 'TRAIN 101 A'}
        self.assertEquals(
            str(SectionCSV(**data)), (
                '2013-spring-TRAIN-101-A--,2013-spring-TRAIN-101-A,'
                'TRAIN 101 A,active,,\n'))

        data = {'section_id': 'abc-groups',
                'course_id': 'abc',
                'name': 'UW Group members'}

        self.assertEquals(
            str(SectionCSV(**data)),
            'abc-groups,abc,UW Group members,active,,\n')
        data['status'] = 'deleted'
        self.assertEquals(
            str(SectionCSV(**data)),
            'abc-groups,abc,UW Group members,deleted,,\n')


@fdao_sws_override
@fdao_pws_override
class EnrollmentCSVTest(TestCase):
    def test_with_kwargs(self):
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
        self.assertEquals(
            str(EnrollmentCSV(**data)),
            ',,9136CCB8F66711D5BE060004AC494FFE,student,,abc,active,\n')

        data['status'] = 'deleted'
        self.assertEquals(
            str(EnrollmentCSV(**data)),
            ',,9136CCB8F66711D5BE060004AC494FFE,student,,abc,deleted,\n')

        data = {'status': 'active',
                'role': 'Student',
                'person': user}

        # No course or section
        self.assertRaises(EnrollmentPolicyException, EnrollmentCSV, **data)

        data['course_id'] = 'abc'
        self.assertEquals(
            str(EnrollmentCSV(**data)),
            'abc,,9136CCB8F66711D5BE060004AC494FFE,student,,,active,\n')

        data['section_id'] = 'abc--'
        self.assertEquals(
            str(EnrollmentCSV(**data)),
            'abc,,9136CCB8F66711D5BE060004AC494FFE,student,,abc--,active,\n')

        # Missing role
        data['role'] = ''
        self.assertRaises(EnrollmentPolicyException, EnrollmentCSV, **data)

        data['role'] = 'TaEnrollment'
        self.assertEquals(
            str(EnrollmentCSV(**data)),
            'abc,,9136CCB8F66711D5BE060004AC494FFE,ta,,abc--,active,\n')

        data['role'] = 'Librarian'  # Known custom role
        self.assertEquals(
            str(EnrollmentCSV(**data)),
            'abc,,9136CCB8F66711D5BE060004AC494FFE,Librarian,,abc--,active,\n')

        data['role'] = 'Custom'  # Unknown custom role
        self.assertEquals(
            str(EnrollmentCSV(**data)),
            'abc,,9136CCB8F66711D5BE060004AC494FFE,Custom,,abc--,active,\n')

    def test_student_enrollment_csv(self):
        section = get_section_by_label('2013,winter,DROP_T,100/B')

        registrations = get_registrations_by_section(section)

        self.assertEquals(len(registrations), 2)

        reg0 = registrations[0]
        reg1 = registrations[1]

        self.assertEquals(
            str(EnrollmentCSV(registration=reg0)), (
                ',,260A0DEC95CB11D78BAA000629C31437,student,,'
                '2013-winter-DROP_T-100-B--,active,\n'))
        self.assertEquals(
            str(EnrollmentCSV(registration=reg1)), (
                ',,9136CCB8F66711D5BE060004AC494FFE,student,,'
                '2013-winter-DROP_T-100-B--,active,\n'))

    def test_instructor_enrollment_csv(self):
        section = get_section_by_label('2013,spring,TRAIN,101/A')

        for user in section.get_instructors():
            self.assertEquals(
                str(EnrollmentCSV(
                    section=section, instructor=user, status='active')),
                ',,{},teacher,,2013-spring-TRAIN-101-A--,active,\n'.format(
                    user.uwregid))


@fdao_sws_override
@fdao_pws_override
class UserCSVTest(TestCase):
    def test_user_csv(self):
        user = PWS().get_person_by_netid('javerage')
        self.assertEquals(
            str(UserCSV(user, 'active')), (
                '9136CCB8F66711D5BE060004AC494FFE,javerage,,Jamesy,'
                'McJamesy,,,,javerage@uw.edu,,active\n'))

        user = PWS().get_entity_by_netid('somalt')
        self.assertEquals(
            str(UserCSV(user, 'active')), (
                '605764A811A847E690F107D763A4B32A,somalt,,,,'
                'SOM ACADEMIC LRNG TECHNOLOGY,,,somalt@uw.edu,,active\n'))


class XlistCSVTest(TestCase):
    def test_xlist_csv(self):
        self.assertEquals(
            str(XlistCSV('abc', 'def', 'active')), 'abc,def,active\n')
        self.assertEquals(
            str(XlistCSV('abc', 'def', 'deleted')), 'abc,def,deleted\n')
        self.assertEquals(
            str(XlistCSV('abc', 'def')), 'abc,def,active\n')
