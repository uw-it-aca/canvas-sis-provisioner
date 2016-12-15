from django.test import TestCase
from sis_provisioner.builders import Builder
from sis_provisioner.csv.data import Collector


class BuilderTest(TestCase):
    def test_builder(self):
        builder = Builder()

        self.assertEquals(type(builder.data), Collector)
        self.assertEquals(builder.queue_id, None)
        self.assertEquals(len(builder.invalid_users), 0)
        self.assertEquals(builder.write(), None)
        self.assertEquals(builder.build(), None)
        self.assertRaises(NotImplementedError, builder._process, True)
