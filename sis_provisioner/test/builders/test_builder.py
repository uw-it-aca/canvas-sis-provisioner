# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.test import TestCase, override_settings
from uw_sws.util import fdao_sws_override
from uw_pws.util import fdao_pws_override
from sis_provisioner.builders import Builder
from sis_provisioner.csv.data import Collector
from sis_provisioner.exceptions import CoursePolicyException
from restclients_core.exceptions import DataFailureException
from uw_sws.exceptions import InvalidCanvasIndependentStudyCourse


@fdao_sws_override
@fdao_pws_override
class BuilderTest(TestCase):
    def test_builder(self):
        builder = Builder()

        self.assertEqual(type(builder.data), Collector)
        self.assertEqual(builder.queue_id, None)
        self.assertEqual(len(builder.invalid_users), 0)
        self.assertEqual(builder.build(), None)
        self.assertRaises(NotImplementedError, builder._process, True)

    def test_get_section_resource_by_id(self):
        builder = Builder()

        # OK
        section = builder.get_section_resource_by_id(
            '2013-winter-DROP_T-100-B')
        self.assertEqual(section.section_label(), '2013,winter,DROP_T,100/B')
        self.assertEqual(section.canvas_course_sis_id(),
                         '2013-winter-DROP_T-100-B')

        # 404 Not Found
        self.assertRaises(DataFailureException,
                          builder.get_section_resource_by_id,
                          '2013-winter-FAKE-999-A')

        # Invalid ID
        self.assertRaises(CoursePolicyException,
                          builder.get_section_resource_by_id,
                          '2013-winter-AAA-BBB')

        # Independent study
        section = builder.get_section_resource_by_id(
            '2020-summer-PHIL-600-A-9136CCB8F66711D5BE060004AC494FFE')
        self.assertEqual(section.section_label(), '2020,summer,PHIL,600/A')
        self.assertEqual(section.canvas_course_sis_id(), (
            '2020-summer-PHIL-600-A-9136CCB8F66711D5BE060004AC494FFE'))

        # Independent study, Missing instructor regid
        self.assertRaises(InvalidCanvasIndependentStudyCourse,
                          builder.get_section_resource_by_id,
                          '2020-summer-PHIL-600-A')

    def test_add_registrations_by_section(self):
        builder = Builder()

        section = builder.get_section_resource_by_id(
            '2013-winter-DROP_T-100-B')
        self.assertEqual(builder.add_registrations_by_section(section), None)

    def test_add_group_enrollment_data(self):
        builder = Builder()
        builder.add_group_enrollment_data(
            'bill', '2013-winter-AAA-BB-groups', 'student', 'active')
        self.assertEqual(
            str(builder.data.enrollments[0]), (
                ',,FBB38FE46A7C11D5A4AE0004AC494FFE,student,'
                ',2013-winter-AAA-BB-groups,active,\n'))

        builder = Builder()
        builder.add_group_enrollment_data(
            'jav.erage@gmail.com', '2013-winter-AAA-BB-groups', 'ta', 'active')
        self.assertEqual(len(builder.data.enrollments), 0)
