from django.conf import settings
from sis_provisioner.csv.format import (
    AccountHeader, TermHeader, CourseHeader, SectionHeader, EnrollmentHeader,
    UserHeader, XlistHeader)
from datetime import datetime
import os
import errno
import stat
import shutil


class Collector(object):
    def __init__(self):
        self._init_data()

    def _init_data(self):
        self.accounts = []
        self.account_ids = {}
        self.terms = {}
        self.courses = {}
        self.sections = {}
        self.enrollments = []
        self.xlists = []
        self.users = {}
        self.headers = {
            'users': UserHeader(),
            'accounts': AccountHeader(),
            'terms': TermHeader(),
            'courses': CourseHeader(),
            'sections': SectionHeader(),
            'enrollments': EnrollmentHeader(),
            'xlists': XlistHeader(),
        }
        self.filemode = (stat.S_IRUSR | stat.S_IWUSR |
                         stat.S_IRGRP | stat.S_IWGRP |
                         stat.S_IROTH)

    def add_account(self, account_id, formatter):
        self.account_ids[account_id] = True
        self.accounts.append(formatter)

    def add_user(self, person_id, formatter):
        self.users[person_id] = formatter

    def add_term(self, term_id, formatter):
        self.terms[term_id] = formatter

    def add_course(self, course_id, formatter):
        self.courses[course_id] = formatter

    def add_section(self, section_id, formatter):
        self.sections[section_id] = formatter

    def add_enrollment(self, formatter):
        self.enrollments.append(formatter)

    def add_xlist(self, formatter):
        self.xlists.append(formatter)

    def has_account(self, key):
        return key in self.account_ids

    def has_course(self, key):
        return key in self.courses

    def has_section(self, key):
        return key in self.sections

    def has_term(self, key):
        return key in self.terms

    def has_user(self, key):
        return key in self.users

    def write_files(self):
        """
        Writes all csv files. Returns a path to the csv files, or None
        if no data was written.
        """
        root = getattr(settings, 'SIS_IMPORT_CSV_ROOT', '')
        filepath = self.filepath(root)
        has_csv = False
        for csv_type in self.headers:
            try:
                data = getattr(self, csv_type).values()
                data.sort()
            except AttributeError:
                data = getattr(self, csv_type)

            if len(data):
                has_csv = True
            else:
                continue

            filename = os.path.join(filepath, csv_type + '.csv')
            f = open(filename, 'w')
            os.chmod(filename, self.filemode)

            try:
                headers = self.headers[csv_type]
                f.write(str(headers))
                for line in data:
                    f.write(str(line))
            finally:
                f.close()

        if has_csv:
            self._init_data()
        else:
            shutil.rmtree(filepath)
            filepath = None

        if getattr(settings, 'SIS_IMPORT_CSV_DEBUG', False):
            print 'CSV PATH: %s' % filepath
        else:
            return filepath

    def filepath(self, root):
        """
        Create a fresh directory for the csv files
        """
        base = os.path.join(root, datetime.now().strftime('%Y%m%d-%H%M%S'))

        # ugo+x
        mode = self.filemode | (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        max_collisions = 100

        for collision in range(max_collisions):
            try:
                filepath = base if (
                    collision < 1) else '%s-%03d' % (base, collision)
                os.makedirs(filepath)
                os.chmod(filepath, mode)
                return filepath
            except OSError as err:
                if err.errno != errno.EEXIST:
                    raise

        raise Exception('Cannot create CSV dir: Too many attempts (%d)' % (
            max_collisions))
