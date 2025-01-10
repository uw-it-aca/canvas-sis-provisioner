# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.test import TestCase, override_settings
from sis_provisioner.dao.canvas import *
from sis_provisioner.dao.course import get_section_by_label
from uw_pws import PWS
from uw_pws.util import fdao_pws_override
from uw_sws.util import fdao_sws_override
from uw_sws.models import Registration
from datetime import datetime
from unittest.mock import ANY
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


class CanvasExternalToolsTest(TestCase):
    @mock.patch.object(ExternalTools, 'get_external_tools_in_account')
    def test_get_external_tools(self, mock_method):
        r = get_external_tools('abc')
        mock_method.assert_called_with('abc')

    @mock.patch.object(ExternalTools, 'create_external_tool_in_account')
    def test_create_external_tool(self, mock_method):
        r = create_external_tool('123', {'name': 'abc'})
        mock_method.assert_called_with('123', {'name': 'abc'})

        r = create_external_tool('123', {'id': '321', 'name': 'abc'})
        mock_method.assert_called_with('123', {'name': 'abc'})

    @mock.patch.object(ExternalTools, 'update_external_tool_in_account')
    def test_update_external_tool(self, mock_method):
        r = update_external_tool('123', '456', {'name': 'abc'})
        mock_method.assert_called_with('123', '456', {'name': 'abc'})

    @mock.patch.object(ExternalTools, 'delete_external_tool_in_account')
    def test_delete_external_tool(self, mock_method):
        r = delete_external_tool('123', '456')
        mock_method.assert_called_with('123', '456')


class CanvasRolesTest(TestCase):
    @mock.patch.object(Roles, 'get_effective_course_roles_in_account')
    @override_settings(RESTCLIENTS_CANVAS_ACCOUNT_ID='12345',
                       CONTINUUM_CANVAS_ACCOUNT_ID='50000')
    def test_get_course_roles_in_account(self, mock_method):
        r = get_course_roles_in_account('')
        mock_method.assert_called_with('12345')

        r = get_course_roles_in_account('uwcourse:abc')
        mock_method.assert_called_with('12345')

        r = get_course_roles_in_account('uwcourse:uweo:abc')
        mock_method.assert_called_with('50000')

    @mock.patch.object(Roles, 'get_roles_in_account')
    def test_get_account_role_data(self, mock_method):
        r = get_account_role_data('12345')
        mock_method.assert_called_with('12345')


class CanvasAdminsTest(TestCase):
    @mock.patch.object(Admins, 'get_admins')
    def test_get_admins(self, mock_method):
        r = get_admins('12345')
        mock_method.assert_called_with('12345')

    @mock.patch.object(Admins, 'delete_admin')
    def test_delete_admin(self, mock_method):
        r = delete_admin('12345', 'javerage', 'accountadmin')
        mock_method.assert_called_with('12345', 'javerage', 'accountadmin')


@fdao_pws_override
class CanvasUsersTest(TestCase):
    @mock.patch.object(Users, 'get_user_by_sis_id')
    def test_get_user_by_sis_id(self, mock_method):
        r = get_user_by_sis_id('abc')
        mock_method.assert_called_with('abc', params={})

    @mock.patch.object(Users, 'get_user_by_sis_id')
    def test_get_all_users_for_person(self, mock_method):
        person = PWS().get_person_by_netid('javerage')
        r = get_all_users_for_person(person)
        mock_method.assert_called_with('9136CCB8F66711D5BE060004AC494FF0',
                                       params={'include': 'last_login'})

    @mock.patch.object(Users, 'create_user')
    def test_create_user(self, mock_method):
        r = create_user('abc')
        mock_method.assert_called_with('abc')


class CanvasCoursesTest(TestCase):
    @mock.patch.object(Courses, 'get_course')
    def test_get_course_by_id(self, mock_method):
        r = get_course_by_id('abc')
        mock_method.assert_called_with('abc', {})

        r = get_course_by_id('abc', {'a': 'test'})
        mock_method.assert_called_with('abc', {'a': 'test'})

    @mock.patch.object(Courses, 'get_course_by_sis_id')
    def test_get_course_by_sis_id(self, mock_method):
        r = get_course_by_sis_id('abc')
        mock_method.assert_called_with('abc', {})

        r = get_course_by_sis_id('abc', {'d': 123})
        mock_method.assert_called_with('abc', {'d': 123})

    @mock.patch.object(Courses, 'update_sis_id')
    def test_update_course_sis_id(self, mock_method):
        r = update_course_sis_id('abc', 'def')
        mock_method.assert_called_with('abc', 'def')


