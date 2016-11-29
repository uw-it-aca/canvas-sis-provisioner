from django.test import TestCase
from sis_provisioner.csv.data import Collector


class CSVDataTest(TestCase):
    def test_accounts(self):
        key = '12345'

        csv = Collector()
        self.assertEquals(len(csv.accounts), 0)
        self.assertEquals(csv.has_account(key), False)

        csv.add_account(key, None)
        self.assertEquals(len(csv.accounts), 1)
        self.assertEquals(csv.has_account(key), True)

    def test_terms(self):
        key = 'spring-2013'

        csv = Collector()
        self.assertEquals(len(csv.terms), 0)
        self.assertEquals(csv.has_term(key), False)

        csv.add_term(key, None)
        self.assertEquals(len(csv.terms), 1)
        self.assertEquals(csv.has_term(key), True)

    def test_courses(self):
        key = 'spring-2013-TRAIN-101-A'

        csv = Collector()
        self.assertEquals(len(csv.courses), 0)
        self.assertEquals(csv.has_course(key), False)

        csv.add_course(key, None)
        self.assertEquals(len(csv.courses), 1)
        self.assertEquals(csv.has_course(key), True)

    def test_sections(self):
        key = 'spring-2013-TRAIN-101-AB'

        csv = Collector()
        self.assertEquals(len(csv.sections), 0)
        self.assertEquals(csv.has_section(key), False)

        csv.add_section(key, None)
        self.assertEquals(len(csv.sections), 1)
        self.assertEquals(csv.has_section(key), True)

    def test_enrollments(self):
        csv = Collector()
        self.assertEquals(len(csv.enrollments), 0)

        csv.add_enrollment(None)
        self.assertEquals(len(csv.enrollments), 1)

    def test_xlists(self):
        csv = Collector()
        self.assertEquals(len(csv.xlists), 0)

        csv.add_xlist(None)
        self.assertEquals(len(csv.xlists), 1)

    def test_users(self):
        key = '12345'

        csv = Collector()
        self.assertEquals(len(csv.users), 0)
        self.assertEquals(csv.has_user(key), False)

        csv.add_user(key, None)
        self.assertEquals(len(csv.users), 1)
        self.assertEquals(csv.has_user(key), True)

    def test_write_files(self):
        pass
