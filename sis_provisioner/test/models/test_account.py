from django.test import TestCase, override_settings
from django.db.models.query import QuerySet
from sis_provisioner.models import Account
from uw_canvas.models import CanvasAccount


def create_account(canvas_id, sis_id, account_name='Test',
                   account_short_name='', account_type=Account.ADHOC_TYPE):
    account = Account(canvas_id=canvas_id, sis_id=sis_id,
                      account_name=account_name,
                      account_short_name=account_short_name,
                      account_type=account_type)
    account.save()
    return account


class AccountModelTest(TestCase):
    def setUp(self):
        create_account(1, 'test_root', account_name='Root',
                       account_type=Account.ROOT_TYPE)
        create_account(2, 'test_sdb', account_name='SDB',
                       account_type=Account.SDB_TYPE)
        create_account(3, 'test_adhoc_1', account_name='Adhoc1',
                       account_type=Account.ADHOC_TYPE)
        create_account(4, 'test_test', account_name='Test',
                       account_type=Account.TEST_TYPE)
        create_account(5, 'test_adhoc_2', account_name='Adhoc2',
                       account_type=Account.ADHOC_TYPE)

    def test_find_by_type(self):
        r = Account.objects.find_by_type()
        self.assertEqual(len(r), 5)

        r = Account.objects.find_by_type(account_type=Account.ADHOC_TYPE)
        self.assertEqual(len(r), 2)

        r = Account.objects.find_by_type(account_type=Account.ROOT_TYPE,
                                         deleted=True)
        self.assertEqual(len(r), 0)

        account = Account.objects.get(canvas_id=1)
        account.is_deleted = True
        account.save()

        r = Account.objects.find_by_type(account_type=Account.ROOT_TYPE,
                                         deleted=True)
        self.assertEqual(len(r), 1)

    def test_find_by_soc(self):
        r = Account.objects.find_by_soc()
        self.assertEqual(len(r), 3)

        r = Account.objects.find_by_soc(account_type='academic')
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].account_type, Account.SDB_TYPE)

        r = Account.objects.find_by_soc(account_type='non-academic')
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0].account_type, Account.ADHOC_TYPE)

        r = Account.objects.find_by_soc(account_type='test-account')
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].account_type, Account.TEST_TYPE)

        r = Account.objects.find_by_soc(account_type='all')
        self.assertEqual(len(r), 5)

    @override_settings(RESTCLIENTS_CANVAS_ACCOUNT_ID='123',
                       SIS_IMPORT_ROOT_ACCOUNT_ID='sis_root')
    def test_add_account(self):
        canvas_account = CanvasAccount(
            account_id=123, sis_account_id='canvas_123', name='Test_123')

        account = Account.objects.add_account(canvas_account)
        self.assertEqual(account.canvas_id, canvas_account.account_id)
        self.assertEqual(account.sis_id, canvas_account.sis_account_id)
        self.assertEqual(account.account_name, canvas_account.name)
        self.assertEqual(account.account_type, Account.ROOT_TYPE)

        canvas_account = CanvasAccount(
            account_id=456, sis_account_id='sis_root:tacoma', name='Test_456')

        account = Account.objects.add_account(canvas_account)
        self.assertEqual(account.account_type, Account.SDB_TYPE)

        canvas_account = CanvasAccount(
            account_id=789, sis_account_id='canvas_789', name='Test_789')

        account = Account.objects.add_account(canvas_account)
        self.assertEqual(account.account_type, Account.ADHOC_TYPE)

    def test_account_types(self):
        account = Account.objects.get(canvas_id=1)
        self.assertTrue(account.is_root())

        account = Account.objects.get(canvas_id=2)
        self.assertTrue(account.is_sdb())

        account = Account.objects.get(canvas_id=3)
        self.assertTrue(account.is_adhoc())

        account = Account.objects.get(canvas_id=4)
        self.assertTrue(account.is_test())

    def test_json_data(self):
        account = Account.objects.get(canvas_id=2)
        json_data = account.json_data()
        self.assertEqual(json_data['canvas_id'], 2)
        self.assertEqual(json_data['sis_id'], 'test_sdb')
        self.assertEqual(json_data['account_name'], 'SDB')
        self.assertEqual(json_data['account_short_name'], '')
        self.assertEqual(json_data['account_type'], 'sdb')
        self.assertEqual(json_data['is_deleted'], False)

    def test_soc_json_data(self):
        account = Account.objects.get(canvas_id=2)
        self.assertEqual(account.soc_json_data(), {
            'description': 'SDB', 'id': 'canvas_2',
            'short_description': '', 'type': 'SDB'})
