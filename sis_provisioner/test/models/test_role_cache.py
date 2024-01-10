# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.test import TestCase
from sis_provisioner.models.account import Account
from sis_provisioner.models.admin import RoleCache
import mock


class RoleCacheModelTest(TestCase):
    def setUp(self):
        account = Account(canvas_id='12345', sis_id='test-account',
                          account_name='Test',
                          account_short_name='',
                          account_type=Account.SDB_TYPE)
        account.save()

    @mock.patch('sis_provisioner.models.admin.get_account_role_data')
    def test_check_roles_for_account(self, mock_fn):
        mock_fn.return_value = '[test]'
        self.assertFalse(RoleCache.objects.check_roles_for_account('12345'))
        self.assertFalse(RoleCache.objects.check_roles_for_account('12345'))

        mock_fn.return_value = '[test, test2]'
        self.assertTrue(RoleCache.objects.check_roles_for_account('12345'))
        self.assertFalse(RoleCache.objects.check_roles_for_account('12345'))
