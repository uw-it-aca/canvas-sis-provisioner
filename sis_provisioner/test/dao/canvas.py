from django.test import TestCase
from sis_provisioner.dao.canvas import *
import mock


class CanvasIDTest(TestCase):
    @mock.patch.object(Canvas, 'valid_canvas_id')
    def test_valid_canvas_id(self, mock_method):
        r = valid_canvas_id('abc')
        mock_method.assert_called_with('abc')


class CanvasAccountsTest(TestCase):
    @mock.patch.object(Accounts, 'get_account')
    def test_get_account_by_id(self, mock_method):
        r = get_account_by_id('abc')
        mock_method.assert_called_with('abc')

    @mock.patch.object(Accounts, 'get_account_by_sis_id')
    def test_get_account_by_sis_id(self, mock_method):
        r = get_account_by_sis_id('abc')
        mock_method.assert_called_with('abc')

    @mock.patch.object(Accounts, 'get_all_sub_accounts')
    def test_get_all_sub_accounts(self, mock_method):
        r = get_all_sub_accounts('abc')
        mock_method.assert_called_with('abc')


class CanvasRolesTest(TestCase):
    @mock.patch.object(Roles, 'get_effective_course_roles_in_account')
    def test_get_course_roles_in_account(self, mock_method):
        r = get_course_roles_in_account('abc')
        mock_method.assert_called_with('abc')


class CanvasUsersTest(TestCase):
    @mock.patch.object(Users, 'get_user_by_sis_id')
    def test_get_user_by_sis_id(self, mock_method):
        r = get_user_by_sis_id('abc')
        mock_method.assert_called_with('abc')

    @mock.patch.object(Users, 'create_user')
    def test_create_user(self, mock_method):
        r = create_user('abc')
        mock_method.assert_called_with('abc')


class CanvasCoursesTest(TestCase):
    @mock.patch.object(Courses, 'get_course')
    def test_get_course_by_id(self, mock_method):
        r = get_course_by_id('abc')
        mock_method.assert_called_with('abc')

    @mock.patch.object(Courses, 'get_course_by_sis_id')
    def test_get_course_by_sis_id(self, mock_method):
        r = get_course_by_sis_id('abc')
        mock_method.assert_called_with('abc')

    @mock.patch.object(Courses, 'update_sis_id')
    def test_update_course_sis_id(self, mock_method):
        r = update_course_sis_id('abc', 'def')
        mock_method.assert_called_with('abc', 'def')


class CanvasSectionsTest(TestCase):
    @mock.patch.object(Sections, 'get_sections_in_course_by_sis_id')
    def test_get_sis_sections_for_course(self, mock_method):
        r = get_sis_sections_for_course('abc')
        mock_method.assert_called_with('abc')
        self.assertEquals(len(r), 0)


class CanvasTermsTest(TestCase):
    @mock.patch.object(Terms, 'get_term_by_sis_id')
    def test_get_term_by_sis_id(self, mock_method):
        r = get_term_by_sis_id('abc') 
        mock_method.assert_called_with('abc')

    @mock.patch.object(Terms, 'update_term_overrides')
    def test_update_term_overrides(self, mock_method):
        r = update_term_overrides('abc', {'xyz': ('somedate', 'anotherdate')})
        mock_method.assert_called_with(
            'abc', overrides={'xyz': {'start_at': 'somedate', 'end_at': 'anotherdate'}})


class CanvasEnrollmentsTest(TestCase):
    @mock.patch.object(Enrollments, 'get_enrollments_for_section')
    @mock.patch.object(Sections, 'get_sections_in_course_by_sis_id')
    def test_get_sis_enrollments_for_course(self, mock_sections, mock_enrollments):
        r = get_sis_enrollments_for_course('abc')
        mock_sections.assert_called_with('abc')
        self.assertEquals(len(r), 0)

    @mock.patch.object(Enrollments, 'get_enrollments_for_course_by_sis_id')
    def test_get_sis_enrollments_for_user_in_course(self, mock_method):
        r = get_sis_enrollments_for_user_in_course('abc', 'def')
        mock_method.assert_called_with('def', {'user_id': 'sis_user_id%3Aabc'})
        self.assertEquals(len(r), 0)


class CanvasReportsTest(TestCase):
    def test_get_active_courses_for_term(self):
        pass


class CanvasSISImportsTest(TestCase):
    @mock.patch.object(SISImport, 'import_dir')
    def test_sis_import_by_path(self, mock_method):
        r = sis_import_by_path('/abc')
        mock_method.assert_called_with('/abc')

    @mock.patch('sis_provisioner.dao.canvas.SISImportModel')
    @mock.patch.object(SISImport, 'get_import_status')
    def test_get_sis_import_status(self, mock_method, mock_model):
        r = get_sis_import_status('123')
        mock_model.assert_called_with(import_id='123')
