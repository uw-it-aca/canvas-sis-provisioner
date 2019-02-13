from django.test import TestCase
from django.conf import settings
from django.db.models.query import QuerySet
from django.utils.timezone import utc
from sis_provisioner.models import Admin
from sis_provisioner.models.astra import Account
from datetime import datetime
import os
import binascii
import mock


class AdminModelTest(TestCase):
    def setUp(self):
        Admin.objects.all().delete()

    def _create_admin(self, net_id):
        admin = Admin(
            net_id=net_id, reg_id=binascii.b2a_hex(os.urandom(16)).upper(),
            role='accountadmin', account_id='test',
            canvas_id=settings.RESTCLIENTS_CANVAS_ACCOUNT_ID)
        admin.save()
        return admin

    def test_is_account_admin(self):
        self.assertEquals(Admin.objects.is_account_admin('javerage'), False)

        admin = self._create_admin('javerage')

        self.assertEquals(Admin.objects.is_account_admin('javerage'), True)

        admin.is_deleted = True
        admin.deleted_date = datetime.utcnow().replace(tzinfo=utc)
        admin.save()

        self.assertEquals(Admin.objects.is_account_admin('javerage'), False)

    def test_set_deleted(self):
        self._create_admin('javerage')
        self._create_admin('jsmith')

        imp = Admin.objects.queue_all()

        Admin.objects.set_deleted(queue_id=imp.pk)

        deleted = Admin.objects.filter(is_deleted=True, queue_id=imp.pk)
        self.assertEquals(len(deleted), 2)

    def test_get_deleted(self):
        admin = self._create_admin('javerage')

        imp = Admin.objects.queue_all()

        deleted = Admin.objects.get_deleted(queue_id=imp.pk)
        self.assertEquals(len(deleted), 0)

        admin = Admin.objects.get(net_id='javerage')
        admin.is_deleted = True
        admin.deleted_date = datetime.utcnow().replace(tzinfo=utc)
        admin.save()

        deleted = Admin.objects.get_deleted(queue_id=imp.pk)
        self.assertEquals(len(deleted), 1)

    def test_json_data(self):
        with self.settings(RESTCLIENTS_CANVAS_HOST='http://canvas.edu',
                           RESTCLIENTS_CANVAS_ACCOUNT_ID='2'):
            json = self._create_admin('javerage').json_data()
            self.assertEquals(json['account_id'], 'test')
            self.assertEquals(json['account_link'],
                              'http://canvas.edu/accounts/2')
            self.assertEquals(json['canvas_id'], '2')
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
