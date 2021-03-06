from django.test import TestCase
from sis_provisioner.builders.enrollments import EnrollmentBuilder
from datetime import datetime


class EnrollmentBuilderTest(TestCase):
    def test_enrollment_builder(self):
        builder = EnrollmentBuilder()

        self.assertEquals(builder.build(), None)
        self.assertEquals(type(builder.retry_missing_id), datetime)
