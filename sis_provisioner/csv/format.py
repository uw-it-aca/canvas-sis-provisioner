from sis_provisioner.dao.account import account_name, account_id_for_section
from sis_provisioner.dao.term import (
    term_sis_id, term_name, term_start_date, term_end_date)
from sis_provisioner.dao.course import (
    is_active_section, section_short_name, section_long_name)
from sis_provisioner.dao.user import user_sis_id, user_email, user_fullname
from sis_provisioner.dao.canvas import (
    valid_enrollment_status, enrollment_status_from_registration,
    INSTRUCTOR_ENROLLMENT, STUDENT_ENROLLMENT)
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
    def __init__(self, **kwargs):
        if kwargs.get('section'):
            section = kwargs.get('section')
            self.key = section.canvas_course_sis_id()
            self.data = [self.key,
                         section_short_name(section),
                         section_long_name(section),
                         account_id_for_section(section),
                         term_sis_id(section),
                         'active' if is_active_section(section) else 'deleted',
                         None, None]
        else:
            self.key = kwargs['course_id']
            self.data = [self.key, kwargs['short_name'], kwargs['long_name'],
                         kwargs['account_id'], kwargs['term_id'],
                         kwargs.get('status', 'active'),
                         kwargs.get('start_date', None),
                         kwargs.get('end_date', None)]


class SectionCSV(CSVFormat):
    """
    section_id, course_id, name, status (active|deleted), start_date, end_date
    """
    def __init__(self, **kwargs):
        if kwargs.get('section'):
            section = kwargs.get('section')
            self.key = section.canvas_section_sis_id()
            self.data = [self.key,
                         section.canvas_course_sis_id(),
                         section_short_name(section),
                         'active' if is_active_section(section) else 'deleted',
                         None, None]
        else:
            self.key = kwargs['section_id']
            self.data = [self.key, kwargs['course_id'], kwargs['name'],
                         kwargs.get('status', 'active'),
                         kwargs.get('start_date', None),
                         kwargs.get('end_date', None)]


class EnrollmentCSV(CSVFormat):
    """
    course_id, root_account, user_id, role, role_id, section_id,
    status (active|inactive|deleted|completed), associated_user_id
    """
    def __init__(self, **kwargs):
        course_id = None  # course_id is not used for SIS enrollments
        if kwargs.get('registration'):  # Student registration object
            registration = kwargs.get('registration')
            person = registration.person
            section_id = registration.section.canvas_section_sis_id()
            role = STUDENT_ENROLLMENT
            status = enrollment_status_from_registration(registration)

        elif kwargs.get('instructor'):
            section = kwargs.get('section')
            person = kwargs.get('instructor')
            section_id = section.canvas_section_sis_id()
            role = INSTRUCTOR_ENROLLMENT
            status = kwargs.get('status')

        else:
            course_id = kwargs.get('course_id', None)
            section_id = kwargs.get('section_id', None)
            person = kwargs.get('person')
            role = kwargs.get('role')
            status = kwargs.get('status')

        user_id = user_sis_id(person)
        if not valid_enrollment_status(status):
            raise EnrollmentPolicyException(
                'Invalid enrollment status for %s: %s' % (user_id, status))

        if course_id is None and section_id is None:
            raise EnrollmentPolicyException(
                'Missing course and section for %s: %s' % (user_id, status))

        self.data = [course_id, None, user_id, role, None, section_id, status,
                     None]


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
