from django.test import TestCase
from django.db.models.query import QuerySet
from sis_provisioner.models import (
    Group, PRIORITY_NONE, PRIORITY_DEFAULT, PRIORITY_HIGH)
from datetime import datetime
import mock


class GroupModelTest(TestCase):
    @mock.patch.object(QuerySet, 'filter')
    def test_find_by_search(self, mock_filter):
        r = Group.objects.find_by_search(
            group_id='123', role='role', queue_id='345')
        mock_filter.assert_called_with(
            group_id='123', is_deleted__isnull=True, queue_id='345', role='role')

    @mock.patch.object(QuerySet, 'filter')
    def test_get_active_by_course(self, mock_filter):
        r = Group.objects.get_active_by_course('123')
        mock_filter.assert_called_with(course_id='123', is_deleted__isnull=True)

    @mock.patch.object(QuerySet, 'filter')
    def test_queued(self, mock_filter):
        r = Group.objects.queued('123')
        mock_filter.assert_called_with(queue_id='123')

    @mock.patch.object(QuerySet, 'update')
    def test_dequeue(self, mock_update):
        r = Group.objects.dequeue('123')
        mock_update.assert_called_with(queue_id=None)

        dt = datetime.now()
        r = Group.objects.dequeue('123', provisioned_date=dt)
        mock_update.assert_called_with(
            queue_id=None, priority=PRIORITY_DEFAULT, provisioned_date=dt)

    @mock.patch.object(QuerySet, 'update')
    def test_dequeue_course(self, mock_update):
        r = Group.objects.dequeue_course('123')
        mock_update.assert_called_with(
            priority=PRIORITY_DEFAULT, queue_id=None)

    @mock.patch.object(QuerySet, 'update')
    def test_deprioritize_course(self, mock_update):
        r = Group.objects.deprioritize_course('123')
        mock_update.assert_called_with(priority=PRIORITY_NONE, queue_id=None)