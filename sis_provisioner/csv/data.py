from django.conf import settings
from django.core.files.storage import default_storage
from sis_provisioner.csv.format import (
    UserHeader, AccountHeader, AdminHeader, TermHeader, CourseHeader,
    SectionHeader, EnrollmentHeader, XlistHeader, UserCSV, AccountCSV,
    AdminCSV, TermCSV, CourseCSV, SectionCSV, EnrollmentCSV, XlistCSV)
from datetime import datetime
from logging import getLogger
import os

logger = getLogger(__name__)


class Collector(object):
    def __init__(self):
        self._init_data()

    def _init_data(self):
        self.accounts = []
        self.account_ids = {}
        self.admins = []
        self.terms = {}
        self.courses = {}
        self.sections = {}
        self.enrollments = []
        self.enrollment_keys = {}
        self.xlists = []
        self.users = {}
        self.headers = {
            'users': UserHeader(),
            'accounts': AccountHeader(),
            'admins': AdminHeader(),
            'terms': TermHeader(),
            'courses': CourseHeader(),
            'sections': SectionHeader(),
            'enrollments': EnrollmentHeader(),
            'xlists': XlistHeader(),
        }

    def add(self, formatter):
        """
        Add the passed csv formatter object based on type, returns True if
        the formatter is added, False otherwise.
        """
        if isinstance(formatter, UserCSV):
            return self._add_user(formatter)
        elif isinstance(formatter, EnrollmentCSV):
            return self._add_enrollment(formatter)
        elif isinstance(formatter, AccountCSV):
            return self._add_account(formatter)
        elif isinstance(formatter, AdminCSV):
            return self._add_admin(formatter)
        elif isinstance(formatter, TermCSV):
            return self._add_term(formatter)
        elif isinstance(formatter, CourseCSV):
            return self._add_course(formatter)
        elif isinstance(formatter, SectionCSV):
            return self._add_section(formatter)
        elif isinstance(formatter, XlistCSV):
            return self._add_xlist(formatter)
        else:
            raise TypeError(
                'Unknown CSVFormat class: {}'.format(type(formatter)))

    def _add_account(self, formatter):
        if formatter.key not in self.account_ids:
            self.account_ids[formatter.key] = True
            self.accounts.append(formatter)
            return True
        return False

    def _add_admin(self, formatter):
        self.admins.append(formatter)
        return True

    def _add_user(self, formatter):
        if formatter.key not in self.users:
            self.users[formatter.key] = formatter
            return True
        return False

    def _add_term(self, formatter):
        if formatter.key not in self.terms:
            self.terms[formatter.key] = formatter
            return True
        return False

    def _add_course(self, formatter):
        if formatter.key not in self.courses:
            self.courses[formatter.key] = formatter
            return True
        return False

    def _add_section(self, formatter):
        if formatter.key not in self.sections:
            self.sections[formatter.key] = formatter
            return True
        return False

    def _add_enrollment(self, formatter):
        if formatter.key not in self.enrollment_keys:
            self.enrollment_keys[formatter.key] = True
            self.enrollments.append(formatter)
            return True
        return False

    def _add_xlist(self, formatter):
        self.xlists.append(formatter)
        return True

    def has_data(self):
        """
        Returns True if the collector contains data, False otherwise.
        """
        for csv_type in self.headers:
            if len(getattr(self, csv_type)):
                return True
        return False

    def write_files(self):
        """
        Writes all csv files. Returns a path to the csv files, or None
        if no data was written.
        """
        filepath = None
        if self.has_data():
            filepath = datetime.now().strftime('%Y/%m/%d/%H%M%S-%f')
            for csv_type in self.headers:
                try:
                    data = list(getattr(self, csv_type).values())
                    data.sort()
                except AttributeError:
                    data = getattr(self, csv_type)

                if len(data):
                    filename = os.path.join(filepath, csv_type + '.csv')
                    f = default_storage.open(filename, mode='w')

                    try:
                        headers = self.headers[csv_type]
                        f.write(str(headers))
                        for line in data:
                            f.write(str(line))
                    finally:
                        f.close()

            self._init_data()

        if getattr(settings, 'SIS_IMPORT_CSV_DEBUG', False):
            logger.debug('CSV PATH: {}'.format(filepath))
            return None
        else:
            return filepath
