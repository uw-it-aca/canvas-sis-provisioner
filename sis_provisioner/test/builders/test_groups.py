from django.test import TestCase
from sis_provisioner.builders.groups import GroupBuilder


class GroupBuilderTest(TestCase):
    def test_group_builder(self):
        # Test delta
        builder = GroupBuilder()
        self.assertEquals(builder.build(), None)
        self.assertEquals(len(builder.cached_sis_enrollments), 0)
        self.assertEquals(len(builder.cached_group_enrollments), 0)
