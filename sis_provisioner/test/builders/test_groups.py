from django.test import TestCase
from sis_provisioner.builders.groups import GroupBuilder


class GroupBuilderTest(TestCase):
    def test_group_builder(self):
        # Test delta
        builder = GroupBuilder()
        self.assertEquals(builder.build(), None)
        self.assertEquals(builder.delta, True)
        self.assertEquals(len(builder.cached_course_enrollments), 0)

        builder = GroupBuilder()
        self.assertEquals(builder.build(delta=False), None)
        self.assertEquals(builder.delta, False)
        self.assertEquals(len(builder.cached_course_enrollments), 0)

        # Test duplicate course_ids
        items = [1, 2, 2, 3, 4, 5, 5]
        builder = GroupBuilder(items)
        self.assertEquals(len(builder.items), len(items))
        builder._init_build()
        self.assertEquals(len(builder.items), 5)
