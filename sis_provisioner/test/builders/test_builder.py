from django.test import TestCase
from uw_sws.util import fdao_sws_override
from uw_pws.util import fdao_pws_override
from sis_provisioner.builders import Builder
from sis_provisioner.csv.data import Collector
from sis_provisioner.exceptions import CoursePolicyException
from restclients_core.exceptions import DataFailureException


@fdao_sws_override
@fdao_pws_override
class BuilderTest(TestCase):
    def test_builder(self):
        builder = Builder()

        self.assertEquals(type(builder.data), Collector)
        self.assertEquals(builder.queue_id, None)
        self.assertEquals(len(builder.invalid_users), 0)
        self.assertEquals(builder.build(), None)
        self.assertRaises(NotImplementedError, builder._process, True)

    def test_get_section_resource_by_id(self):
        builder = Builder()

        # OK
        section = builder.get_section_resource_by_id(
            '2013-winter-DROP_T-100-B')
        self.assertEqual(section.section_label(), '2013,winter,DROP_T,100/B')

        # 404 Not Found
        self.assertRaises(DataFailureException,
                          builder.get_section_resource_by_id,
                          '2013-winter-FAKE-999-A')

        # Invalid ID
        self.assertRaises(CoursePolicyException,
                          builder.get_section_resource_by_id,
                          '2013-winter-AAA-BBB')
