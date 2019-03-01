from django.conf import settings
from django.test import TestCase, override_settings
from django.db.models.query import QuerySet
from django.utils.timezone import utc
from sis_provisioner.models import Admin
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


def create_admin(net_id, account_id='test', role='accountadmin',
                 reg_id=binascii.b2a_hex(os.urandom(16)).upper(),
                 canvas_id=None):
    if canvas_id is None:
        canvas_id = settings.RESTCLIENTS_CANVAS_ACCOUNT_ID

    admin = Admin(net_id=net_id, reg_id=reg_id, account_id=account_id,
                  canvas_id=canvas_id, role=role)
    admin.save()
    return admin


@override_settings(RESTCLIENTS_CANVAS_ACCOUNT_ID='123',
                   RESTCLIENTS_CANVAS_HOST='http://canvas.edu')
class AdminModelTest(TestCase):
    def setUp(self):
        create_account(1, 'test1')
        create_account(2, 'test2')

    def test_add_admin(self):
        kwargs = {'net_id': 'javerage',
                  'reg_id': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1',
                  'account_id': 'test1',
                  'canvas_id': 1,
                  'role': 'accountadmin'}

        admin = Admin.objects.add_admin(**kwargs)
        original_pk = admin.pk
        self.assertEqual(admin.net_id, 'javerage')
        self.assertEqual(admin.reg_id, 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1')
        self.assertEqual(admin.account_id, 'test1')
        self.assertEqual(admin.canvas_id, 1)
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
                  'account_id': None,
                  'canvas_id': 1,
                  'role': 'accountadmin'}

        admin = Admin.objects.add_admin(**kwargs)
        self.assertEqual(admin.canvas_id, 1)
        self.assertEqual(admin.account_id, 'test1')

        kwargs = {'net_id': 'javerage',
                  'reg_id': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1',
                  'account_id': None,
                  'canvas_id': 33,
                  'role': 'accountadmin'}

        self.assertRaises(
            AccountPolicyException, Admin.objects.add_admin, **kwargs)

    def test_add_admin_missing_canvas_id(self):
        kwargs = {'net_id': 'javerage',
                  'reg_id': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1',
                  'account_id': 'test2',
                  'canvas_id': None,
                  'role': 'accountadmin'}

        admin = Admin.objects.add_admin(**kwargs)
        self.assertEqual(admin.canvas_id, 2)
        self.assertEqual(admin.account_id, 'test2')

        kwargs = {'net_id': 'javerage',
                  'reg_id': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1',
                  'account_id': 'test33',
                  'canvas_id': None,
                  'role': 'accountadmin'}

        self.assertRaises(
            AccountPolicyException, Admin.objects.add_admin, **kwargs)

    def test_is_account_admin(self):
        self.assertEqual(Admin.objects.is_account_admin('javerage'), False)

        admin = create_admin('javerage')

        self.assertEqual(Admin.objects.is_account_admin('javerage'), True)

        admin.is_deleted = True
        admin.deleted_date = datetime.utcnow().replace(tzinfo=utc)
        admin.save()

        self.assertEqual(Admin.objects.is_account_admin('javerage'), False)

    def test_start_reconcile(self):
        create_admin('javerage')
        create_admin('jsmith')

        imp = Admin.objects.queue_all()

        Admin.objects.start_reconcile(queue_id=imp.pk)

        deleted = Admin.objects.filter(
            is_deleted=True, deleted_date=None, queue_id=imp.pk)
        self.assertEqual(len(deleted), 2)

    def test_finish_reconcile(self):
        create_admin('javerage')
        create_admin('jsmith')

        imp = Admin.objects.queue_all()

        Admin.objects.start_reconcile(queue_id=imp.pk)
        Admin.objects.finish_reconcile(queue_id=imp.pk)

        deleted = Admin.objects.filter(
            is_deleted=True, is_deleted__isnull=False, queue_id=imp.pk)
        self.assertEqual(len(deleted), 2)

        Admin.objects.start_reconcile(queue_id=imp.pk)

        Admin.objects.queued(imp.pk).update(
            deleted_date=(datetime.utcnow() - timedelta(days=100)))

        Admin.objects.finish_reconcile(queue_id=imp.pk)

        admins = Admin.objects.filter(queue_id=imp.pk)
        self.assertEqual(len(admins), 0)

    def test_json_data(self):
        json = create_admin('javerage').json_data()
        self.assertEqual(json['account_id'], 'test')
        self.assertEqual(json['account_link'],
                         'http://canvas.edu/accounts/123')
        self.assertEqual(json['canvas_id'], '123')
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
    ANCILLARY_CANVAS_ROLES={'Support': {'account': 'root',
                                        'canvas_role': 'Masquerader'}})
class AdminVerificationTest(TestCase):
    def setUp(self):
        create_admin('admin1', account_id=ACCOUNT_SIS_ID,
                     canvas_id=ACCOUNT_ID, role='accountadmin')
        create_admin('admin2', account_id=ACCOUNT_SIS_ID,
                     canvas_id=ACCOUNT_ID, role='accountadmin')
        create_admin('admin3', account_id=ACCOUNT_SIS_ID,
                     canvas_id=ACCOUNT_ID, role='accountadmin')
        create_admin('admin4', account_id=ACCOUNT_SIS_ID,
                     canvas_id=ACCOUNT_ID, role='subaccountadmin')
        create_admin('admin5', account_id=ACCOUNT_SIS_ID,
                     canvas_id=ACCOUNT_ID, role='support')

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
