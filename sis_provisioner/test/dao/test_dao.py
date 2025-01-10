# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.test import TestCase
from sis_provisioner.dao import titleize


class DaoTest(TestCase):
    def test_titleize(self):
        self.assertRaises(TypeError, titleize, None)
        self.assertEqual(titleize(123), '123')
        self.assertEqual(titleize(''), '')
        self.assertEqual(titleize('the'), 'The')
        self.assertEqual(titleize('THE'), 'The')
        self.assertEqual(titleize('the xml'), 'The XML')
        self.assertEqual(titleize('the    xml'), 'The    XML')
        self.assertEqual(titleize('the:xml'), 'The:XML')
        self.assertEqual(titleize('the-xml'), 'The-XML')
        self.assertEqual(titleize('the.xml'), 'The.XML')
        self.assertEqual(titleize('the&xml'), 'The&XML')
        self.assertEqual(titleize('the i'), 'The I')
        self.assertEqual(titleize('THE II'), 'The II')
        self.assertEqual(titleize('THE Iii'), 'The III')
        self.assertEqual(titleize('THE Iv'), 'The IV')
        self.assertEqual(titleize('the (now)'), 'The (Now)')
        self.assertEqual(titleize('joe\'s xml'), 'Joe\'s XML')
        self.assertEqual(titleize('xml/Xml'), 'XML/XML')
        self.assertEqual(titleize('the "xml"'), 'The "XML"')
        self.assertEqual(titleize('the "now"'), 'The "Now"')
