from django.conf import settings
from django.test import TestCase, override_settings
from sis_provisioner.test import create_admin
from sis_provisioner.dao.astra import verify_canvas_admin
from uw_canvas.utilities import fdao_canvas_override
from uw_canvas.admins import Admins
import copy

ACCOUNT_SIS_ID = 'uwcourse:seattle:nursing:nurs'
ACCOUNT_ID = '789'


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
        for admin in Admins().get_admins_by_sis_id(ACCOUNT_SIS_ID):
            self.canvas_admins[admin.user.login_id] = admin

    def test_verify_canvas_admin(self):
        # Valid admins
        self.assertTrue(verify_canvas_admin(
            self.canvas_admins['admin1'], ACCOUNT_ID))
        self.assertTrue(verify_canvas_admin(
            self.canvas_admins['admin4'], ACCOUNT_ID))
        self.assertTrue(verify_canvas_admin(
            self.canvas_admins['admin5'], ACCOUNT_ID))

        # Invalid admins
        self.assertFalse(verify_canvas_admin(
            self.canvas_admins['admin1'], '345'))
        self.assertFalse(verify_canvas_admin(
            self.canvas_admins['admin11'], ACCOUNT_ID))

        # Valid ancillary roles
        admin_5 = copy.deepcopy(self.canvas_admins['admin5'])
        admin_5.role = 'Masquerader'
        self.assertTrue(verify_canvas_admin(
            admin_5, settings.RESTCLIENTS_CANVAS_ACCOUNT_ID))

        # Invalid ancillary roles
        self.assertFalse(verify_canvas_admin(admin_5, ACCOUNT_ID))

        admin_4 = copy.deepcopy(self.canvas_admins['admin4'])
        admin_4.role = 'Masquerader'
        self.assertFalse(verify_canvas_admin(
            admin_4, settings.RESTCLIENTS_CANVAS_ACCOUNT_ID))
