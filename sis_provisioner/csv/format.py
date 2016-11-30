from sis_provisioner.dao.account import account_name
from sis_provisioner.dao.term import term_sis_id, term_name,\
    term_start_date, term_end_date
from sis_provisioner.dao.course import is_active_section, section_short_name,\
    section_long_name, group_section_sis_id, group_section_name
from sis_provisioner.dao.user import user_sis_id, user_email, user_fullname
from sis_provisioner.models import Curriculum, Enrollment
from sis_provisioner.exceptions import EnrollmentPolicyException
import StringIO
import csv


class CSVFormat(object):
    def __init__(self):
        self.key = None
        self.data = []

    def __str__(self):
        """
        Creates a line of csv data from the obj data attribute
        """
        s = StringIO.StringIO()

        csv.register_dialect('unix_newline', lineterminator='\n')
        csv.writer(s, dialect='unix_newline').writerow(self.data)

        line = s.getvalue()
        s.close()
        return line


# CSV Header classes
class AccountHeader(CSVFormat):
    def __init__(self):
        self.data = ['account_id', 'parent_account_id', 'name', 'status']


class TermHeader(CSVFormat):
    def __init__(self):
        self.data = ['term_id', 'name', 'status', 'start_date', 'end_date']


class CourseHeader(CSVFormat):
    def __init__(self):
        self.data = ['course_id', 'short_name', 'long_name', 'account_id',
                     'term_id', 'status', 'start_date', 'end_date']


class SectionHeader(CSVFormat):
    def __init__(self):
        self.data = ['section_id', 'course_id', 'name', 'status',
                     'start_date', 'end_date']


class EnrollmentHeader(CSVFormat):
    def __init__(self):
        self.data = ['course_id', 'root_account', 'user_id', 'role',
                     'role_id', 'section_id', 'status', 'associated_user_id']


class UserHeader(CSVFormat):
    def __init__(self):
        self.data = ['user_id', 'login_id', 'password', 'first_name',
                     'last_name', 'full_name', 'sortable_name', 'short_name',
                     'email', 'status']


class XlistHeader(CSVFormat):
    def __init__(self):
        self.data = ['xlist_course_id', 'section_id', 'status']


# CSV Data classes
class AccountCSV(CSVFormat):
    """
    account_id, parent_account_id, name, status (active|deleted)
    """
    def __init__(self, account_id, parent_id, context, status='active'):
        self.key = account_id
        self.data = [account_id,
                     parent_id,
                     account_name(context),
                     status]


class TermCSV(CSVFormat):
    """
    term_id, name, status (active|deleted), start_date, end_date
    """
    def __init__(self, section, status='active'):
        self.key = term_sis_id(section)
        self.data = [self.key,
                     term_name(section),
                     status,
                     term_start_date(section),
                     term_end_date(section)]


class CourseCSV(CSVFormat):
    """
    course_id, short_name, long_name, account_id, term_id,
    status (active|deleted|completed), start_date, end_date
    """
    def __init__(self, section):
        self.key = section.canvas_course_sis_id()
        self.data = [self.key,
                     section_short_name(section),
                     section_long_name(section),
                     Curriculum.objects.canvas_account_id(section),
                     term_sis_id(section),
                     'active' if is_active_section(section) else 'deleted',
                     None, None]


class SectionCSV(CSVFormat):
    """
    section_id, course_id, name, status (active|deleted), start_date, end_date
    """
    def __init__(self, section):
        self.key = section.canvas_section_sis_id()
        self.data = [self.key,
                     section.canvas_course_sis_id(),
                     section_short_name(section),
                     'active' if is_active_section(section) else 'deleted',
                     None, None]


class GroupSectionCSV(CSVFormat):
    """
    section_id, course_id, name, status (active|deleted), start_date, end_date
    """
    def __init__(self, course_id, status='active'):
        self.key = group_section_sis_id(course_id)
        self.data = [self.key, course_id, group_section_name(), status,
                     None, None]


class EnrollmentCSV(CSVFormat):
    """
    course_id, root_account, user_id, role, role_id, section_id,
    status (active|inactive|deleted|completed), associated_user_id
    """
    def __init__(self, section_id, user, role, status):
        user_id = user_sis_id(user)
        if not any(status == val for (val, name) in Enrollment.STATUS_CHOICES):
            raise EnrollmentPolicyException(
                'Invalid enrollment status for %s: %s' % (user_id, status))

        self.data = [None, None, user_id, role, None, section_id, status, None]


class StudentEnrollmentCSV(EnrollmentCSV):
    def __init__(self, registration):
        if registration.is_active:
            status = Enrollment.ACTIVE_STATUS
        else:
            status = Enrollment.DELETED_STATUS

        super(StudentEnrollmentCSV, self).__init__(
            registration.section.canvas_section_sis_id(),
            registration.person,
            Enrollment.STUDENT_ROLE,
            status)


class InstructorEnrollmentCSV(EnrollmentCSV):
    def __init__(self, section, user, status):
        super(InstructorEnrollmentCSV, self).__init__(
            section.canvas_section_sis_id(), user, Enrollment.INSTRUCTOR_ROLE,
            status)


class UserCSV(CSVFormat):
    """
    user_id, login_id, password, first_name, last_name, full_name,
    sortable_name, short_name, email, status (active|deleted)
    """
    def __init__(self, user, status='active'):
        self.key = user_sis_id(user)
        self.data = [
            self.key,
            user.uwnetid if hasattr(user, 'uwnetid') else user.login_id,
            None, None, None,
            user_fullname(user),
            None, None,
            user_email(user),
            status]


class XlistCSV(CSVFormat):
    """
    xlist_course_id, section_id, status (active|deleted)
    """
    def __init__(self, course_id, section_id, status='active'):
        self.data = [course_id, section_id, status]
