from django.test import TestCase
from sis_provisioner.models import Import, User


class ImportModelTest(TestCase):
    def test_is_completed(self):
        imp = Import()
        self.assertEquals(imp.is_completed(), False)

        imp = Import(post_status=200, canvas_progress=10)
        self.assertEquals(imp.is_completed(), False)

        imp = Import(post_status=200, canvas_progress=100)
        self.assertEquals(imp.is_completed(), True)

    def test_is_cleanly_imported(self):
        imp = Import()
        self.assertEquals(imp.is_cleanly_imported(), False)

        imp = Import(post_status=200, canvas_progress=100)
        self.assertEquals(imp.is_cleanly_imported(), False)

        imp = Import(
            post_status=200, canvas_progress=100,
            canvas_state='imported_with_messages',
            canvas_warnings='[["users.csv", "oops"]]')
        self.assertEquals(imp.is_cleanly_imported(), False)

        imp = Import(
            post_status=200, canvas_progress=100,
            canvas_state='imported_with_messages')
        self.assertEquals(imp.is_cleanly_imported(), True)

        imp = Import(
            post_status=200, canvas_progress=100, canvas_state='imported')
        self.assertEquals(imp.is_cleanly_imported(), True)

    def test_is_imported(self):
        imp = Import()
        self.assertEquals(imp.is_imported(), False)

        imp = Import(post_status=200, canvas_progress=100)
        self.assertEquals(imp.is_imported(), False)

        imp = Import(
            post_status=200, canvas_progress=100,
            canvas_state='imported_with_messages')
        self.assertEquals(imp.is_imported(), True)

        imp = Import(
            post_status=200, canvas_progress=100, canvas_state='imported')
        self.assertEquals(imp.is_imported(), True)

    def test_dependent_model(self):
        imp = Import()
        self.assertRaises(KeyError, imp.dependent_model)

        imp = Import(csv_type='fake')
        self.assertRaises(KeyError, imp.dependent_model)

        imp = Import(csv_type='user')
        self.assertEquals(imp.dependent_model(), User)

    def test_process_warnings(self):
        imp = Import()

        empty_warning = []
        one_warning = [['users.csv', 'oops']]
        two_warnings = [['users.csv', 'oops'], [
            'courses.csv',
            '2013-spring-MSIS-550-B--, Course is not a valid course']]

        self.assertEqual(imp._process_warnings(empty_warning), None)
        self.assertEqual(imp._process_warnings(one_warning), one_warning)
        self.assertEqual(imp._process_warnings(two_warnings), one_warning)
