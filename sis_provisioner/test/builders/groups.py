from django.test import TestCase
from sis_provisioner.builders.groups import GroupBuilder


class GroupBuilderTest(TestCase):
    def test_group_builder(self):
        builder = GroupBuilder()

        self.assertEquals(builder.build(), None)
        self.assertEquals(builder.delta, True)
        self.assertEquals(len(builder.cached_course_enrollments), 0)

        self.assertEquals(builder.build(delta=False), None)
        self.assertEquals(builder.delta, False)
        self.assertEquals(len(builder.cached_course_enrollments), 0)
