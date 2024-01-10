# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.test import TestCase
from django.db.models.query import QuerySet
from sis_provisioner.models import Import
from sis_provisioner.models.group import Group
from datetime import datetime
from dateutil import tz
import mock


def create_group(course_id, group_id, role='teacher', added_by='javerage'):
    group = Group(course_id=course_id,
                  group_id=group_id,
                  role=role,
                  added_by=added_by)
    group.save()


class GroupModelTest(TestCase):
    def setUp(self):
        create_group(course_id='123', group_id='test_group_1')
        create_group(course_id='123', group_id='test_group_2')
        create_group(course_id='456', group_id='test_group_3')
        create_group(course_id='789', group_id='test_group_1', role='student')

    def test_update_priority(self):
        create_group(course_id='1099', group_id='test_priority', role='ta')
        group = Group.objects.get(group_id='test_priority')
        self.assertEqual(group.priority, group.PRIORITY_DEFAULT)

        # Set a valid priority value
        group.update_priority(group.PRIORITY_HIGH)
        group = Group.objects.get(group_id='test_priority')
        self.assertEqual(group.priority, group.PRIORITY_HIGH)

        # Set an invalid priority value
        group.update_priority(-1)
        group = Group.objects.get(group_id='test_priority')
        self.assertEqual(group.priority, group.PRIORITY_HIGH)

    def test_find_by_search(self):
        r = Group.objects.find_by_search(course_id='123')
        self.assertEqual(r.count(), 2)

        r = Group.objects.find_by_search(group_id='test_group_1',
                                         role='teacher')
        self.assertEqual(r.count(), 1)

    def test_get_active_by_course(self):
        r = Group.objects.get_active_by_course('123')
        self.assertEqual(r.count(), 2)

    def test_queued(self):
        r = Group.objects.queued('12345')
        self.assertEqual(len(r), 0)

        Group.objects.all().update(queue_id='12345')
        r = Group.objects.queued('12345')
        self.assertEqual(len(r), 3)

    @mock.patch.object(QuerySet, 'update')
    def test_dequeue(self, mock_update):
        dt = datetime.now()
        r = Group.objects.dequeue(Import(pk=1,
                                         priority=Group.PRIORITY_HIGH,
                                         canvas_state='imported',
                                         post_status=200,
                                         canvas_progress=100,
                                         monitor_date=dt))
        mock_update.assert_called_with(
            priority=Group.PRIORITY_DEFAULT, queue_id=None,
            provisioned_date=dt)

        r = Group.objects.dequeue(Import(pk=1, priority=Group.PRIORITY_HIGH))
        mock_update.assert_called_with(queue_id=None)

    @mock.patch.object(QuerySet, 'update')
    def test_dequeue_course(self, mock_update):
        r = Group.objects.dequeue_course('123')
        mock_update.assert_called_with(
            priority=Group.PRIORITY_DEFAULT, queue_id=None)

    @mock.patch.object(QuerySet, 'update')
    def test_deprioritize_course(self, mock_update):
        r = Group.objects.deprioritize_course('123')
        mock_update.assert_called_with(priority=Group.PRIORITY_NONE,
                                       queue_id=None)

    @mock.patch('sis_provisioner.models.group.datetime')
    @mock.patch.object(QuerySet, 'update')
    def test_delete_group_not_found(self, mock_update, mock_dt):
        mock_dt.utcnow = mock.Mock(return_value=datetime(2015, 1, 23))
        r = Group.objects.delete_group_not_found('u_does_not_exist')
        mock_update.assert_called_with(
            is_deleted=True, deleted_by='gws',
            deleted_date=datetime(2015, 1, 23, tzinfo=tz.tzutc()))
