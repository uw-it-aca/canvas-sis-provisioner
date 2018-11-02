from django.test import TestCase
from sis_provisioner.builders.courses import CourseBuilder, UnusedCourseBuilder
import mock


class CourseBuilderTest(TestCase):
    def test_course_builder(self):
        builder = CourseBuilder()

        self.assertEquals(builder.build(), None)
        self.assertEquals(builder.include_enrollment, True)

        self.assertEquals(builder.build(include_enrollment=False), None)
        self.assertEquals(builder.include_enrollment, False)

    @mock.patch(
        'sis_provisioner.builders.courses.get_unused_course_report_data')
    def test_unused_course_builder(self, mock_report):
        builder = UnusedCourseBuilder()

        self.assertEquals(builder.build(), None)
        self.assertEquals(builder.term_sis_id, None)

        self.assertEquals(builder.build(term_sis_id='2013-autumn'), None)
        self.assertEquals(builder.term_sis_id, '2013-autumn')
