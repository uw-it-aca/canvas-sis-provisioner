from django.test import TestCase
from sis_provisioner.events.group.dispatch import Dispatch
import xml.etree.ElementTree as ET


class GroupDispatchTest(TestCase):
    def test_parser(self):
        self.assertIsInstance(
            Dispatch._parse(b'<group><user></user></group>'), ET.Element)
        self.assertIsInstance(
            Dispatch._parse(b'\n\n\n<group></group>\n\n\n'), ET.Element)
        self.assertIsInstance(
            Dispatch._parse(b'abc<group></group>abc'), ET.Element)
        self.assertIsInstance(
            Dispatch._parse(b'<group></group>\x03\x03\x03'), ET.Element)
        self.assertIsInstance(
            Dispatch._parse(b'\n\n\n<group></group>\n\n\x03\x03'), ET.Element)
