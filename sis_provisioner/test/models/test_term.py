# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from datetime import datetime, timezone
from unittest import mock

from django.db.models.query import QuerySet
from django.test import TestCase

from sis_provisioner.models import Import
from sis_provisioner.models.term import Term


class TermModelTest(TestCase):
    @mock.patch.object(QuerySet, 'update')
    def test_dequeue(self, mock_update):
        dt = datetime.now(timezone.utc)
        Term.objects.dequeue(Import(pk=1,
                                    priority=Term.PRIORITY_HIGH,
                                    canvas_state='imported',
                                    post_status=200,
                                    canvas_progress=100,
                                    monitor_date=dt))
        mock_update.assert_called_with(
            queue_id=None, deleted_unused_courses_date=dt)
