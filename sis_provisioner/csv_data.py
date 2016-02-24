from django.conf import settings
from sis_provisioner.csv_formatters import header_for_users,\
    header_for_accounts, header_for_terms, header_for_courses,\
    header_for_sections, header_for_enrollments, header_for_xlists
import StringIO
import csv
import os
import errno
import stat
import shutil
import re
import datetime


class CSVData():
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
            'users': header_for_users(),
            'accounts': header_for_accounts(),
            'terms': header_for_terms(),
            'courses': header_for_courses(),
            'sections': header_for_sections(),
            'enrollments': header_for_enrollments(),
            'xlists': header_for_xlists(),
        }
        self.filemode = (stat.S_IRUSR | stat.S_IWUSR |
                         stat.S_IRGRP | stat.S_IWGRP |
                         stat.S_IROTH)

    def add_account(self, account_id, csv_data):
        self.account_ids[account_id] = True
        self.accounts.append(csv_data)

    def add_user(self, person_id, csv_data):
        self.users[person_id] = csv_data

    def add_term(self, term_id, csv_data):
        self.terms[term_id] = csv_data

    def add_course(self, course_id, csv_data):
        self.courses[course_id] = csv_data

    def add_section(self, key, csv_data):
        self.sections[key] = csv_data

    def add_enrollment(self, csv_data):
        self.enrollments.append(csv_data)

    def add_xlist(self, csv_data):
        self.xlists.append(csv_data)

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

    def csv_line_from_data(self, data):
        """
        Creates a line of csv data from the passed list.
        """
        s = StringIO.StringIO()

        csv.register_dialect("unix_newline", lineterminator="\n")
        writer = csv.writer(s, dialect="unix_newline")
        try:
            writer.writerow(data)
        except UnicodeEncodeError:
            print "Caught unicode error: %s" % data

        line = s.getvalue()
        s.close()
        return line

    def write_files(self):
        """
        Writes all csv files. Returns a path to the csv files, or None
        if no data was written.
        """

        filepath = self.filepath()
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
                f.write(self.csv_line_from_data(headers))
                for line in data:
                    f.write(self.csv_line_from_data(line))
            finally:
                f.close()

        if has_csv:
            self._init_data()
        else:
            shutil.rmtree(filepath)
            filepath = None

        if settings.SIS_IMPORT_CSV_DEBUG:
            print "CSV PATH: %s" % filepath
        else:
            return filepath

    def filepath(self, root=settings.SIS_IMPORT_CSV_ROOT):
        """
        Create a fresh directory for the csv files
        """

        base = os.path.join(root,
                            datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))

        # ugo+x
        mode = self.filemode | (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        max_collisions = 100

        for collision in range(max_collisions):
            try:
                filepath = base if collision < 1 else '%s-%03d' % (base,
                                                                   collision)
                os.makedirs(filepath)
                os.chmod(filepath, mode)
                return filepath
            except OSError as err:
                if err.errno != errno.EEXIST:
                    raise

        raise Exception('Cannot create CSV dir: Too many attempts (%d)' % (
            max_collisions))
