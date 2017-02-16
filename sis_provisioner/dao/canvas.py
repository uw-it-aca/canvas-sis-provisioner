from django.conf import settings
from restclients.canvas import Canvas
from restclients.canvas.accounts import Accounts
from restclients.canvas.courses import Courses
from restclients.canvas.sections import Sections
from restclients.canvas.enrollments import Enrollments
from restclients.canvas.reports import Reports
from restclients.canvas.roles import Roles
from restclients.canvas.users import Users
from restclients.canvas.terms import Terms
from restclients.canvas.sis_import import SISImport
from restclients.models.canvas import SISImport as SISImportModel
from restclients.exceptions import DataFailureException
from restclients.util.retry import retry
from sis_provisioner.dao.course import (
    valid_academic_course_sis_id, valid_academic_section_sis_id)
from sis_provisioner.exceptions import CoursePolicyException
from urllib3.exceptions import SSLError
from logging import getLogger
from csv import reader


logger = getLogger(__name__)


def valid_canvas_id(canvas_id):
    return Canvas().valid_canvas_id(canvas_id)


def get_account_by_id(account_id):
    return Accounts().get_account(account_id)


def get_account_by_sis_id(sis_account_id):
    return Accounts().get_account_by_sis_id(sis_account_id)


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
    for role, dates in override_dates.iteritems():
        overrides[role] = {'start_at': dates[0], 'end_at': dates[1]}

    return Terms().update_term_overrides(term_sis_id, overrides=overrides)


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


def sis_import_by_path(csv_path):
    return SISImport().import_dir(csv_path)


def get_sis_import_status(import_id):
    return SISImport().get_import_status(
        SISImportModel(import_id=str(import_id)))
