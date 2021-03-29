# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase, override_settings
from sis_provisioner.dao.astra import ASTRA
from sis_provisioner.exceptions import ASTRAException
from uw_canvas.utilities import fdao_canvas_override


class MockSoC():
    def __init__(self, *args, **kwargs):
        self._type = kwargs.get('type')
        self._code = kwargs.get('code')


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

    @override_settings(SIS_IMPORT_ROOT_ACCOUNT_ID='root')
    def test_canvas_account_from_academic_soc(self):
        soc1 = MockSoC(type='SWSCampus', code='seattle')
        soc2 = MockSoC(type='swscollege', code='med')
        soc3 = MockSoC(type='swsdepartment', code='anest')
        soc4 = MockSoC(type='swscampus', code='nomatch')
        soc5 = MockSoC(type='swscollege', code='nomatch')
        soc6 = MockSoC(type='swsdepartment', code='nomatch')

        self.assertEqual(ASTRA._canvas_account_from_academic_soc(
            [soc1]), 'root:seattle')
        self.assertEqual(ASTRA._canvas_account_from_academic_soc(
            [soc1, soc2]), 'root:seattle:medicine')
        self.assertEqual(ASTRA._canvas_account_from_academic_soc(
            [soc1, soc2, soc3]), 'root:seattle:medicine:anest')

        # Missing campus
        self.assertRaises(
            ASTRAException, ASTRA._canvas_account_from_academic_soc,
            [soc2, soc3])
        # Missing college
        self.assertRaises(
            ASTRAException, ASTRA._canvas_account_from_academic_soc,
            [soc1, soc3])
        # Unknown campus
        self.assertRaises(
            ASTRAException, ASTRA._canvas_account_from_academic_soc,
            [soc4])
        # Unknown college
        self.assertRaises(
            ASTRAException, ASTRA._canvas_account_from_academic_soc,
            [soc1, soc5])
        # Unknown department
        self.assertRaises(
            ASTRAException, ASTRA._canvas_account_from_academic_soc,
            [soc1, soc2, soc6])
        # Empty list
        self.assertRaises(
            ASTRAException, ASTRA._canvas_account_from_academic_soc,
            [])
