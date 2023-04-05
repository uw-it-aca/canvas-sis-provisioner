# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.test import TestCase, override_settings
from django.db.models.query import QuerySet
from django.utils.timezone import utc
from datetime import datetime
from sis_provisioner.dao.course import get_section_by_id
from sis_provisioner.models import Import
from sis_provisioner.models.enrollment import (
    Enrollment, EnrollmentManager, InvalidEnrollment)
from sis_provisioner.models.course import Course
from sis_provisioner.exceptions import EmptyQueueException
from uw_sws.util import fdao_sws_override
from uw_pws.util import fdao_pws_override
import mock


@fdao_sws_override
@fdao_pws_override
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

    @mock.patch('sis_provisioner.models.enrollment.is_active_term',
                return_value=False)
    @mock.patch('sis_provisioner.models.enrollment.logger')
    def test_add_teacher_enrollment(self, mock_logger, mock_is_active_term):
        now_dt = datetime(2013, 1, 1).replace(tzinfo=utc)
        teacher_data = {
            'Section': get_section_by_id('2013-summer-TRAIN-101-A'),
            'UWRegID': 'BCDEF1234567890ABCDEF1234567890',
            'Role': 'Teacher',
            'Status': 'Active',
            'LastModified': now_dt,
            'InstructorUWRegID': None}

        # Section not in course table
        Enrollment.objects.add_enrollment(teacher_data)
        mock_logger.info.assert_called_with(
            'ADD ENROLLMENT: IGNORE (Inactive section) status: active, '
            'regid: BCDEF1234567890ABCDEF1234567890, section: 2013-summer-'
            'TRAIN-101-A, duplicate_code: , role: Teacher, last_modified '
            '2013-01-01 00:00:00+00:00, queue_id: ')

        course, created = Course.objects.get_or_create(
            course_id='2013-summer-TRAIN-101-A')

        # Course model without a provisioned_date
        Enrollment.objects.add_enrollment(teacher_data)
        mock_logger.info.assert_called_with(
            'ADD ENROLLMENT: IGNORE (Unprovisioned course) status: active, '
            'regid: BCDEF1234567890ABCDEF1234567890, section: 2013-summer-'
            'TRAIN-101-A, duplicate_code: , role: Teacher, last_modified '
            '2013-01-01 00:00:00+00:00, queue_id: ')

        # Course model with a provisioned_date
        course.provisioned_date = now_dt
        course.save()
        Enrollment.objects.add_enrollment(teacher_data)
        mock_logger.info.assert_called_with(
            'ADD ENROLLMENT: ADD status: active, regid: BCDEF1234567890ABCD'
            'EF1234567890, section: 2013-summer-TRAIN-101-A, duplicate_code: '
            ', role: Teacher, last_modified 2013-01-01 00:00:00+00:00, '
            'queue_id: ')

        # Enrollment added again
        Enrollment.objects.add_enrollment(teacher_data)
        mock_logger.info.assert_called_with(
            'ADD ENROLLMENT: UPDATE EXISTING status: active, regid: BCDEF123'
            '4567890ABCDEF1234567890, section: 2013-summer-TRAIN-101-A, '
            'duplicate_code: , role: Teacher, last_modified 2013-01-01 '
            '00:00:00+00:00, queue_id: ')

        # Deleted
        teacher_data['Status'] = 'Deleted'
        Enrollment.objects.add_enrollment(teacher_data)
        mock_logger.info.assert_called_with(
            'ADD ENROLLMENT: UPDATE EXISTING status: deleted, regid: BCDEF123'
            '4567890ABCDEF1234567890, section: 2013-summer-TRAIN-101-A, '
            'duplicate_code: , role: Teacher, last_modified 2013-01-01 '
            '00:00:00+00:00, queue_id: ')

        Course.objects.all().delete()
        Enrollment.objects.all().delete()

    @mock.patch('sis_provisioner.models.enrollment.is_active_term',
                return_value=False)
    @mock.patch('sis_provisioner.models.enrollment.logger')
    def test_add_student_enrollment(self, mock_logger, mock_is_active_term):
        now_dt = datetime(2013, 1, 1).replace(tzinfo=utc)
        student_data = {
            'Section': get_section_by_id('2013-summer-TRAIN-101-A'),
            'UWRegID': 'BCDEF1234567890ABCDEF1234567890',
            'Role': 'Student',
            'Status': 'Active',
            'LastModified': now_dt,
            'DuplicateCode': 'A',
            'InstructorUWRegID': None}

        # Section not in course table
        Enrollment.objects.add_enrollment(student_data)
        mock_logger.info.assert_called_with(
            'ADD ENROLLMENT: IGNORE (Inactive section) status: active, '
            'regid: BCDEF1234567890ABCDEF1234567890, section: 2013-summer-'
            'TRAIN-101-A, duplicate_code: A, role: Student, last_modified '
            '2013-01-01 00:00:00+00:00, queue_id: ')

        course, created = Course.objects.get_or_create(
            course_id='2013-summer-TRAIN-101-A')

        # Course model without a provisioned_date
        Enrollment.objects.add_enrollment(student_data)
        mock_logger.info.assert_called_with(
            'ADD ENROLLMENT: IGNORE (Unprovisioned course) status: active, '
            'regid: BCDEF1234567890ABCDEF1234567890, section: 2013-summer-'
            'TRAIN-101-A, duplicate_code: A, role: Student, last_modified '
            '2013-01-01 00:00:00+00:00, queue_id: ')

        # Course model with a provisioned_date
        course.provisioned_date = now_dt
        course.save()
        Enrollment.objects.add_enrollment(student_data)
        mock_logger.info.assert_called_with(
            'ADD ENROLLMENT: ADD status: active, regid: BCDEF1234567890ABCD'
            'EF1234567890, section: 2013-summer-TRAIN-101-A, duplicate_code: '
            'A, role: Student, last_modified 2013-01-01 00:00:00+00:00, '
            'queue_id: ')

        # Enrollment added again
        Enrollment.objects.add_enrollment(student_data)
        mock_logger.info.assert_called_with(
            'ADD ENROLLMENT: UPDATE EXISTING status: active, regid: BCDEF123'
            '4567890ABCDEF1234567890, section: 2013-summer-TRAIN-101-A, '
            'duplicate_code: A, role: Student, last_modified 2013-01-01 '
            '00:00:00+00:00, queue_id: ')

        # Enrollment added again with deleted status
        student_data['DuplicateCode'] = ''
        student_data['Status'] = 'Deleted'
        Enrollment.objects.add_enrollment(student_data)
        mock_logger.info.assert_called_with(
            'ADD ENROLLMENT: IGNORE (Out of order: 2013-01-01 00:00:00+00:00) '
            'status: deleted, regid: BCDEF1234567890ABCDEF1234567890, '
            'section: 2013-summer-TRAIN-101-A, duplicate_code: , role: '
            'Student, last_modified 2013-01-01 00:00:00+00:00, queue_id: ')

        student_data['DuplicateCode'] = 'A'
        student_data['Status'] = 'Deleted'
        Enrollment.objects.add_enrollment(student_data)
        mock_logger.info.assert_called_with(
            'ADD ENROLLMENT: UPDATE EXISTING status: deleted, regid: BCDEF123'
            '4567890ABCDEF1234567890, section: 2013-summer-TRAIN-101-A, '
            'duplicate_code: A, role: Student, last_modified 2013-01-01 '
            '00:00:00+00:00, queue_id: ')

        Course.objects.all().delete()
        Enrollment.objects.all().delete()

    @mock.patch.object(QuerySet, 'filter')
    @mock.patch.object(EnrollmentManager, 'purge_expired')
    def test_dequeue_imported(self, mock_purge, mock_filter):
        dt = datetime.now()
        r = Enrollment.objects.dequeue(Import(
            pk=1,
            priority=Enrollment.PRIORITY_HIGH,
            canvas_state='imported',
            post_status=200,
            canvas_progress=100,
            monitor_date=dt))

        mock_filter.assert_called_with(
            queue_id=1, priority__gt=Enrollment.PRIORITY_NONE)

    @mock.patch.object(QuerySet, 'update')
    def test_dequeue_not_imported(self, mock_update):
        r = Enrollment.objects.dequeue(
            Import(pk=1, priority=Enrollment.PRIORITY_HIGH))
        mock_update.assert_called_with(queue_id=None)

    @mock.patch.object(QuerySet, 'filter')
    @mock.patch('sis_provisioner.models.enrollment.datetime')
    @override_settings(ENROLLMENT_EVENT_RETENTION_DAYS=3)
    def test_purge_expired(self, mock_datetime, mock_filter):
        mock_datetime.utcnow.return_value = datetime(2013, 1, 4, 0, 0, 0)
        r = Enrollment.objects.purge_expired()
        mock_filter.assert_called_with(
            priority=Enrollment.PRIORITY_NONE,
            last_modified__lt=datetime(2013, 1, 1, 0, 0, 0, tzinfo=utc))


class InvalidEnrollmentModelTest(TestCase):
    @mock.patch.object(QuerySet, 'filter')
    def test_queue_by_priority(self, mock_filter):
        try:
            r = InvalidEnrollment.objects.queue_by_priority()
        except EmptyQueueException:
            pass
        mock_filter.assert_called_with(
            priority=InvalidEnrollment.PRIORITY_DEFAULT,
            queue_id__isnull=True)
