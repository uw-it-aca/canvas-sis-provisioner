from django.test import TestCase, override_settings
from sis_provisioner.dao.astra import ASTRA
from sis_provisioner.exceptions import ASTRAException
from uw_canvas.utilities import fdao_canvas_override


class ASTRATest(TestCase):
    def test_get_canvas_admins(self):
        pass

    def test_canvas_id_from_nonacademic_code(self):
        self.assertEqual(
            ASTRA._canvas_id_from_nonacademic_soc('canvas_123'), '123')
        self.assertRaises(
            ASTRAException, ASTRA._canvas_id_from_nonacademic_soc,
            'abc_123')
        self.assertRaises(
            ASTRAException, ASTRA._canvas_id_from_nonacademic_soc,
            '123')

    def test_canvas_account_from_academic_soc(self):
        pass
