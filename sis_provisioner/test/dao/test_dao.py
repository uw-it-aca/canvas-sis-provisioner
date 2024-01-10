# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.test import TestCase
from sis_provisioner.dao import titleize


class DaoTest(TestCase):
    def test_titleize(self):
        self.assertRaises(TypeError, titleize, None)
        self.assertEquals(titleize(123), '123')
        self.assertEquals(titleize(''), '')
        self.assertEquals(titleize('the'), 'The')
        self.assertEquals(titleize('THE'), 'The')
        self.assertEquals(titleize('the xml'), 'The XML')
        self.assertEquals(titleize('the    xml'), 'The    XML')
        self.assertEquals(titleize('the:xml'), 'The:XML')
        self.assertEquals(titleize('the-xml'), 'The-XML')
        self.assertEquals(titleize('the.xml'), 'The.XML')
        self.assertEquals(titleize('the&xml'), 'The&XML')
        self.assertEquals(titleize('the i'), 'The I')
        self.assertEquals(titleize('THE II'), 'The II')
        self.assertEquals(titleize('THE Iii'), 'The III')
        self.assertEquals(titleize('THE Iv'), 'The IV')
        self.assertEquals(titleize('the (now)'), 'The (Now)')
        self.assertEquals(titleize('joe\'s xml'), 'Joe\'s XML')
        self.assertEquals(titleize('xml/Xml'), 'XML/XML')
        self.assertEquals(titleize('the "xml"'), 'The "XML"')
        self.assertEquals(titleize('the "now"'), 'The "Now"')
