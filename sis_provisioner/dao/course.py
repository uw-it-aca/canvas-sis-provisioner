# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.conf import settings
from uw_sws.section import (
    get_section_by_label, get_section_by_url, get_changed_sections_by_term,
    get_sections_by_instructor_and_term)
from uw_sws.registration import get_all_registrations_by_section
from uw_sws.models import Section
from uw_canvas.models import CanvasCourse, CanvasSection
from restclients_core.exceptions import DataFailureException
from sis_provisioner.exceptions import CoursePolicyException
from sis_provisioner.dao import titleize
from logging import getLogger
from urllib.parse import unquote
import re

logger = getLogger(__name__)

RE_CANVAS_ID = re.compile(r"^\d+$")
RE_ADHOC_COURSE_SIS_ID = re.compile(r"^course_\d+$")


def valid_canvas_course_id(canvas_id):
    if (canvas_id is None or RE_CANVAS_ID.match(canvas_id) is None):
        raise CoursePolicyException("Invalid Canvas ID: {}".format(canvas_id))


def valid_course_sis_id(sis_id):
    if (sis_id is None or not len(sis_id)):
        raise CoursePolicyException("Invalid course SIS ID: {}".format(sis_id))


def valid_adhoc_course_sis_id(sis_id):
    if (sis_id is None or RE_ADHOC_COURSE_SIS_ID.match(sis_id) is None):
        raise CoursePolicyException("Invalid course SIS ID: {}".format(sis_id))


def valid_academic_course_sis_id(sis_id):
    if not CanvasCourse(sis_course_id=sis_id).is_academic_sis_id():
        raise CoursePolicyException(
            "Invalid academic course SIS ID: {}".format(sis_id))


def valid_academic_section_sis_id(sis_id):
    if not CanvasSection(sis_section_id=sis_id).is_academic_sis_id():
        raise CoursePolicyException(
            "Invalid academic section SIS ID: {}".format(sis_id))


def adhoc_course_sis_id(canvas_id):
    valid_canvas_course_id(canvas_id)
    return "course_{}".format(canvas_id)


def group_section_sis_id(course_sis_id):
    valid_course_sis_id(course_sis_id)
    return "{}-groups".format(course_sis_id)


def group_section_name():
    return getattr(settings, 'DEFAULT_GROUP_SECTION_NAME', 'UW Group members')


def section_id_from_url(url):
    label = re.sub(r'^/student/v5/course/', '', unquote(str(url)))
    label = re.sub(r'.json$', '', label)

    try:
        (year, quarter, curr_abbr, course_num,
            section_id) = label.replace('/', ',').split(',', 4)
    except ValueError:
        return None

    return '{year}-{quarter}-{curr_abbr}-{course_num}-{section_id}'.format(
        year=year, quarter=quarter.lower(), curr_abbr=curr_abbr.upper(),
        course_num=course_num, section_id=section_id)


def section_label_from_section_id(section_id):
    canvas_section = CanvasSection(sis_section_id=section_id)
    section_label = canvas_section.sws_section_id()
    if section_label is None:
        valid_academic_course_sis_id(section_id)
        canvas_course = CanvasCourse(sis_course_id=section_id)
        section_label = canvas_course.sws_course_id()
    return section_label


def instructor_regid_from_section_id(section_id):
    canvas_section = CanvasSection(sis_section_id=section_id)
    reg_id = canvas_section.sws_instructor_regid()
    if reg_id is None:
        canvas_course = CanvasCourse(sis_course_id=section_id)
        reg_id = canvas_course.sws_instructor_regid()
    return reg_id


def valid_canvas_section(section):
    course_id = section.canvas_course_sis_id()
    if (hasattr(section, "primary_lms") and section.primary_lms and
            section.primary_lms != Section.LMS_CANVAS):
        raise CoursePolicyException("Non-Canvas LMS '{}' for {}".format(
            section.primary_lms, course_id))


def is_active_section(section):
    try:
        valid_canvas_section(section)
        return not section.is_withdrawn()
    except CoursePolicyException:
        return False


def is_time_schedule_construction(section):
    campus = section.course_campus.lower()
    if campus == 'bothell':
        return not section.term.time_schedule_published.get(campus)
    return section.term.time_schedule_construction.get(campus, False)


def section_short_name(section):
    return '{curr_abbr} {course_num} {section_id}'.format(
        curr_abbr=section.curriculum_abbr,
        course_num=section.course_number,
        section_id=section.section_id)


def section_long_name(section):
    name = '{curr_abbr} {course_num} {section_id} {quarter} {year}'.format(
        curr_abbr=section.curriculum_abbr,
        course_num=section.course_number,
        section_id=section.section_id,
        quarter=section.term.quarter[:2].capitalize(),
        year=str(section.term.year)[-2:])

    if (section.course_title_long is not None and
            len(section.course_title_long)):
        name = '{name}: {title}'.format(
            name=name, title=titleize(section.course_title_long))

    if section.is_independent_study:
        for person in section.get_instructors():
            if person.uwregid == section.independent_study_instructor_regid:
                name = '{name} ({user_fullname})'.format(
                    name=name,
                    user_fullname=person.get_formatted_name('{first} {last}'))
                break

    return name


def get_section_by_id(section_id):
    label = section_label_from_section_id(section_id)

    section = get_section_by_label(label)

    if section.is_independent_study:
        reg_id = instructor_regid_from_section_id(section_id)
        section.independent_study_instructor_regid = reg_id

    return section


def get_new_sections_by_term(changed_since_date, term, existing={}):
    kwargs = {
        'future_terms': 0,
        'transcriptable_course': 'all',
        'include_secondaries': 'on',
        'delete_flag': [Section.DELETE_FLAG_ACTIVE,
                        Section.DELETE_FLAG_SUSPENDED]
    }
    sections = []
    for section_ref in get_changed_sections_by_term(
            changed_since_date, term, **kwargs):

        primary_id = None
        course_id = '{term_id}-{curr_abbr}-{course_num}-{section_id}'.format(
            term_id=section_ref.term.canvas_sis_id(),
            curr_abbr=section_ref.curriculum_abbr.upper(),
            course_num=section_ref.course_number,
            section_id=section_ref.section_id.upper())

        if course_id not in existing:
            try:
                label = section_ref.section_label()
                section = get_section_by_label(label)
                if is_time_schedule_construction(section):
                    logger.info('Course: SKIP {}, TSC on'.format(label))
                    continue
            except DataFailureException as err:
                logger.info('Course: SKIP {}, {}'.format(label, err))
                continue
            except ValueError as err:
                logger.info('Course: SKIP, {}'.format(err))
                continue

            if section.is_independent_study:
                for instructor in section.get_instructors():
                    ind_course_id = '{}-{}'.format(
                        course_id, instructor.uwregid)
                    if ind_course_id not in existing:
                        sections.append({'course_id': ind_course_id,
                                         'primary_id': primary_id})
            else:
                if not section.is_primary_section:
                    primary_id = section.canvas_course_sis_id()

                sections.append({'course_id': course_id,
                                 'primary_id': primary_id})

    return sections


def get_registrations_by_section(section):
    registrations = get_all_registrations_by_section(
        section, transcriptable_course='all')

    # Sort by regid, is_active, duplicate code
    registrations.sort(key=lambda r: (
        r.person.uwregid, r.is_active, r.duplicate_code))

    # Keep the last instance of a regid
    uniques = {}
    for registration in registrations:
        uniques[registration.person.uwregid] = registration

    return sorted(list(uniques.values()), key=lambda r: r.person.uwregid)


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
