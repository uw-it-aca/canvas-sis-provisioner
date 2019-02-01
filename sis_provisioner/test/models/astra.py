from django.test import TestCase
from django.db.models.query import QuerySet
from django.utils.timezone import utc
from sis_provisioner.models.astra import Account, Admin
from datetime import datetime
import mock


class AdminModelTest(TestCase):
    def _create_admin(self, net_id):
        admin = Admin(
            net_id=net_id, reg_id='AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
            role='accountadmin', account_id='1', canvas_id='2')
        admin.save()
        return admin

    def _clear_admins(self):
        Admin.objects.all().delete()

    def test_is_account_admin(self):
        self._clear_admins()

        self.assertEquals(Admin.objects.is_account_admin('javerage'), False)

        admin = self._create_admin('javerage')

        self.assertEquals(Admin.objects.is_account_admin('javerage'), True)

        admin.is_deleted = True
        admin.deleted_date = datetime.utcnow().replace(tzinfo=utc)
        admin.save()

        self.assertEquals(Admin.objects.is_account_admin('javerage'), False)

        self._clear_admins()

    @mock.patch.object(QuerySet, 'update')
    def test_dequeue(self, mock_update):
        r = Admin.objects.dequeue(queue_id=1)
        mock_update.assert_called_with(queue_id=None)

        r = Admin.objects.dequeue()
        mock_update.assert_called_with(queue_id=None)

    def test_get_deleted(self):
        self._clear_admins()
        admin = self._create_admin('javerage')

        deleted = Admin.objects.get_deleted()
        self.assertEquals(len(deleted), 0)

        admin.is_deleted = True
        admin.deleted_date = datetime.utcnow().replace(tzinfo=utc)
        admin.save()

        deleted = Admin.objects.get_deleted()
        self.assertEquals(len(deleted), 1)

        self._clear_admins()

    def test_json_data(self):
        self._clear_admins()
        with self.settings(RESTCLIENTS_CANVAS_HOST='http://canvas.edu'):
            json = self._create_admin('javerage').json_data()
            self.assertEquals(json['account_id'], '1')
            self.assertEquals(json['account_link'],
                              'http://canvas.edu/accounts/2')
            self.assertEquals(json['canvas_id'], '2')
            self.assertEquals(json['is_deleted'], False)
            self.assertEquals(json['queue_id'], None)
            self.assertEquals(json['provisioned_date'], '')
            self.assertEquals(json['role'], 'accountadmin')
            self.assertEquals(json['net_id'], 'javerage')

        self._clear_admins()


class AccountModelTest(TestCase):
    @mock.patch.object(QuerySet, 'filter')
    def test_find_by_type(self, mock_filter):
        r = Account.objects.find_by_type()
        mock_filter.assert_called_with()

        r = Account.objects.find_by_type(account_type='admin')
        mock_filter.assert_called_with(account_type='admin')

        r = Account.objects.find_by_type(account_type='admin', deleted=True)
        mock_filter.assert_called_with(account_type='admin', is_deleted=1)
