from django.test import TestCase, override_settings
from uw_pws import PWS
from uw_pws.util import fdao_pws_override
from uw_sws.util import fdao_sws_override
from sis_provisioner.models import Curriculum
from sis_provisioner.dao.course import (
    get_section_by_label, get_registrations_by_section)
from sis_provisioner.csv.data import Collector
from sis_provisioner.csv.format import *
import mock


class InvalidFormat(CSVFormat):
    pass


@fdao_sws_override
@fdao_pws_override
class CSVDataTest(TestCase):
    def test_accounts(self):
        context = Curriculum(full_name='abc')
        formatter = AccountCSV('account_id', 'parent_id', context)

        csv = Collector()
        self.assertEquals(len(csv.accounts), 0)
        self.assertEquals(csv.add(formatter), True)
        self.assertEquals(len(csv.accounts), 1)
        self.assertEquals(csv.add(formatter), False)
        self.assertEquals(csv.has_data(), True)

    def test_invalid_format(self):
        csv = Collector()
        self.assertRaises(TypeError, csv.add, InvalidFormat)
        self.assertEquals(csv.has_data(), False)

    def test_terms(self):
        section = get_section_by_label('2013,summer,TRAIN,101/A')
        formatter = TermCSV(section)

        csv = Collector()
        self.assertEquals(len(csv.terms), 0)
        self.assertEquals(csv.add(formatter), True)
        self.assertEquals(len(csv.terms), 1)
        self.assertEquals(csv.add(formatter), False)
        self.assertEquals(csv.has_data(), True)

    def test_admins(self):
        formatter = AdminCSV('user_id', 'account_id', 'admin', 'active')

        csv = Collector()
        self.assertEquals(len(csv.admins), 0)
        self.assertEquals(csv.add(formatter), True)
        self.assertEquals(len(csv.admins), 1)
        self.assertEquals(csv.has_data(), True)

    @override_settings(
        LMS_OWNERSHIP_SUBACCOUNT={'PCE_NONE': 'pce_none_account'})
    def test_courses(self):
        section = get_section_by_label('2013,spring,TRAIN,101/A')
        section.course_campus = 'PCE'
        formatter = CourseCSV(section=section)

        csv = Collector()
        self.assertEquals(len(csv.courses), 0)
        self.assertEquals(csv.add(formatter), True)
        self.assertEquals(len(csv.courses), 1)
        self.assertEquals(csv.add(formatter), False)
        self.assertEquals(csv.has_data(), True)

    def test_sections(self):
        section = get_section_by_label('2013,spring,TRAIN,101/A')
        formatter = SectionCSV(section=section)

        csv = Collector()
        self.assertEquals(len(csv.sections), 0)
        self.assertEquals(csv.add(formatter), True)
        self.assertEquals(len(csv.sections), 1)
        self.assertEquals(csv.add(formatter), False)
        self.assertEquals(
            csv.add(SectionCSV(
                section_id='abc', course_id='abc', name='abc',
                status='active')), True)
        self.assertEquals(len(csv.sections), 2)
        self.assertEquals(csv.has_data(), True)

    def test_enrollments(self):
        user = PWS().get_person_by_netid('javerage')

        csv = Collector()
        self.assertEquals(len(csv.enrollments), 0)
        self.assertEquals(
            csv.add(EnrollmentCSV(
                section_id='abc', person=user, role='Student',
                status='active')), True)
        self.assertEquals(len(csv.enrollments), 1)

        section = get_section_by_label('2013,winter,DROP_T,100/B')
        for registration in get_registrations_by_section(section):
            self.assertEquals(
                csv.add(EnrollmentCSV(registration=registration)), True)
        self.assertEquals(len(csv.enrollments), 3)

        section = get_section_by_label('2013,spring,TRAIN,101/A')
        for user in section.get_instructors():
            self.assertEquals(
                csv.add(EnrollmentCSV(
                    section=section, instructor=user, status='active')), True)

            # Duplicate
            self.assertEquals(
                csv.add(EnrollmentCSV(
                    section=section, instructor=user, status='active')), False)

        self.assertEquals(len(csv.enrollments), 5)
        self.assertEquals(csv.has_data(), True)

        # Ad-hoc enrollment
        self.assertEquals(csv.add(EnrollmentCSV(
            course_id='course_123', section_id='section_123',
            person=user, role='Observer', status='active')), True)
        self.assertEquals(len(csv.enrollments), 6)

        # Duplicate
        self.assertEquals(csv.add(EnrollmentCSV(
            course_id='course_123', section_id='section_123',
            person=user, role='Observer', status='active')), False)

    def test_xlists(self):
        csv = Collector()
        self.assertEquals(len(csv.xlists), 0)
        self.assertEquals(csv.add(XlistCSV('abc', 'def')), True)
        self.assertEquals(len(csv.xlists), 1)
        self.assertEquals(csv.has_data(), True)

    def test_users(self):
        user = PWS().get_person_by_netid('javerage')

        csv = Collector()
        self.assertEquals(len(csv.users), 0)
        self.assertEquals(csv.add(UserCSV(user, 'active')), True)
        self.assertEquals(len(csv.users), 1)
        self.assertEquals(csv.add(UserCSV(user, 'active')), False)
        self.assertEquals(csv.has_data(), True)

    @mock.patch('sis_provisioner.csv.data.stat')
    @mock.patch('sis_provisioner.csv.data.os')
    @mock.patch('sis_provisioner.csv.data.open')
    def test_write_files(self, mock_open, mock_os, mock_stat):
        # Test empty
        csv = Collector()
        self.assertEquals(csv.has_data(), False)
        self.assertEquals(csv.write_files(), None)

        # Test with data
        csv = Collector()
        csv.enrollments.append(1)
        self.assertEquals(csv.has_data(), True)

        with self.settings(SIS_IMPORT_CSV_DEBUG=False):
            path = csv.write_files()

            mock_os.path.join.assert_called_with(path, 'enrollments.csv')
            mock_open.assert_called_with(path, 'w')
            mock_os.chmod.assert_called_with(path, csv.filemode)
            self.assertEquals(csv.has_data(), False)

    @mock.patch('sis_provisioner.csv.data.stat')
    @mock.patch('sis_provisioner.csv.data.os')
    def test_create_filepath(self, mock_os, mock_stat):
        with self.settings(SIS_IMPORT_CSV_FILEPATH_COLLISIONS_MAX=1):
            csv = Collector()
            root = ''

            path = csv.create_filepath(root)

            mock_os.makedirs.assert_called_with(path)
            mock_os.chmod.assert_called_with(path, csv.dirmode)

        with self.settings(SIS_IMPORT_CSV_FILEPATH_COLLISIONS_MAX=0):
            csv = Collector()
            root = ''

            self.assertRaises(EnvironmentError, csv.create_filepath, root)
