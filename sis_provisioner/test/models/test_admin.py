# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.conf import settings
from django.test import TestCase, override_settings
from django.db.models.query import QuerySet
from django.utils.timezone import utc
from sis_provisioner.models.admin import Admin
from sis_provisioner.exceptions import AccountPolicyException
from sis_provisioner.test.models.test_account import create_account
from uw_canvas.utilities import fdao_canvas_override
from uw_canvas.admins import Admins as CanvasAdmins
from datetime import datetime, timedelta
import binascii
import os
import copy

ACCOUNT_SIS_ID = 'uwcourse:seattle:nursing:nurs'
ACCOUNT_ID = '789'


def create_admin(
        net_id, account, role='accountadmin',
        reg_id=binascii.b2a_hex(os.urandom(16)).upper()):
    admin = Admin(net_id=net_id, reg_id=reg_id, account=account, role=role)
    admin.save()
    return admin


@override_settings(RESTCLIENTS_CANVAS_ACCOUNT_ID='1',
                   RESTCLIENTS_CANVAS_HOST='http://canvas.edu')
class AdminModelTest(TestCase):
    def setUp(self):
        self.account1 = create_account(1, 'test1')
        self.account2 = create_account(2, 'test2')

    def test_add_admin(self):
        kwargs = {'net_id': 'javerage',
                  'reg_id': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1',
                  'account_sis_id': 'test1',
                  'canvas_id': 1,
                  'role': 'accountadmin'}

        admin = Admin.objects.add_admin(**kwargs)
        original_pk = admin.pk
        self.assertEqual(admin.net_id, 'javerage')
        self.assertEqual(admin.reg_id, 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1')
        self.assertEqual(admin.account.sis_id, 'test1')
        self.assertEqual(admin.account.canvas_id, 1)
        self.assertEqual(admin.role, 'accountadmin')
        self.assertEqual(admin.is_deleted, None)
        self.assertEqual(admin.deleted_date, None)
        self.assertEqual(admin.queue_id, None)

        admin.is_deleted = True
        admin.deleted_date = datetime.utcnow().replace(tzinfo=utc)
        admin.save()

        # add_admin should reset is_deleted
        admin = Admin.objects.add_admin(queue_id=123, **kwargs)
        self.assertEqual(admin.pk, original_pk)
        self.assertEqual(admin.is_deleted, None)
        self.assertEqual(admin.deleted_date, None)
        self.assertEqual(admin.queue_id, 123)

    def test_add_admin_missing_account_id(self):
        kwargs = {'net_id': 'javerage',
                  'reg_id': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1',
                  'account_sis_id': None,
                  'canvas_id': 1,
                  'role': 'accountadmin'}

        admin = Admin.objects.add_admin(**kwargs)
        self.assertEqual(admin.account.canvas_id, 1)
        self.assertEqual(admin.account.sis_id, 'test1')

        kwargs = {'net_id': 'javerage',
                  'reg_id': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1',
                  'account_sis_id': None,
                  'canvas_id': 33,
                  'role': 'accountadmin'}

        self.assertRaises(
            AccountPolicyException, Admin.objects.add_admin, **kwargs)

    def test_add_admin_missing_canvas_id(self):
        kwargs = {'net_id': 'javerage',
                  'reg_id': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1',
                  'account_sis_id': 'test2',
                  'canvas_id': None,
                  'role': 'accountadmin'}

        admin = Admin.objects.add_admin(**kwargs)
        self.assertEqual(admin.account.canvas_id, 2)
        self.assertEqual(admin.account.sis_id, 'test2')

        kwargs = {'net_id': 'javerage',
                  'reg_id': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1',
                  'account_sis_id': 'test33',
                  'canvas_id': None,
                  'role': 'accountadmin'}

        self.assertRaises(
            AccountPolicyException, Admin.objects.add_admin, **kwargs)

    def test_is_account_admin(self):
        self.assertEqual(Admin.objects.is_account_admin('javerage'), False)

        admin = create_admin('javerage', self.account2)
        self.assertEqual(Admin.objects.is_account_admin('javerage'), False)

        admin.is_deleted = True
        admin.deleted_date = datetime.utcnow().replace(tzinfo=utc)
        admin.save()

        self.assertEqual(Admin.objects.is_account_admin('javerage'), False)

        admin = create_admin('javerage', self.account1)
        self.assertEqual(Admin.objects.is_account_admin('javerage'), True)

    def test_has_role(self):
        self.assertEqual(Admin.objects.has_role('javerage', 'support'), False)

        admin = create_admin('javerage', self.account2, role='support')
        self.assertEqual(Admin.objects.has_role('javerage', 'support'), True)

        self.account2.is_deleted = True
        self.account2.save()

        # Admin still has role, but on deleted account
        self.assertEqual(Admin.objects.has_role('javerage', 'support'), False)

    def test_find_by_account(self):
        admin1 = create_admin('javerage', self.account1)
        admin2 = create_admin('jsmith', self.account2)
        admin3 = create_admin('jjones', self.account2)

        r = Admin.objects.find_by_account()
        self.assertEqual(len(r), 3)

        r = Admin.objects.find_by_account(account=self.account2)
        self.assertEqual(len(r), 2)

        admin2.is_deleted = True
        admin2.save()

        r = Admin.objects.find_by_account(account=self.account2)
        self.assertEqual(len(r), 2)

        r = Admin.objects.find_by_account(account=self.account2,
                                          is_deleted=True)
        self.assertEqual(len(r), 1)

    def test_start_reconcile(self):
        create_admin('javerage', self.account1)
        create_admin('jsmith', self.account2)

        imp = Admin.objects.queue_all()

        Admin.objects.start_reconcile(queue_id=imp.pk)

        deleted = Admin.objects.filter(
            is_deleted=True, deleted_date=None, queue_id=imp.pk)
        self.assertEqual(len(deleted), 2)

    def test_finish_reconcile(self):
        create_admin('javerage', self.account1)
        create_admin('jsmith', self.account2)

        imp = Admin.objects.queue_all()

        Admin.objects.start_reconcile(queue_id=imp.pk)
        Admin.objects.finish_reconcile(queue_id=imp.pk)

        deleted = Admin.objects.filter(
            is_deleted=True, is_deleted__isnull=False, queue_id=imp.pk)
        self.assertEqual(len(deleted), 2)

        Admin.objects.start_reconcile(queue_id=imp.pk)

        Admin.objects.queued(imp.pk).update(
            deleted_date=(datetime.utcnow() - timedelta(days=100)).replace(
                tzinfo=utc))

        Admin.objects.finish_reconcile(queue_id=imp.pk)

        admins = Admin.objects.filter(queue_id=imp.pk)
        self.assertEqual(len(admins), 0)

    def test_json_data(self):
        json = create_admin('javerage', self.account2).json_data()
        self.assertEqual(json['account']['sis_id'], 'test2')
        self.assertEqual(json['account']['canvas_url'],
                         'http://canvas.edu/accounts/2')
        self.assertEqual(json['account']['canvas_id'], 2)
        self.assertEqual(json['is_deleted'], False)
        self.assertEqual(json['queue_id'], None)
        self.assertEqual(json['provisioned_date'], '')
        self.assertEqual(json['role'], 'accountadmin')
        self.assertEqual(json['net_id'], 'javerage')


@fdao_canvas_override
@override_settings(
    RESTCLIENTS_CANVAS_ACCOUNT_ID='123',
    ASTRA_ROLE_MAPPING={
        'accountadmin': 'AccountAdmin',
        'support': 'Support',
        'subaccountadmin': 'Sub Account Admin'},
    ANCILLARY_CANVAS_ROLES={'support': {'account': 'root',
                                        'canvas_role': 'Masquerader'}})
class AdminVerificationTest(TestCase):
    def setUp(self):
        account = create_account(ACCOUNT_ID, ACCOUNT_SIS_ID)
        create_admin('admin1', account, role='accountadmin')
        create_admin('admin2', account, role='accountadmin')
        create_admin('admin3', account, role='accountadmin')
        create_admin('admin4', account, role='subaccountadmin')
        create_admin('admin5', account, role='support')

        self.canvas_admins = {}
        for admin in CanvasAdmins().get_admins_by_sis_id(ACCOUNT_SIS_ID):
            self.canvas_admins[admin.user.login_id] = admin

    def test_verify_canvas_admin(self):
        # Valid admins
        self.assertTrue(Admin.objects.verify_canvas_admin(
            self.canvas_admins['admin1'], ACCOUNT_ID))
        self.assertTrue(Admin.objects.verify_canvas_admin(
            self.canvas_admins['admin4'], ACCOUNT_ID))
        self.assertTrue(Admin.objects.verify_canvas_admin(
            self.canvas_admins['admin5'], ACCOUNT_ID))

        # Invalid admins
        self.assertFalse(Admin.objects.verify_canvas_admin(
            self.canvas_admins['admin1'], '345'))
        self.assertFalse(Admin.objects.verify_canvas_admin(
            self.canvas_admins['admin11'], ACCOUNT_ID))

        # Valid ancillary roles
        admin_5 = copy.deepcopy(self.canvas_admins['admin5'])
        admin_5.role = 'Masquerader'
        self.assertTrue(Admin.objects.verify_canvas_admin(
            admin_5, settings.RESTCLIENTS_CANVAS_ACCOUNT_ID))

        # Invalid ancillary roles
        self.assertFalse(Admin.objects.verify_canvas_admin(
            admin_5, ACCOUNT_ID))

        admin_4 = copy.deepcopy(self.canvas_admins['admin4'])
        admin_4.role = 'Masquerader'
        self.assertFalse(Admin.objects.verify_canvas_admin(
            admin_4, settings.RESTCLIENTS_CANVAS_ACCOUNT_ID))
