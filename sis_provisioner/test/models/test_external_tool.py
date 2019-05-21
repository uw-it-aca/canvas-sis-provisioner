from django.test import TestCase, override_settings
from django.utils.timezone import utc
from sis_provisioner.models.external_tools import (
    ExternalTool, ExternalToolManager)
from sis_provisioner.test.models.test_account import create_account
from datetime import datetime
import json
import mock


@override_settings(RESTCLIENTS_CANVAS_ACCOUNT_ID='1',
                   RESTCLIENTS_CANVAS_HOST='http://canvas.edu')
class ExternalToolModelTest(TestCase):
    def setUp(self):
        self.account1 = create_account('1', 'test1')
        self.tool1 = ExternalTool(
            account=self.account1,
            canvas_id='123',
            config=json.dumps({
                'name': 'Test1'}),
            changed_by='user123',
            changed_date=datetime(2000, 10, 10, 0, 0, 0).replace(tzinfo=utc))
        self.tool1.save()

    def test_generate_shared_secret(self):
        secret = self.tool1.generate_shared_secret()
        self.assertRegex(secret, r'^[A-Z0-9]{32}$')

    def test_json_data(self):
        data = self.tool1.json_data()
        self.assertEqual(data['account']['canvas_id'], '1')
        self.assertEqual(data['canvas_id'], '123')
        self.assertEqual(data['changed_by'], 'user123')
        self.assertEqual(data['changed_date'], '2000-10-10T00:00:00+00:00')
        self.assertEqual(data['config'], {'name': 'Test1'})
        self.assertEqual(data['consumer_key'], None)
        self.assertEqual(data['name'], 'Test1')
        self.assertEqual(data['provisioned_date'], None)

    @mock.patch.object(ExternalToolManager, 'update_tools_in_account')
    def test_update_all(self, mock_method):
        r = ExternalTool.objects.update_all()
        mock_method.assert_called_with('1', 'auto')
