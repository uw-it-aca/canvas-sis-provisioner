# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse
from django.contrib.sessions.middleware import SessionMiddleware
from sis_provisioner.views.admin import *
from sis_provisioner.exceptions import (
    MissingLoginIdException, InvalidLoginIdException)
from sis_provisioner.test.models.test_account import create_account
from sis_provisioner.test.models.test_admin import create_admin
from uw_pws.util import fdao_pws_override
from uw_sws.util import fdao_sws_override
from uw_gws.utilities import fdao_gws_override
from datetime import datetime
import mock


@fdao_pws_override
@fdao_sws_override
@fdao_gws_override
@override_settings(
    RESTCLIENTS_CANVAS_ACCOUNT_ID=123,
    RESTCLIENTS_ADMIN_GROUP='u_test_group',
    CANVAS_MANAGER_ADMIN_GROUP='u_acadev_unittest',
    MOCK_SAML_ATTRIBUTES={
        'uwnetid': ['javerage'],
        'isMemberOf': ['u_test_group', 'u_acadev_unittest']})
class AdminViewTest(TestCase):
    def setUp(self):
        account = create_account(123, 'test1')
        self.user = create_admin('javerage', account)

        self.request = RequestFactory().get(
            reverse('ImportStatus'), HTTP_HOST='example.uw.edu')
        get_response = mock.MagicMock()
        middleware = SessionMiddleware(get_response)
        response = middleware(self.request)
        self.request.session['samlUserdata'] = settings.MOCK_SAML_ATTRIBUTES
        self.request.session.save()

    def test_params(self):
        params = AdminView()._params(self.request)
        self.assertEqual(params['can_manage_admin_group'], True)
        self.assertEqual(params['can_view_restclients'], True)
        self.assertEqual(params['can_manage_jobs'], True)
        self.assertEqual(params['can_manage_external_tools'], True)

    def test_can_view_source_data(self):
        self.assertTrue(AdminView.can_view_source_data(self.request))

    def test_can_manage_admin_group(self):
        self.assertTrue(AdminView.can_manage_admin_group(self.request))

    def test_can_manage_jobs(self):
        self.assertTrue(AdminView.can_manage_jobs(self.request))

    def test_can_manage_external_tools(self):
        self.assertTrue(AdminView.can_manage_external_tools(self.request))

    def test_can_manage_course_expirations(self):
        self.assertTrue(AdminView.can_manage_course_expirations(self.request))

    def test_can_masquerade_as_user(self):
        self.assertTrue(AdminView.can_masquerade_as_user(
            self.request, 'jbothell'))
        self.assertFalse(AdminView.can_masquerade_as_user(
            self.request, 'javerage'))


class RestDispatchTest(TestCase):
    def test_error_response(self):
        response = RESTDispatch.error_response(400, message='Error')
        self.assertEqual(response.content, b'{"error": "Error"}')
        self.assertEqual(response.status_code, 400)

    def test_json_response(self):
        response = RESTDispatch.json_response('Test')
        self.assertEqual(response.content, b'"Test"')
        self.assertEqual(response.status_code, 200)

        response = RESTDispatch.json_response({'Test': 3, 'Another Test': 4})
        self.assertEqual(response.content, b'{"Another Test": 4, "Test": 3}')
        self.assertEqual(response.status_code, 200)

    def test_regid_from_request(self):
        self.assertEqual(
            RESTDispatch.regid_from_request(
                {'reg_id': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1'}),
            'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1')
        self.assertEqual(
            RESTDispatch.regid_from_request(
                {'reg_id': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1'}),
            'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1')
        self.assertEqual(
            RESTDispatch.regid_from_request(
                {'reg_id': '  aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1 '}),
            'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1')
        self.assertRaises(
            InvalidLoginIdException,
            RESTDispatch.regid_from_request, {'reg_id': ''})
        self.assertRaises(
            InvalidLoginIdException,
            RESTDispatch.regid_from_request, {'foo': ''})
        self.assertRaises(
            InvalidLoginIdException,
            RESTDispatch.regid_from_request,
            {'reg_id': 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXx1'})

    def test_netid_from_request(self):
        self.assertEqual(
            RESTDispatch.netid_from_request({'net_id': 'abc'}), 'abc')
        self.assertEqual(
            RESTDispatch.netid_from_request({'net_id': 'ABC'}), 'abc')
        self.assertEqual(
            RESTDispatch.netid_from_request({'net_id': '  abc '}), 'abc')
        self.assertRaises(
            MissingLoginIdException,
            RESTDispatch.netid_from_request, {'net_id': ''})
        self.assertRaises(
            MissingLoginIdException,
            RESTDispatch.netid_from_request, {'foo': ''})
        self.assertRaises(
            InvalidLoginIdException,
            RESTDispatch.netid_from_request, {'net_id': '123'})
