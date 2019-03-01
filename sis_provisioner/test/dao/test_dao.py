from django.test import TestCase, override_settings
from django.utils.timezone import utc, localtime
from sis_provisioner.dao import titleize, localize
from datetime import datetime


class DaoTest(TestCase):
    def test_titleize(self):
        self.assertRaises(TypeError, titleize, None)
        self.assertEquals(titleize(123), '123')
        self.assertEquals(titleize(''), '')
        self.assertEquals(titleize('abc'), 'Abc')
        self.assertEquals(titleize('ABC'), 'Abc')
        self.assertEquals(titleize('abc def'), 'Abc Def')
        self.assertEquals(titleize('abc    def'), 'Abc    Def')
        self.assertEquals(titleize('abc:def'), 'Abc:Def')
        self.assertEquals(titleize('abc-def'), 'Abc-Def')
        self.assertEquals(titleize('abc.def'), 'Abc.Def')
        self.assertEquals(titleize('abc&def'), 'Abc&Def')
        self.assertEquals(titleize('UW abc'), 'UW Abc')
        self.assertEquals(titleize('ABC I'), 'Abc I')
        self.assertEquals(titleize('ABC II'), 'Abc II')
        self.assertEquals(titleize('ABC III'), 'Abc III')
        self.assertEquals(titleize('ABC IV'), 'Abc IV')
        self.assertEquals(titleize('abc (DEF)'), 'Abc (Def)')
        self.assertEquals(titleize('abc\'s def'), 'Abc\'s Def')

    @override_settings(TIME_ZONE='America/Los_Angeles')
    def test_localize(self):
        self.assertRaises(AttributeError, localize, None)

        dt = datetime(2013, 1, 1)
        self.assertEquals(str(localize(dt)), '2013-01-01 00:00:00-08:00')

        dt = datetime(2013, 1, 1).replace(tzinfo=utc)
        self.assertEquals(str(localize(dt)), '2012-12-31 16:00:00-08:00')
