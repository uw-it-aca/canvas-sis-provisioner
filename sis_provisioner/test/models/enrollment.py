from django.test import TestCase
from django.db.models.query import QuerySet
from django.utils.timezone import utc
from datetime import datetime
from sis_provisioner.dao.course import get_section_by_id
from sis_provisioner.models import (
    Course, Enrollment, Import, PRIORITY_NONE, PRIORITY_DEFAULT, PRIORITY_HIGH)
import mock


class EnrollmentModelTest(TestCase):
    def test_is_active(self):
        active_enrollment = Enrollment(status='active')
        self.assertEquals(active_enrollment.is_active(), True)

        active_enrollment = Enrollment(status='Active')
        self.assertEquals(active_enrollment.is_active(), True)

        inactive_enrollment = Enrollment()
        self.assertEquals(inactive_enrollment.is_active(), False)

        inactive_enrollment = Enrollment(status='inactive')
        self.assertEquals(inactive_enrollment.is_active(), False)

        deleted_enrollment = Enrollment(status='deleted')
        self.assertEquals(deleted_enrollment.is_active(), False)

        completed_enrollment = Enrollment(status='completed')
        self.assertEquals(completed_enrollment.is_active(), False)

    def test_is_instructor(self):
        enrollment = Enrollment(role='teacher')
        self.assertEquals(enrollment.is_instructor(), True)

        enrollment = Enrollment(role='Teacher')
        self.assertEquals(enrollment.is_instructor(), True)

        enrollment = Enrollment(role='instructor')
        self.assertEquals(enrollment.is_instructor(), False)

        enrollment = Enrollment(role='student')
        self.assertEquals(enrollment.is_instructor(), False)

        enrollment = Enrollment()
        self.assertEquals(enrollment.is_instructor(), False)

    @mock.patch('sis_provisioner.models.logger')
    def test_add_enrollment(self, mock_logger):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            now_dt = datetime(2013, 1, 1).replace(tzinfo=utc)
            student_data = {'Section': get_section_by_id('2013-summer-TRAIN-101-A'),
                            'UWRegID': 'BCDEF1234567890ABCDEF1234567890',
                            'Role': 'Student',
                            'Status': 'Active',
                            'LastModified': now_dt,
                            'InstructorUWRegID': None}

            # Section not in course table
            Enrollment.objects.add_enrollment(student_data)
            mock_logger.info.assert_called_with('Enrollment: IGNORE Unprovisioned course 2013-summer-TRAIN-101-A, BCDEF1234567890ABCDEF1234567890, Student')

            course = Course.objects.get(course_id='2013-summer-TRAIN-101-A')

            # Course model without a provisioned_date
            Enrollment.objects.add_enrollment(student_data)
            mock_logger.info.assert_called_with('Enrollment: IGNORE Unprovisioned course 2013-summer-TRAIN-101-A, BCDEF1234567890ABCDEF1234567890, Student')

            # Course model with a provisioned_date
            course.provisioned_date = now_dt
            course.save()
            Enrollment.objects.add_enrollment(student_data)
            mock_logger.info.assert_called_with('Enrollment: ADD 2013-summer-TRAIN-101-A, BCDEF1234567890ABCDEF1234567890, Student, active, 2013-01-01 00:00:00+00:00')

            # Enrollment added again
            Enrollment.objects.add_enrollment(student_data)
            mock_logger.info.assert_called_with('Enrollment: UPDATE 2013-summer-TRAIN-101-A, BCDEF1234567890ABCDEF1234567890, Student, active, 2013-01-01 00:00:00+00:00')

            # Enrollment added again with deleted status
            student_data['Status'] = 'Deleted'
            Enrollment.objects.add_enrollment(student_data)
            mock_logger.info.assert_called_with('Enrollment: IGNORE 2013-summer-TRAIN-101-A, BCDEF1234567890ABCDEF1234567890, 2013-01-01 00:00:00+00:00 before 2013-01-01 00:00:00+00:00')

            Course.objects.all().delete()
            Enrollment.objects.all().delete()

    @mock.patch.object(QuerySet, 'filter')
    def test_dequeue_imported(self, mock_filter):
        dt = datetime.now()
        r = Enrollment.objects.dequeue(Import(pk=1,
                                              priority=PRIORITY_HIGH,
                                              canvas_state='imported',
                                              post_status=200,
                                              canvas_progress=100,
                                              monitor_date=dt))

        mock_filter.assert_called_with(queue_id=1, priority__gt=PRIORITY_NONE)

    @mock.patch.object(QuerySet, 'update')
    def test_dequeue_not_imported(self, mock_update):
        r = Enrollment.objects.dequeue(Import(pk=1, priority=PRIORITY_HIGH))
        mock_update.assert_called_with(queue_id=None)
