# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.test import TestCase, override_settings
from sis_provisioner.dao.course import get_section_by_label
from sis_provisioner.dao.account import *
from sis_provisioner.exceptions import AccountPolicyException
from uw_sws.models import Campus, College, Department, Curriculum
from uw_sws.util import fdao_sws_override
from uw_pws.util import fdao_pws_override


@fdao_sws_override
class AccountPolicyTest(TestCase):
    def test_valid_canvas_account_id(self):
        self.assertEquals(valid_canvas_account_id(12345), None)
        self.assertEquals(valid_canvas_account_id('0'), None)
        self.assertEquals(valid_canvas_account_id('1111111111'), None)
        self.assertRaises(
            AccountPolicyException, valid_canvas_account_id, None)
        self.assertRaises(
            AccountPolicyException, valid_canvas_account_id, 'abc')
        self.assertRaises(
            AccountPolicyException, valid_canvas_account_id, '1234z')

    @override_settings(SIS_IMPORT_ROOT_ACCOUNT_ID='sis_root')
    def test_valid_account_sis_id(self):
        self.assertEquals(valid_account_sis_id('sis_root'), None)
        self.assertEquals(valid_account_sis_id('sis_root:courses'), None)
        self.assertEquals(valid_account_sis_id('sis_root:abc:def'), None)

        self.assertRaises(
            AccountPolicyException, valid_account_sis_id, 'course')
        self.assertRaises(
            AccountPolicyException, valid_account_sis_id, 'sis_root:')
        self.assertRaises(
            AccountPolicyException, valid_account_sis_id, 'sis_root:%')
        self.assertRaises(
            AccountPolicyException, valid_account_sis_id, None)

    @override_settings(SIS_IMPORT_ROOT_ACCOUNT_ID='sis_root')
    def test_valid_academic_account_sis_id(self):
        self.assertEquals(
            valid_academic_account_sis_id('sis_root:seattle'), None)
        self.assertEquals(
            valid_academic_account_sis_id('sis_root:tacoma:abc'), None)

        self.assertRaises(
            AccountPolicyException,
            valid_academic_account_sis_id, 'sis_root')
        self.assertRaises(
            AccountPolicyException,
            valid_academic_account_sis_id, 'sis_root:uweo')

    def test_adhoc_account_sis_id(self):
        self.assertEquals(adhoc_account_sis_id('12345'), 'account_12345')
        self.assertEquals(adhoc_account_sis_id('0'), 'account_0')
        self.assertRaises(AccountPolicyException, adhoc_account_sis_id, None)
        self.assertRaises(AccountPolicyException, adhoc_account_sis_id, 'abc')
        self.assertRaises(AccountPolicyException, adhoc_account_sis_id, '')

    def test_account_sis_id(self):
        self.assertEquals(account_sis_id(['abc']), 'abc')
        self.assertEquals(account_sis_id(['ab&c']), 'ab&c')
        self.assertEquals(account_sis_id(['a b c']), 'a-b-c')
        self.assertEquals(account_sis_id(['a:b:c']), 'a-b-c')
        self.assertEquals(account_sis_id(['a-b-c']), 'a-b-c')

        accounts = ['abc', 'def', 'ghi']
        self.assertEquals(account_sis_id(accounts), 'abc:def:ghi')

        accounts = [' abc ', 'def ', ' ghi']
        self.assertEquals(account_sis_id(accounts), 'abc:def:ghi')

        accounts = ['abc', 'de:f', 'g:hi']
        self.assertEquals(account_sis_id(accounts), 'abc:de-f:g-hi')

        accounts = ['ABC', 'DEF', 'GHI']
        self.assertEquals(account_sis_id(accounts), 'abc:def:ghi')

        accounts = [123, 456, 789]
        self.assertRaises(AccountPolicyException, account_sis_id, accounts)

        accounts = ['', 'def', 'ghi']
        self.assertRaises(AccountPolicyException, account_sis_id, accounts)

        accounts = ['abc', None, 'ghi']
        self.assertRaises(AccountPolicyException, account_sis_id, accounts)

    def test_account_name(self):
        campus = Campus(full_name='Campus Name')
        college = College(full_name='College Name')
        dept = Department(full_name='Department Name')
        curriculum = Curriculum(full_name='Curriculum Name',
                                label='ABC')

        self.assertEquals(account_name(campus), campus.full_name)
        self.assertEquals(account_name(college), college.full_name)
        self.assertEquals(account_name(dept), dept.full_name)
        self.assertEquals(account_name(curriculum), 'Curriculum Name [ABC]')

        campus.full_name = 'uw campus'
        self.assertEquals(account_name(campus), 'UW Campus')

        curriculum.full_name = 'Name UW Bothell Campus'
        self.assertEquals(account_name(curriculum), 'Name [ABC]')

    @override_settings(LMS_OWNERSHIP_SUBACCOUNT={
            'PCE_OL': 'uwcourse:uweo:ol-managed',
            'PCE_NONE': 'uwcourse:uweo:noncredit-campus-managed'})
    def test_account_id_for_section(self):
        section = get_section_by_label('2013,spring,TRAIN,101/A')

        section.lms_ownership = 'Seattle'
        section.lms_ownership = None
        self.assertRaises(AccountPolicyException,
                          account_id_for_section, section)

        section.course_campus = 'PCE'
        self.assertEquals(account_id_for_section(section),
                          'uwcourse:uweo:noncredit-campus-managed')

        section.lms_ownership = 'PCE_OL'
        self.assertEquals(account_id_for_section(section),
                          'uwcourse:uweo:ol-managed')


@fdao_sws_override
class CampusCollegeDepartmentTest(TestCase):
    def test_get_campus_by_label(self):
        campus = get_campus_by_label('Seattle')
        self.assertEqual(campus.label, 'SEATTLE')

        campus = get_campus_by_label('NoMatch')
        self.assertEqual(campus, None)

    def test_get_college_by_label(self):
        campus = get_campus_by_label('Seattle')

        college = get_college_by_label(campus, 'Med')
        self.assertEqual(college.label, 'MED')

        college = get_college_by_label(campus, 'NoMatch')
        self.assertEqual(college, None)

    def test_get_department_by_label(self):
        campus = get_campus_by_label('Seattle')
        college = get_college_by_label(campus, 'Med')

        department = get_department_by_label(college, 'Anest')
        self.assertEqual(department.label, 'ANEST')

        department = get_department_by_label(college, 'NoMatch')
        self.assertEqual(department, None)
