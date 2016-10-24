from django.test import TestCase
from restclients.models.sws import Campus, College, Department, Curriculum
from sis_provisioner.dao import titleize
from sis_provisioner.dao.account import *
from sis_provisioner.exceptions import AccountPolicyException


class AccountPolicyTest(TestCase):
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

    def test_titleize(self):
        self.assertRaises(TypeError, titleize, None)
        self.assertEquals(titleize(123), '123')
        self.assertEquals(titleize(''), '')
        self.assertEquals(titleize('abc'), 'Abc')
        self.assertEquals(titleize('ABC'), 'Abc')
        self.assertEquals(titleize('abc def'), 'Abc Def')
        self.assertEquals(titleize('abc:def'), 'Abc:Def')
        self.assertEquals(titleize('abc-def'), 'Abc-Def')
        self.assertEquals(titleize('abc.def'), 'Abc.Def')
        self.assertEquals(titleize('abc&def'), 'Abc&Def')
        self.assertEquals(titleize('UW abc'), 'UW Abc')
        self.assertEquals(titleize('ABC I'), 'Abc I')
        self.assertEquals(titleize('ABC II'), 'Abc II')
        self.assertEquals(titleize('ABC III'), 'Abc III')
        self.assertEquals(titleize('ABC IV'), 'Abc IV')
        self.assertEquals(titleize('abc (DEF)'), 'Abc (Def)')
