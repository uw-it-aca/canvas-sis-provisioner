from django.test import TestCase
from sis_provisioner.builders.groups import GroupBuilder


class GroupBuilderTest(TestCase):
    def test_group_builder(self):
        builder = GroupBuilder()
        self.assertEquals(builder.build(), None)
