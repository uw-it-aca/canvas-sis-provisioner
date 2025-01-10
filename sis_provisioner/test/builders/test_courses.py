# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.test import TestCase
from sis_provisioner.builders.courses import CourseBuilder, UnusedCourseBuilder
import mock


class CourseBuilderTest(TestCase):
    def test_course_builder(self):
        builder = CourseBuilder()

        self.assertEqual(builder.build(), None)
        self.assertEqual(builder.include_enrollment, True)

        self.assertEqual(builder.build(include_enrollment=False), None)
        self.assertEqual(builder.include_enrollment, False)

    @mock.patch(
        'sis_provisioner.builders.courses.get_unused_course_report_data')
    def test_unused_course_builder(self, mock_report):
        builder = UnusedCourseBuilder()

        self.assertEqual(builder.build(), None)
        self.assertEqual(builder.term_sis_id, None)

        self.assertEqual(builder.build(term_sis_id='2013-autumn'), None)
        self.assertEqual(builder.term_sis_id, '2013-autumn')
