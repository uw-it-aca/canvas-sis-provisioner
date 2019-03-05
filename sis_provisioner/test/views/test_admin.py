from django.test import TestCase, override_settings
from sis_provisioner.views.admin import *
from sis_provisioner.exceptions import (
    MissingLoginIdException, InvalidLoginIdException)


class AdminViewTest(TestCase):
    def test_can_view_source_data(self):
        pass

    def test_can_manage_admin_group(self):
        pass

    def test_can_manage_jobs(self):
        pass

    def test_can_manage_external_tools(self):
        pass


class RestDispatchTest(TestCase):
    def test_error_response(self):
        pass

    def test_json_response(self):
        pass

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
