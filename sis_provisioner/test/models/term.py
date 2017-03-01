from django.test import TestCase
from django.db.models.query import QuerySet
from sis_provisioner.models import (
    Term, Import, PRIORITY_NONE, PRIORITY_DEFAULT, PRIORITY_HIGH)
from datetime import datetime
import mock


class TermModelTest(TestCase):
    @mock.patch.object(QuerySet, 'update')
    def test_dequeue(self, mock_update):
        dt = datetime.now()
        r = Term.objects.dequeue(Import(pk=1,
                                         priority=PRIORITY_HIGH,
                                         canvas_state='imported',
                                         post_status=200,
                                         canvas_progress=100,
                                         monitor_date=dt))
        mock_update.assert_called_with(
            queue_id=None, deleted_unused_courses_date=dt)