class CanvasSectionsTest(TestCase):
    @mock.patch.object(Sections, 'get_sections_in_course_by_sis_id')
    def test_get_sis_sections_for_course(self, mock_method):
        r = get_sis_sections_for_course('abc')
        mock_method.assert_called_with('abc')
        self.assertEqual(len(r), 0)


class CanvasTermsTest(TestCase):
    @mock.patch.object(Terms, 'get_term_by_sis_id')
    def test_get_term_by_sis_id(self, mock_method):
        r = get_term_by_sis_id('abc')
        mock_method.assert_called_with('abc')

    @mock.patch.object(Terms, 'update_term_overrides')
    def test_update_term_overrides(self, mock_method):
        r = update_term_overrides('abc', {'xyz': {'start_at': 'somedate'}})
        mock_method.assert_called_with(
            'abc', overrides={'xyz': {'start_at': 'somedate'}})


@fdao_sws_override
@fdao_pws_override
class CanvasEnrollmentsTest(TestCase):
    def test_valid_enrollment_status(self):
        self.assertEqual(valid_enrollment_status('active'), True)
        self.assertEqual(valid_enrollment_status('inactive'), True)
        self.assertEqual(valid_enrollment_status('deleted'), True)
        self.assertEqual(valid_enrollment_status('abc'), False)
        self.assertEqual(valid_enrollment_status(None), False)
        self.assertEqual(valid_enrollment_status(4), False)

    def test_status_from_registration(self):
        section = get_section_by_label('2013,winter,DROP_T,100/B')

        reg = Registration(section=section,
                           is_active=True)
        self.assertEqual(enrollment_status_from_registration(reg), 'active')

        reg = Registration(section=section,
                           is_active=False,
                           request_date=section.term.last_day_instruction)
        self.assertEqual(enrollment_status_from_registration(reg), 'inactive')

        reg = Registration(section=section,
                           is_active=False,
                           request_status='Added to Standby')
        self.assertEqual(enrollment_status_from_registration(reg), 'active')

        reg = Registration(section=section,
                           is_active=False,
                           request_status='PENDING ADDED TO CLASS')
        self.assertEqual(enrollment_status_from_registration(reg), 'active')

        # request_date equals term.first_day_quarter
        reg = Registration(section=section,
                           is_active=False,
                           request_date=section.term.first_day_quarter)
        self.assertEqual(enrollment_status_from_registration(reg), 'deleted')

        # request_date equals term.census_day
        reg = Registration(section=section,
                           is_active=False,
                           request_date=section.term.census_day)
        self.assertEqual(enrollment_status_from_registration(reg), 'deleted')

    @mock.patch.object(Enrollments, 'get_enrollments_for_course_by_sis_id')
    def test_get_sis_enrollments_for_user_in_course(self, mock_method):
        r = get_sis_enrollments_for_user_in_course('abc', 'def')
        mock_method.assert_called_with('def', {'user_id': 'sis_user_id%3Aabc'})
        self.assertEqual(len(r), 0)

    @mock.patch.object(Enrollments, 'get_enrollments_for_regid')
    def test_get_active_sis_enrollments_for_user(self, mock_method):
        r = get_active_sis_enrollments_for_user('abc')
        mock_method.assert_called_with('abc', {'state': ['active']})
        self.assertEqual(len(r), 0)

        r = get_active_sis_enrollments_for_user('abc', roles=['testRole'])
        mock_method.assert_called_with('abc', {
            'state': ['active'], 'type': ['testRole']})
        self.assertEqual(len(r), 0)


class CanvasReportsTest(TestCase):
    def test_get_active_courses_for_term(self):
        pass


class CanvasSISImportsTest(TestCase):
    @mock.patch('sis_provisioner.dao.canvas.default_storage.listdir')
    @mock.patch.object(SISImport, 'import_archive')
    def test_sis_import_by_path(self, mock_method, mock_listdir):
        mock_listdir.return_value = ((), ())

        r = sis_import_by_path('abc')
        mock_method.assert_called_with(ANY, params={})

        r = sis_import_by_path('abc', override_sis_stickiness=True)
        mock_method.assert_called_with(
            ANY, params={'override_sis_stickiness': '1'})

    @mock.patch('sis_provisioner.dao.canvas.SISImportModel')
    @mock.patch.object(SISImport, 'get_import_status')
    def test_get_sis_import_status(self, mock_method, mock_model):
        r = get_sis_import_status('123')
        mock_model.assert_called_with(import_id='123')

    @mock.patch('sis_provisioner.dao.canvas.SISImportModel')
    @mock.patch.object(SISImport, 'delete_import')
    def test_delete_sis_import(self, mock_method, mock_model):
        r = delete_sis_import('123')
        mock_model.assert_called_with(import_id='123')
