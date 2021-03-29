# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
from sis_provisioner.models import Curriculum


class CurriculumModelTest(TestCase):
    def test_accounts_by_curricula(self):
        r = Curriculum.objects.accounts_by_curricula()
        self.assertTrue(isinstance(r, dict))
        self.assertEquals(len(r), 0)
