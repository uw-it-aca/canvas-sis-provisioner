from django.test import TestCase
from django.db.models.query import QuerySet
from datetime import datetime
from sis_provisioner.models import (
    CourseMember, Import, PRIORITY_NONE, PRIORITY_DEFAULT, PRIORITY_HIGH)
import mock


class CourseMemberModelTest(TestCase):
    @mock.patch.object(QuerySet, 'filter')
    def test_dequeue_imported(self, mock_filter):
        dt = datetime.now()
        r = CourseMember.objects.dequeue(Import(pk=1,
                                                priority=PRIORITY_HIGH,
                                                canvas_state='imported',
                                                post_status=200,
                                                canvas_progress=100,
                                                monitor_date=dt))

        mock_filter.assert_called_with(queue_id=1, priority__gt=PRIORITY_NONE)

    @mock.patch.object(QuerySet, 'update')
    def test_dequeue_not_imported(self, mock_update):
        r = CourseMember.objects.dequeue(Import(pk=1, priority=PRIORITY_HIGH))
        mock_update.assert_called_with(queue_id=None)
