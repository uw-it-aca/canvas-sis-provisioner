from django.test import TestCase, override_settings
from django.db.models.query import QuerySet
from django.utils.timezone import utc
from sis_provisioner.test import create_admin
from sis_provisioner.models import Admin
from sis_provisioner.models.astra import Account
from datetime import datetime, timedelta
import mock


@override_settings(RESTCLIENTS_CANVAS_ACCOUNT_ID='123',
                   RESTCLIENTS_CANVAS_HOST='http://canvas.edu')
class AdminModelTest(TestCase):
    def test_is_account_admin(self):
        self.assertEquals(Admin.objects.is_account_admin('javerage'), False)

        admin = create_admin('javerage')

        self.assertEquals(Admin.objects.is_account_admin('javerage'), True)

        admin.is_deleted = True
        admin.deleted_date = datetime.utcnow().replace(tzinfo=utc)
        admin.save()

        self.assertEquals(Admin.objects.is_account_admin('javerage'), False)

    def test_start_reconcile(self):
        create_admin('javerage')
        create_admin('jsmith')

        imp = Admin.objects.queue_all()

        Admin.objects.start_reconcile(queue_id=imp.pk)

        deleted = Admin.objects.filter(
            is_deleted=True, deleted_date=None, queue_id=imp.pk)
        self.assertEquals(len(deleted), 2)

    def test_finish_reconcile(self):
        create_admin('javerage')
        create_admin('jsmith')

        imp = Admin.objects.queue_all()

        Admin.objects.start_reconcile(queue_id=imp.pk)
        Admin.objects.finish_reconcile(queue_id=imp.pk)

        deleted = Admin.objects.filter(
            is_deleted=True, is_deleted__isnull=False, queue_id=imp.pk)
        self.assertEquals(len(deleted), 2)

        Admin.objects.start_reconcile(queue_id=imp.pk)

        Admin.objects.queued(imp.pk).update(
            deleted_date=(datetime.utcnow() - timedelta(days=100)))

        Admin.objects.finish_reconcile(queue_id=imp.pk)

        admins = Admin.objects.filter(queue_id=imp.pk)
        self.assertEquals(len(admins), 0)

    def test_json_data(self):
        json = create_admin('javerage').json_data()
        self.assertEquals(json['account_id'], 'test')
        self.assertEquals(json['account_link'],
                          'http://canvas.edu/accounts/123')
        self.assertEquals(json['canvas_id'], '123')
        self.assertEquals(json['is_deleted'], False)
        self.assertEquals(json['queue_id'], None)
        self.assertEquals(json['provisioned_date'], '')
        self.assertEquals(json['role'], 'accountadmin')
        self.assertEquals(json['net_id'], 'javerage')


class AccountModelTest(TestCase):
    @mock.patch.object(QuerySet, 'filter')
    def test_find_by_type(self, mock_filter):
        r = Account.objects.find_by_type()
        mock_filter.assert_called_with()

        r = Account.objects.find_by_type(account_type='admin')
        mock_filter.assert_called_with(account_type='admin')

        r = Account.objects.find_by_type(account_type='admin', deleted=True)
        mock_filter.assert_called_with(account_type='admin', is_deleted=1)
