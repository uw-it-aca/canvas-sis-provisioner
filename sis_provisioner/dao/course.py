from django.conf import settings
from restclients.sws.section import get_section_by_label, get_section_by_url,\
    get_changed_sections_by_term, get_sections_by_instructor_and_term
from restclients.sws.registration import get_all_registrations_by_section
from restclients.models.sws import Section
from restclients.exceptions import DataFailureException
from sis_provisioner.exceptions import CoursePolicyException
from sis_provisioner.dao.user import user_fullname
from sis_provisioner.dao import titleize
import re


RE_COURSE_SIS_ID = re.compile(
    "^\d{4}-"                           # year
    "(?:winter|spring|summer|autumn)-"  # quarter
    "[\w& ]+-"                          # curriculum
    "\d{3}-"                            # course number
    "[A-Z][A-Z0-9]?"                    # section id
    "(?:-[A-F0-9]{32})?$",              # ind. study instructor regid
    re.VERBOSE)


RE_SECTION_SIS_ID = re.compile(
    "^\d{4}-"                                  # year
    "(?:winter|spring|summer|autumn)-"         # quarter
    "[\w& ]+-"                                 # curriculum
    "\d{3}-"                                   # course number
    "[A-Z](?:[A-Z0-9]|--|-[A-F0-9]{32}--)?$",  # section id|regid
    re.VERBOSE)


RE_CANVAS_ID = re.compile(r"^\d+$")
RE_ADHOC_COURSE_SIS_ID = re.compile(r"^course_\d+$")


def valid_canvas_course_id(canvas_id):
    if (RE_CANVAS_ID.match(str(canvas_id)) is None):
        raise CoursePolicyException("Invalid Canvas ID: %s" % canvas_id)


def valid_course_sis_id(sis_id):
    if not (sis_id and len(str(sis_id)) > 0):
        raise CoursePolicyException("Invalid course SIS ID: %s" % sis_id)


def valid_adhoc_course_sis_id(sis_id):
    if (RE_ADHOC_COURSE_SIS_ID.match(str(sis_id)) is None):
        raise CoursePolicyException("Invalid course SIS ID: %s" % sis_id)


def valid_academic_course_sis_id(sis_id):
    if (RE_COURSE_SIS_ID.match(str(sis_id)) is None):
        raise CoursePolicyException(
            "Invalid academic course SIS ID: %s" % sis_id)


def valid_academic_section_sis_id(sis_id):
    if (RE_SECTION_SIS_ID.match(str(sis_id)) is None):
        raise CoursePolicyException(
            "Invalid academic section SIS ID: %s" % sis_id)


def adhoc_course_sis_id(canvas_id):
    valid_canvas_course_id(canvas_id)
    return "course_%s" % canvas_id


def group_section_sis_id(course_sis_id):
    valid_course_sis_id(course_sis_id)
    return "%s-groups" % course_sis_id


def group_section_name():
    return getattr(settings, 'DEFAULT_GROUP_SECTION_NAME', 'UW Group members')


def section_label_from_section_id(section_id):
    section_id = re.sub(r'--$', '', str(section_id))
    valid_academic_course_sis_id(section_id)
    try:
        (year, quarter, curr_abbr, course_num,
            section_id, reg_id) = section_id.split('-', 5)
    except ValueError:
        (year, quarter, curr_abbr, course_num,
            section_id) = section_id.split('-', 4)

    return '%s,%s,%s,%s/%s' % (str(year), quarter.lower(), curr_abbr.upper(),
                               course_num, section_id)


def instructor_regid_from_section_id(section_id):
    section_id = re.sub(r'--$', '', str(section_id))
    valid_academic_course_sis_id(section_id)
    try:
        (year, quarter, curr_abbr, course_num, section_id,
            reg_id) = section_id.split('-', 5)
        return reg_id
    except ValueError:
        return None


def valid_canvas_section(section):
    course_id = section.canvas_course_sis_id()
    if (hasattr(section, "primary_lms") and section.primary_lms and
            section.primary_lms != Section.LMS_CANVAS):
        raise CoursePolicyException("Non-Canvas LMS '%s' for %s" % (
            section.primary_lms, course_id))


def is_active_section(section):
    try:
        valid_canvas_section(section)
        return not section.is_withdrawn
    except CoursePolicyException:
        return False


def is_time_schedule_construction(section):
    campus = section.course_campus.lower()
    return next(
        (t.is_on for t in section.term.time_schedule_construction if (
            t.campus.lower() == campus)), False)


def section_short_name(section):
    return '%s %s %s' % (section.curriculum_abbr, section.course_number,
                         section.section_id)


def section_long_name(section):
    name = '%s %s %s %s %s' % (
        section.curriculum_abbr, section.course_number, section.section_id,
        section.term.quarter[:2].capitalize(), str(section.term.year)[-2:])

    if (section.course_title_long is not None and
            len(section.course_title_long)):
        name = '%s: %s' % (name, titleize(
            section.course_title_long.encode('ascii', 'ignore')))

    if section.is_independent_study:
        for person in section.get_instructors():
            if person.uwregid == section.independent_study_instructor_regid:
                name = '%s (%s)' % (name, user_fullname(person))
                break

    return name


def get_section_by_id(section_id):
    label = section_label_from_section_id(section_id)

    section = get_section_by_label(label)

    if section.is_independent_study:
        reg_id = instructor_regid_from_section_id(section_id)
        section.independent_study_instructor_regid = reg_id

    return section


def get_sections_by_term(changed_since_date, term):
    return get_changed_sections_by_term(changed_since_date, term,
                                        transcriptable_course='all')


def get_registrations_by_section(section):
    return get_all_registrations_by_section(section,
                                            transcriptable_course='all')


def canvas_xlist_id(section_list):
    xlist_courses = []
    for section in section_list:
        if is_active_section(section):
            xlist_courses.append(section)

    xlist_courses.sort(key=lambda s: (
        s.lms_ownership != Section.LMS_OWNER_OL,
        s.canvas_course_sis_id())
    )

    try:
        return xlist_courses[0].canvas_course_sis_id()
    except IndexError:
        return None
