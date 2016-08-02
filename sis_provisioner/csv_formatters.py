from sis_provisioner.models import Enrollment
from sis_provisioner.policy import CoursePolicy
from restclients.models.sws import Person, Entity
from restclients.models.canvas import CanvasUser
from nameparser import HumanName
import string
import re


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
    policy = CoursePolicy()

    start_date = policy.term_start_date(section)
    if start_date is not None:
        start_date = start_date.strftime("%Y-%m-%dT00:00:00-0800")

    end_date = policy.term_end_date(section)
    if end_date is not None:
        end_date = end_date.strftime("%Y-%m-%dT00:00:00-0800")

    return [policy.term_sis_id(section),
            policy.term_name(section),
            "active",
            start_date,
            end_date]


def _csv_for_enrollment(section_id, user, role, status):
    """
    Returns a list of data for creating a line of csv for an enrollment:
        course_id, root_account, user_id, role, role_id, section_id, status,
        associated_user_id
    """
    if not any(status == val for (val, name) in Enrollment.STATUS_CHOICES):
        raise Exception("Invalid enrollment status for %s: %s" % (user_id,
                                                                  status))

    if (isinstance(user, Person) or isinstance(user, Entity)):
        user_id = user.uwregid
    elif isinstance(user, CanvasUser):  # Gmail ePPN
        user_id = user.sis_user_id
    else:
        raise Exception("Not a valid user class: %s" % user.__class__.__name__)

    return [None, None, user_id, role, None, section_id, status, None]


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


def csv_for_sis_auditor_enrollment(section, user, status):
    """
    Returns a list of data for creating a line of csv for an SIS Auditor.
    """
    return _csv_for_enrollment(section.canvas_section_sis_id(), user,
                               Enrollment.AUDITOR_ROLE, status)


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
    section_name = " ".join([section.curriculum_abbr, section.course_number,
                             section.section_id])

    return [section.canvas_section_sis_id(),
            section.canvas_course_sis_id(),
            section_name,
            "active" if (
                CoursePolicy().is_active_section(section)) else "deleted",
            None, None]


def csv_for_group_section(course_id):
    policy = CoursePolicy()
    return [policy.group_section_sis_id(course_id),
            course_id,
            policy.group_section_name(),
            "active",
            None, None]


def csv_for_course(section):
    """
    Returns a list of data for creating a line of csv for a course:
        course_id, short_name, long_name, account_id, term_id,
        status (active|deleted|completed), start_date, end_date
    """
    policy = CoursePolicy()
    course_id = section.canvas_course_sis_id()
    short_name = " ".join([section.curriculum_abbr, section.course_number,
                           section.section_id])

    if section.course_title_long is not None:
        long_name = "%s: %s" % (short_name, titleize(
            section.course_title_long.encode("ascii", "ignore")))
    else:
        long_name = short_name

    if section.is_independent_study:
        for person in section.get_instructors():
            if person.uwregid == section.independent_study_instructor_regid:
                long_name = "%s (%s)" % (long_name, fullname(person))
                break

    return [course_id, short_name, long_name,
            policy.canvas_account_id(section),
            policy.term_sis_id(section),
            "active" if policy.is_active_section(section) else "deleted",
            None, None]


def csv_for_xlist(course_id, section_id, status="active"):
    """
    Returns a list of data for creating a line of csv for a cross-listed
        section: xlist_course_id, section_id, status (active|deleted)
    """
    return [course_id, section_id, status]


def csv_for_account(account_id, parent_id, name, curriculum_label=None):
    """
    Returns a list of data for creating a line of csv for an account:
        account_id, parent_account_id, name, status (active|deleted)
    """
    name = titleize(name)

    if curriculum_label is not None:
        name = re.sub(r"(\(?(UW )?Bothell( Campus)?\)?|Bth)$", "", name)
        name = re.sub(r"(\(?(UW )?Tacoma( Campus)?\)?|T)$", "", name)
        name = re.sub(r"[\s-]+$", "", name)
        name += " [%s]" % curriculum_label

    return [account_id, parent_id, name, "active"]


def csv_for_user(user, status="active"):
    """
    Returns a list of data for creating a line of csv for a user:
        user_id, login_id, password, first_name, last_name, full_name,
        sortable_name, short_name, email, status (active|deleted)
    """
    if isinstance(user, Person):
        email = "%s@uw.edu" % user.uwnetid
        return [user.uwregid, user.uwnetid, None, None, None,
                fullname(user), None, None, email, status]

    elif isinstance(user, Entity):
        email = "%s@uw.edu" % user.uwnetid
        return [user.uwregid, user.uwnetid, None, None, None,
                user.display_name, None, None, email, status]

    elif isinstance(user, CanvasUser):  # Gmail ePPN
        full_name = user.email.split("@")[0]
        return [user.sis_user_id, user.login_id, None, None, None,
                full_name, None, None, user.email, status]

    else:
        raise Exception("Not a valid user class: %s" % user.__class__.__name__)


def sisid_for_account(accounts):
    """
    Generates the unique identifier for a sub-account in the form of
    account-1:account-2:account-3
    """
    clean_accounts = []
    for account in accounts:
        if account is None or not len(account):
            raise Exception("Invalid account: %s" % account)

        clean_account = account.strip(string.whitespace + ":").lower()
        clean_account = re.sub(r"[:\s]+", "-", clean_account)
        clean_accounts.append(clean_account)

    return ":".join(clean_accounts)


def fullname(person):
    """
    Generates the full name for a PWS person.
    """
    if (person.display_name is not None and len(person.display_name) and
            not person.display_name.isupper()):
        full_name = person.display_name
    else:
        full_name = HumanName("%s %s" % (person.first_name, person.surname))
        full_name.capitalize()
        full_name.string_format = "{first} {last}"

    return full_name


def titleize(s):
    """
    Capitalizes the first letter of every word, effective only in
    ASCII region.
    """
    new_s = ''
    for word in re.split('(\s|-|\(|\)|\.|,|\/|:)', s):
        new_s += word.capitalize()

    pattern = (r'\b('
               r'3d|3d4m|Asp|Basw|Cep|Cisb|Cophp|Csr|Css3|'
               r'Dub|Edp|Gis|Hcde|Hci|Hiv|Hr|Html5|'
               r'Ias|Ielts|Ii|Iii|Ios|It|Iv|Jsis|'
               r'Mpa|Mph|Msw|Rotc|Sql|Toefl|'
               r'Us|Uw|Uwmc|Vba|Wsma|Wwami|Xml'
               r')\b')

    new_s = re.sub(pattern, lambda m: m.group(0).upper(), new_s)

    return new_s
