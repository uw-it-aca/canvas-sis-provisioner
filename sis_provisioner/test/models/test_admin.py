from django.test import TestCase, override_settings
from django.db.models.query import QuerySet
from django.utils.timezone import utc
from sis_provisioner.test import create_admin
from sis_provisioner.models import Admin
from datetime import datetime, timedelta


@override_settings(RESTCLIENTS_CANVAS_ACCOUNT_ID='123',
                   RESTCLIENTS_CANVAS_HOST='http://canvas.edu')
class AdminModelTest(TestCase):
    def test_add_admin(self):
        kwargs = {'net_id': 'javerage',
                  'reg_id': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1',
                  'account_id': 'test',
                  'canvas_id': 1,
                  'role': 'accountadmin'}

        admin = Admin.objects.add_admin(**kwargs)
        original_pk = admin.pk
        self.assertEqual(admin.net_id, 'javerage')
        self.assertEqual(admin.reg_id, 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1')
        self.assertEqual(admin.account_id, 'test')
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
