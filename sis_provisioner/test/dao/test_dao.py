from django.test import TestCase, override_settings
from django.utils.timezone import utc, localtime
from sis_provisioner.dao import titleize, localize
from datetime import datetime


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

    @override_settings(TIME_ZONE='America/Los_Angeles')
    def test_localize(self):
        self.assertRaises(AttributeError, localize, None)

        dt = datetime(2013, 1, 1)
        self.assertEquals(str(localize(dt)), '2013-01-01 00:00:00-08:00')

        dt = datetime(2013, 1, 1).replace(tzinfo=utc)
        self.assertEquals(str(localize(dt)), '2012-12-31 16:00:00-08:00')
