from sis_provisioner.dao.term import term_sis_id, term_name,\
    term_start_date, term_end_date
from sis_provisioner.dao.course import is_active_section,\
    group_section_sis_id, group_section_name, section_short_name,\
    section_long_name
from sis_provisioner.dao.user import user_sis_id, user_email, user_fullname
from sis_provisioner.dao.account import account_name
from sis_provisioner.models import Enrollment, Curriculum


def header_for_accounts():
    return ['account_id', 'parent_account_id', 'name', 'status']


def header_for_terms():
    return ['term_id', 'name', 'status', 'start_date', 'end_date']


def header_for_courses():
    return ['course_id', 'short_name', 'long_name', 'account_id', 'term_id',
            'status', 'start_date', 'end_date']


def header_for_sections():
    return ['section_id', 'course_id', 'name', 'status', 'start_date',
            'end_date']


def header_for_enrollments():
    return ['course_id', 'root_account', 'user_id', 'role', 'role_id',
            'section_id', 'status', 'associated_user_id']


def header_for_users():
    return ['user_id', 'login_id', 'password', 'first_name', 'last_name',
            'full_name', 'sortable_name', 'short_name', 'email', 'status']


def header_for_xlists():
    return ['xlist_course_id', 'section_id', 'status']


def csv_for_term(section):
    """
    Returns a list of data for creating a line of csv for a term:
        term_id, name, status (active|deleted), start_date, end_date
    """
    return [term_sis_id(section),
            term_name(section),
            "active",
            term_start_date(section),
            term_end_date(section)]


def _csv_for_enrollment(section_id, user, role, status):
    """
    Returns a list of data for creating a line of csv for an enrollment:
        course_id, root_account, user_id, role, role_id, section_id, status,
        associated_user_id
    """
    user_sis_id = user_sis_id(user)
    if not any(status == val for (val, name) in Enrollment.STATUS_CHOICES):
        raise Exception(
            "Invalid enrollment status for %s: %s" % (user_sis_id, status))

    return [None, None, user_sis_id, role, None, section_id, status, None]


def csv_for_sis_student_enrollment(registration):
    """
    Returns a list of data for creating a line of csv for an SIS Student.
    """
    role = Enrollment.STUDENT_ROLE

    if registration.is_active:
        status = Enrollment.ACTIVE_STATUS
    else:
        status = Enrollment.DELETED_STATUS

    return _csv_for_enrollment(registration.section.canvas_section_sis_id(),
                               registration.person, role, status)


def csv_for_sis_instructor_enrollment(section, user, status):
    """
    Returns a list of data for creating a line of csv for an SIS Instructor.
    """
    return _csv_for_enrollment(section.canvas_section_sis_id(), user,
                               Enrollment.INSTRUCTOR_ROLE, status)


def csv_for_group_enrollment(section_id, user, role, status):
    """
    Returns a list of data for creating a line of csv for a group member.
    """
    return _csv_for_enrollment(section_id, user, role, status)


def csv_for_section(section):
    """
    Returns a list of data for creating a line of csv for a section:
        section_id, course_id, name, status (active|deleted),
        start_date, end_date
    """
    return [section.canvas_section_sis_id(),
            section.canvas_course_sis_id(),
            section_short_name(section),
            "active" if is_active_section(section) else "deleted",
            None, None]


def csv_for_group_section(course_id):
    return [group_section_sis_id(course_id),
            course_id,
            group_section_name(),
            "active",
            None, None]


def csv_for_course(section):
    """
    Returns a list of data for creating a line of csv for a course:
        course_id, short_name, long_name, account_id, term_id,
        status (active|deleted|completed), start_date, end_date
    """
    return [section.canvas_course_sis_id(),
            section_short_name(section),
            section_long_name(section),
            Curriculum.objects.canvas_account_id(section),
            term_sis_id(section),
            "active" if is_active_section(section) else "deleted",
            None, None]


def csv_for_xlist(course_id, section_id, status="active"):
    """
    Returns a list of data for creating a line of csv for a cross-listed
        section: xlist_course_id, section_id, status (active|deleted)
    """
    return [course_id, section_id, status]


def csv_for_account(account_id, parent_id, context, status="active"):
    """
    Returns a list of data for creating a line of csv for an account:
        account_id, parent_account_id, name, status (active|deleted)
    """
    return [account_id, parent_id, account_name(context), status]


def csv_for_user(user, status="active"):
    """
    Returns a list of data for creating a line of csv for a user:
        user_id, login_id, password, first_name, last_name, full_name,
        sortable_name, short_name, email, status (active|deleted)
    """
    return [user_sis_id(user),
            user.uwnetid if hasattr(user, 'uwnetid') else user.login_id,
            None, None, None,
            user_fullname(user),
            None, None,
            user_email(user),
            status]
