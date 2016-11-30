from django.conf import settings
from sis_provisioner.csv.format import *
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

    def add(self, formatter):
        """
        Add the passed csv formatter object based on type, returns True if
        the formatter is added, False otherwise.
        """
        if isinstance(formatter, UserCSV):
            return self._add_user(formatter)
        elif isinstance(formatter, (
                EnrollmentCSV, StudentEnrollmentCSV, InstructorEnrollmentCSV)):
            return self._add_enrollment(formatter)
        elif isinstance(formatter, AccountCSV):
            return self._add_account(formatter)
        elif isinstance(formatter, TermCSV):
            return self._add_term(formatter)
        elif isinstance(formatter, CourseCSV):
            return self._add_course(formatter)
        elif isinstance(formatter, (SectionCSV, GroupSectionCSV)):
            return self._add_section(formatter)
        elif isinstance(formatter, XlistCSV):
            return self._add_xlist(formatter)
        else:
            raise Exception('Unknown CSV format class %s' % type(formatter))

    def _add_account(self, formatter):
        if formatter.key not in self.account_ids:
            self.account_ids[formatter.key] = True
            self.accounts.append(formatter)
            return True
        return False

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
        self.enrollments.append(formatter)
        return True

    def _add_xlist(self, formatter):
        self.xlists.append(formatter)
        return True

    def write_files(self):
        """
        Writes all csv files. Returns a path to the csv files, or None
        if no data was written.
        """
        root = getattr(settings, 'SIS_IMPORT_CSV_ROOT', '')
        filepath = self.create_filepath(root)
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

    def create_filepath(self, root):
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
