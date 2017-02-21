from django.test import TestCase
from types import DictType
from sis_provisioner.models import Curriculum


class CurriculumModelTest(TestCase):
    def test_accounts_by_curricula(self):
        r = Curriculum.objects.accounts_by_curricula()
        self.assertEquals(type(r), DictType)
        self.assertEquals(len(r), 0)
