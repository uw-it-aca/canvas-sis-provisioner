from django.test import TestCase
from django.conf import settings
from sis_provisioner.dao.course import get_section_by_label
from sis_provisioner.dao.account import *
from sis_provisioner.exceptions import AccountPolicyException
from uw_sws.models import Campus, College, Department, Curriculum
from uw_sws.util import fdao_sws_override
from uw_pws.util import fdao_pws_override


@fdao_sws_override
class AccountPolicyTest(TestCase):
    def test_valid_sccount_sis_id(self):
        with self.settings(SIS_IMPORT_ROOT_ACCOUNT_ID='sis_root'):
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

    def test_account_id_for_section(self):
        with self.settings(
                LMS_OWNERSHIP_SUBACCOUNT={
                    'PCE_OL': 'uwcourse:uweo:ol-managed',
                    'PCE_NONE': 'uwcourse:uweo:noncredit-campus-managed'}):

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
