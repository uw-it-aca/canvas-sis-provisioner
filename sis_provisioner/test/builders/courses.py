from django.test import TestCase
from sis_provisioner.builders.courses import CourseBuilder


class CourseBuilderTest(TestCase):
    def test_course_builder(self):
        builder = CourseBuilder()

        self.assertEquals(builder.build(), None)
        self.assertEquals(builder.include_enrollment, True)

        self.assertEquals(builder.build(include_enrollment=False), None)
        self.assertEquals(builder.include_enrollment, False)
