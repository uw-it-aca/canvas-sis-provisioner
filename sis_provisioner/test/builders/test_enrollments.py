# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.test import TestCase
from sis_provisioner.builders.enrollments import EnrollmentBuilder
from datetime import datetime


class EnrollmentBuilderTest(TestCase):
    def test_enrollment_builder(self):
        builder = EnrollmentBuilder()

        self.assertEqual(builder.build(), None)
        self.assertEqual(type(builder.retry_missing_id), datetime)
