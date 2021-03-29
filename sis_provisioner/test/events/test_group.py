# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
from sis_provisioner.events.group.dispatch import (
    Dispatch, CourseGroupDispatch)
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
