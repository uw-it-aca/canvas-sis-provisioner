# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.test import TestCase, override_settings
from sis_provisioner.events.group.dispatch import (
    Dispatch, CourseGroupDispatch, LoginGroupDispatch,
    StudentLoginGroupDispatch, AffiliateLoginGroupDispatch,
    SponsoredLoginGroupDispatch)
import xml.etree.ElementTree as ET


class GroupDispatchTest(TestCase):
    def test_parser(self):
        self.assertIsInstance(
            Dispatch._parse(b'<group><user></user></group>'), ET.Element)
        self.assertIsInstance(
            Dispatch._parse(b'\n\n\n<group>\n\n\n</group>\n\n\n'), ET.Element)
        self.assertIsInstance(
            Dispatch._parse(b'abc<group></group>abc'), ET.Element)
        self.assertIsInstance(
            Dispatch._parse(b'<group></group>\x03\x03\x03'), ET.Element)
        self.assertIsInstance(
            Dispatch._parse(b'\n\n<group>\n</group>\n\n\x03\x03'), ET.Element)


class CourseGroupDispatchTest(TestCase):
    def test_mine(self):
        dispatch = CourseGroupDispatch(config={})
        self.assertEqual(dispatch.mine('course_2020win-art496a2'), True)
        self.assertEqual(dispatch.mine('course_2020win-mse700a'), True)
        self.assertEqual(dispatch.mine('course_2020win-mse700'), False)


class LoginGroupDispatchTest(TestCase):
    def test_group(self):
        dispatch = LoginGroupDispatch(config={})
        self.assertRaises(NotImplementedError, dispatch.group)
        self.assertRaises(NotImplementedError, dispatch.mine, 'u_test_group')

    def test_valid_member(self):
        dispatch = LoginGroupDispatch(config={})
        net_id = ''
        self.assertFalse(dispatch._valid_member(net_id),
                         'Does not raise exception')


@override_settings(ALLOWED_CANVAS_AFFILIATE_USERS='u_affiliate_test')
class AffiliateLoginGroupDispatchTest(TestCase):
    def test_group(self):
        dispatch = AffiliateLoginGroupDispatch(config={})
        self.assertEqual(dispatch.group(), 'u_affiliate_test')

    def test_mine(self):
        dispatch = AffiliateLoginGroupDispatch(config={})
        self.assertTrue(dispatch.mine('u_affiliate_test'))


@override_settings(ALLOWED_CANVAS_SPONSORED_USERS='u_sponsored_test')
class SponsoredLoginGroupDispatchTest(TestCase):
    def test_group(self):
        dispatch = SponsoredLoginGroupDispatch(config={})
        self.assertEqual(dispatch.group(), 'u_sponsored_test')

    def test_mine(self):
        dispatch = SponsoredLoginGroupDispatch(config={})
        self.assertTrue(dispatch.mine('u_sponsored_test'))


@override_settings(ALLOWED_CANVAS_STUDENT_USERS='u_student_test')
class StudentLoginGroupDispatchTest(TestCase):
    def test_group(self):
        dispatch = StudentLoginGroupDispatch(config={})
        self.assertEqual(dispatch.group(), 'u_student_test')

    def test_mine(self):
        dispatch = StudentLoginGroupDispatch(config={})
        self.assertTrue(dispatch.mine('u_student_test'))
