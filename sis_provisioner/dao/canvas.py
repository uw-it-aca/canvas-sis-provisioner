from django.conf import settings
from uw_canvas import Canvas
from uw_canvas.accounts import Accounts
from uw_canvas.courses import Courses
from uw_canvas.sections import Sections
from uw_canvas.enrollments import Enrollments
from uw_canvas.reports import Reports
from uw_canvas.roles import Roles
from uw_canvas.users import Users
from uw_canvas.terms import Terms
from uw_canvas.sis_import import SISImport
from uw_canvas.models import CanvasEnrollment, SISImport as SISImportModel
from restclients_core.exceptions import DataFailureException
from sis_provisioner.util.retry import retry
from sis_provisioner.dao.course import (
    valid_academic_course_sis_id, valid_academic_section_sis_id)
from sis_provisioner.dao import localize
from sis_provisioner.exceptions import CoursePolicyException
from urllib3.exceptions import SSLError
from logging import getLogger
from csv import reader


logger = getLogger(__name__)

INSTRUCTOR_ENROLLMENT = CanvasEnrollment.TEACHER.replace('Enrollment', '')
STUDENT_ENROLLMENT = CanvasEnrollment.STUDENT.replace('Enrollment', '')
AUDITOR_ENROLLMENT = 'Auditor'
ENROLLMENT_ACTIVE = CanvasEnrollment.STATUS_ACTIVE
ENROLLMENT_INACTIVE = CanvasEnrollment.STATUS_INACTIVE
ENROLLMENT_DELETED = CanvasEnrollment.STATUS_DELETED


def valid_canvas_id(canvas_id):
    return Canvas().valid_canvas_id(canvas_id)


def get_account_by_id(account_id):
    return Accounts().get_account(account_id)


def get_account_by_sis_id(sis_account_id):
    return Accounts().get_account_by_sis_id(sis_account_id)


def get_sub_accounts(account_id):
    return Accounts().get_sub_accounts(account_id)


def get_all_sub_accounts(account_id):
    return Accounts().get_all_sub_accounts(account_id)


@retry(SSLError, tries=3, delay=1, logger=logger)
def get_course_roles_in_account(account_id):
    return Roles().get_effective_course_roles_in_account(account_id)


def get_user_by_sis_id(sis_user_id):
    return Users().get_user_by_sis_id(sis_user_id)


def create_user(person):
    return Users().create_user(person)


def get_term_by_sis_id(term_sis_id):
    return Terms().get_term_by_sis_id(term_sis_id)


def get_course_by_id(course_id):
    return Courses().get_course(course_id)


def get_course_by_sis_id(course_sis_id):
    return Courses().get_course_by_sis_id(course_sis_id)


def update_course_sis_id(course_id, course_sis_id):
    return Courses().update_sis_id(course_id, course_sis_id)


def update_term_overrides(term_sis_id, override_dates):
    overrides = {}
    for role in override_dates.keys():
        overrides[role] = {
            'start_at': override_dates[role][0],
            'end_at': override_dates[role][1]
        }

    return Terms().update_term_overrides(term_sis_id, overrides=overrides)


def get_section_by_sis_id(section_sis_id):
    return Sections().get_section_by_sis_id(section_sis_id)


def get_sis_sections_for_course(course_sis_id):
    @retry(DataFailureException, status_codes=[408, 500, 502, 503, 504],
           tries=5, delay=3, logger=logger)
    def _get_sections(course_sis_id):
        try:
            return Sections().get_sections_in_course_by_sis_id(course_sis_id)
        except DataFailureException as err:
            if err.status == 404:
                return []
            else:
                raise

    sis_sections = []
    for section in _get_sections(course_sis_id):
        try:
            valid_academic_section_sis_id(section.sis_section_id)
            sis_sections.append(section)
        except CoursePolicyException:
            continue

    return sis_sections


def valid_enrollment_status(status):
    return (status == ENROLLMENT_ACTIVE or status == ENROLLMENT_INACTIVE or
            status == ENROLLMENT_DELETED)


def enrollment_status_from_registration(registration):
    request_status = registration.request_status.lower()
    if (registration.is_active or request_status == 'added to standby' or
            request_status == 'pending added to class'):
        return ENROLLMENT_ACTIVE

    if registration.request_date is None:
        logger.info('Missing request_date: %s %s' % (
            registration.section.section_label(), registration.person.uwregid))
        return ENROLLMENT_DELETED

    if (localize(registration.request_date) >
            localize(registration.section.term.get_eod_census_day())):
        return ENROLLMENT_INACTIVE
    else:
        return ENROLLMENT_DELETED


def get_sis_enrollments_for_course(course_sis_id):
    canvas = Enrollments()
    enrollments = []
    for section in get_sis_sections_for_course(course_sis_id):
        enrollments.extend(
            canvas.get_enrollments_for_section(section.section_id)
        )
    return enrollments


def get_sis_enrollments_for_user_in_course(user_sis_id, course_sis_id):
    canvas = Enrollments()
    enrollments = []
    for enrollment in canvas.get_enrollments_for_course_by_sis_id(
            course_sis_id, {'user_id': canvas.sis_user_id(user_sis_id)}):
        try:
            valid_academic_section_sis_id(enrollment.sis_section_id)
            enrollments.append(enrollment)
        except CoursePolicyException:
            continue
    return enrollments


def get_active_courses_for_term(term, account_id=None):
    if account_id is None:
        account_id = getattr(settings, 'RESTCLIENTS_CANVAS_ACCOUNT_ID', None)
    canvas_term = get_term_by_sis_id(term.canvas_sis_id())
    reports = Reports()

    # Canvas report of "unused" courses for the term
    unused_course_report = reports.create_unused_courses_report(
        account_id, canvas_term.term_id)

    unused_courses = {}
    for row in reader(reports.get_report_data(unused_course_report)):
        try:
            sis_course_id = row[1]
            valid_academic_course_sis_id(sis_course_id)
            unused_courses[sis_course_id] = True
        except (IndexError, CoursePolicyException):
            pass

    # Canvas report of all courses for the term
    all_course_report = reports.create_course_provisioning_report(
        account_id, canvas_term.term_id)

    active_courses = []
    for row in reader(reports.get_report_data(all_course_report)):
        try:
            sis_course_id = row[1]
            valid_academic_course_sis_id(sis_course_id)
            if sis_course_id not in unused_courses:
                active_courses.append(sis_course_id)
        except (IndexError, CoursePolicyException):
            pass

    reports.delete_report(unused_course_report)
    reports.delete_report(all_course_report)
    return active_courses


def get_unused_course_report_data(term_sis_id):
    term = Terms().get_term_by_sis_id(term_sis_id)
    account_id = getattr(settings, 'RESTCLIENTS_CANVAS_ACCOUNT_ID', None)

    reports = Reports()
    unused_course_report = reports.create_unused_courses_report(
        account_id, term_id=term.term_id)

    report_data = reports.get_report_data(unused_course_report)

    reports.delete_report(unused_course_report)
    return report_data


def sis_import_by_path(csv_path, override_sis_stickiness=False):
    params = {}
    if override_sis_stickiness:
        params['override_sis_stickiness'] = '1'
    return SISImport().import_dir(csv_path, params=params)


def get_sis_import_status(import_id):
    return SISImport().get_import_status(
        SISImportModel(import_id=str(import_id)))
