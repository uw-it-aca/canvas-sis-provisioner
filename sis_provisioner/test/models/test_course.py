# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.test import TestCase
from django.db.models.query import QuerySet
from django.utils.timezone import utc
from datetime import datetime
from sis_provisioner.dao.course import get_section_by_id
from sis_provisioner.models import Import
from sis_provisioner.models.course import Course
from sis_provisioner.exceptions import CoursePolicyException
from uw_sws.util import fdao_sws_override
from uw_pws.util import fdao_pws_override
import mock


@fdao_sws_override
@fdao_pws_override
class CourseModelTest(TestCase):
    def test_types(self):
        sdb_course = Course(course_type=Course.SDB_TYPE)
        self.assertEquals(sdb_course.is_sdb(), True)
        self.assertEquals(sdb_course.is_adhoc(), False)

        adhoc_course = Course(course_type=Course.ADHOC_TYPE)
        self.assertEquals(adhoc_course.is_sdb(), False)
        self.assertEquals(adhoc_course.is_adhoc(), True)

    def test_sws_url(self):
        sdb_course = Course(course_type=Course.SDB_TYPE,
                            course_id='2013-summer-TRAIN-101-A')
        self.assertEquals(
            sdb_course.sws_url(), (
                '/restclients/view/sws/student/v5/course/'
                '2013,summer,TRAIN,101/A.json'))

        adhoc_course = Course(course_type=Course.ADHOC_TYPE,
                              course_id='course_12345')
        self.assertEquals(adhoc_course.sws_url(), None)

    def test_add_to_queue(self):
        section = get_section_by_id('2013-summer-TRAIN-101-A')
        course = Course.objects.add_to_queue(section, queue_id=1)
        self.assertEquals(course.queue_id, 1)
        self.assertEquals(course.primary_id, None)

        section = get_section_by_id('2013-summer-TRAIN-100-AB')
        course = Course.objects.add_to_queue(section, queue_id=2)
        self.assertEquals(course.queue_id, 2)
        self.assertEquals(course.primary_id, '2013-summer-TRAIN-100-A')

        Course.objects.all().delete()

    def test_remove_from_queue(self):
        course_id = '2013-summer-TRAIN-101-A'

        section = get_section_by_id(course_id)
        course = Course.objects.add_to_queue(section, queue_id='1')
        course = Course.objects.get(course_id=course_id)
        self.assertEquals(course.queue_id, '1')

        Course.objects.remove_from_queue(course_id)
        course = Course.objects.get(course_id=course_id)
        self.assertEquals(course.queue_id, None)
        self.assertEquals(course.provisioned_error, None)
        self.assertEquals(course.provisioned_status, None)

        # Remove with error
        course = Course.objects.add_to_queue(section, queue_id='2')
        course = Course.objects.get(course_id=course_id)
        self.assertEquals(course.queue_id, '2')

        Course.objects.remove_from_queue(course_id, error='oops')
        course = Course.objects.get(course_id=course_id)
        self.assertEquals(course.queue_id, None)
        self.assertEquals(course.provisioned_error, True)
        self.assertEquals(course.provisioned_status, 'oops')

        Course.objects.all().delete()

    def test_update_status(self):
        course_id = '2013-summer-TRAIN-101-A'

        section = get_section_by_id(course_id)

        course = Course.objects.add_to_queue(section, queue_id='3')
        Course.objects.update_status(section)
        course = Course.objects.get(course_id=course_id)
        self.assertEquals(course.queue_id, '3')
        self.assertEquals(course.provisioned_status, None)
        self.assertEquals(course.priority, course.PRIORITY_DEFAULT)

        section.delete_flag = section.DELETE_FLAG_WITHDRAWN
        course = Course.objects.add_to_queue(section, queue_id='4')
        Course.objects.update_status(section)
        course = Course.objects.get(course_id=course_id)
        self.assertEquals(course.queue_id, '4')
        self.assertEquals(course.provisioned_status, None)
        self.assertEquals(course.priority, course.PRIORITY_NONE)

        Course.objects.all().delete()

    def test_update_priority(self):
        course = Course(course_type=Course.SDB_TYPE,
                        course_id='2013-summer-TRAIN-101-A')
        self.assertEqual(course.priority, course.PRIORITY_DEFAULT)

        course.update_priority('high')
        self.assertEqual(course.priority, course.PRIORITY_HIGH)

        self.assertRaises(CoursePolicyException, course.update_priority, '')

    def test_default_expiration_date(self):
        course = Course(course_type=Course.SDB_TYPE,
                        course_id='2013-summer-TRAIN-101-A')

        self.assertEqual(course.default_expiration_date.year, 2019)

        course = Course(course_type=Course.SDB_TYPE,
                        course_id='2014-winter-TRAIN-101-A')
        self.assertEqual(course.default_expiration_date.year, 2019)

        now = datetime.now().replace(tzinfo=utc)
        course = Course(course_type=Course.SDB_TYPE,
                        course_id='course_54321',
                        created_date=now)
        self.assertEqual(course.default_expiration_date.year, now.year + 5)

    @mock.patch.object(QuerySet, 'update')
    def test_dequeue(self, mock_update):
        dt = datetime.now()
        r = Course.objects.dequeue(Import(pk=1,
                                          priority=Course.PRIORITY_HIGH,
                                          canvas_state='imported',
                                          post_status=200,
                                          canvas_progress=100,
                                          monitor_date=dt))
        mock_update.assert_called_with(
            priority=Course.PRIORITY_DEFAULT, queue_id=None,
            provisioned_date=dt)

        r = Course.objects.dequeue(Import(pk=1, priority=Course.PRIORITY_HIGH))
        mock_update.assert_called_with(queue_id=None)
