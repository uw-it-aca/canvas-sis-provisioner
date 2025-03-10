# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.test import TestCase
from sis_provisioner.models import Import, ImportResource
import mock


class ImportModelTest(TestCase):
    def test_is_completed(self):
        imp = Import()
        self.assertEqual(imp.is_completed(), False)

        imp = Import(post_status=200, canvas_progress=10)
        self.assertEqual(imp.is_completed(), False)

        imp = Import(post_status=200, canvas_progress=100)
        self.assertEqual(imp.is_completed(), True)

    def test_is_cleanly_imported(self):
        imp = Import()
        self.assertEqual(imp.is_cleanly_imported(), False)

        imp = Import(post_status=200, canvas_progress=100)
        self.assertEqual(imp.is_cleanly_imported(), False)

        imp = Import(
            post_status=200, canvas_progress=100,
            canvas_state='imported_with_messages',
            canvas_warnings='[["users.csv", "oops"]]')
        self.assertEqual(imp.is_cleanly_imported(), False)

        imp = Import(
            post_status=200, canvas_progress=100,
            canvas_state='imported_with_messages')
        self.assertEqual(imp.is_cleanly_imported(), True)

        imp = Import(
            post_status=200, canvas_progress=100, canvas_state='imported')
        self.assertEqual(imp.is_cleanly_imported(), True)

    def test_is_imported(self):
        imp = Import()
        self.assertEqual(imp.is_imported(), False)

        imp = Import(post_status=200, canvas_progress=100)
        self.assertEqual(imp.is_imported(), False)

        imp = Import(
            post_status=200, canvas_progress=100,
            canvas_state='imported_with_messages')
        self.assertEqual(imp.is_imported(), True)

        imp = Import(
            post_status=200, canvas_progress=100, canvas_state='imported')
        self.assertEqual(imp.is_imported(), True)

    def test_dependent_model(self):
        imp = Import()
        self.assertRaises(ImportError, imp.dependent_model)

        imp = Import(csv_type='fake')
        self.assertRaises(ImportError, imp.dependent_model)

        for csv_type in ['enrollment', 'user', 'course', 'admin', 'group']:
            imp = Import(csv_type=csv_type)
            self.assertTrue(issubclass(imp.dependent_model(), ImportResource))

    def test_type_name(self):
        imp = Import()
        self.assertEqual(imp.type_name, None)

        imp = Import(csv_type='fake')
        self.assertEqual(imp.type_name, 'fake')

        imp = Import(csv_type='course')
        self.assertEqual(imp.type_name, 'Course')

    def test_process_warnings(self):
        imp = Import()

        empty_warning = []
        one_warning = [['users.csv', 'oops']]
        two_warnings = [['users.csv', 'oops'], [
            'courses.csv',
            '2013-spring-MSIS-550-B--, Course is not a valid course']]

        self.assertEqual(imp._process_warnings(empty_warning), empty_warning)
        self.assertEqual(imp._process_warnings(one_warning), one_warning)
        self.assertEqual(imp._process_warnings(two_warnings), one_warning)

    @mock.patch('sis_provisioner.models.delete_sis_import')
    @mock.patch.object(Import, 'dequeue_dependent_models')
    def test_delete(self, mock_dequeue, mock_delete):
        imp = Import(canvas_id=123, post_status=200, canvas_progress=10)
        imp.save()
        imp.delete()
        mock_dequeue.assert_called_once()
        mock_delete.assert_called_with(imp.canvas_id)

        mock_dequeue.reset_mock()
        mock_delete.reset_mock()

        imp = Import(canvas_id=456, post_status=200, canvas_progress=100)
        imp.save()
        imp.delete()
        mock_dequeue.assert_called_once()
        mock_delete.assert_not_called()
