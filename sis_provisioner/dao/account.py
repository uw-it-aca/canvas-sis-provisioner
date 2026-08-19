# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


import re
import string

from django.conf import settings
from uw_sws.campus import get_all_campuses
from uw_sws.college import get_all_colleges
from uw_sws.department import get_departments_by_college
from uw_sws.models import Curriculum

from sis_provisioner.dao import titleize
from sis_provisioner.exceptions import AccountPolicyException

RE_CANVAS_ID = re.compile(r"^\d+$")
RE_ACCOUNT_ID = re.compile(r"(?=.*[a-z])[\w\-:& ]", re.IGNORECASE)
CACHED_ACCOUNTS = {}
CACHED_OVERRIDES = {}


def valid_canvas_account_id(canvas_id):
    if (canvas_id is None or RE_CANVAS_ID.match(str(canvas_id)) is None):
        raise AccountPolicyException(f"Invalid Canvas ID: {canvas_id}")


def valid_account_id(account_id):
    if (account_id is None or RE_ACCOUNT_ID.match(str(account_id)) is None):
        raise AccountPolicyException(f"Invalid account ID: {account_id}")


def valid_account_sis_id(account_id):
    if account_id is not None:
        sis_root = settings.SIS_IMPORT_ROOT_ACCOUNT_ID
        if (account_id == sis_root or
                re.match(rf"^{re.escape(sis_root)}\:\w+", account_id)):
            return
    raise AccountPolicyException(f"Invalid account SIS ID: {account_id}")


def valid_academic_account_sis_id(account_id):
    valid_account_sis_id(account_id)
    try:
        campus = account_id.split(":")[1]
        if re.match(r"^(?:seattle|bothell|tacoma)$", campus):
            return
    except IndexError:
        pass

    raise AccountPolicyException(f"Invalid academic account SIS ID: {account_id}")


def adhoc_account_sis_id(canvas_id):
    valid_canvas_account_id(canvas_id)
    return f"account_{canvas_id}"


def account_sis_id(accounts):
    """
    Generates the unique identifier for a sub-account in the form of
    account-1:account-2:account-3
    """
    clean_accounts = []
    for account in accounts:
        valid_account_id(account)
        clean_account = account.strip(string.whitespace + ":").lower()
        clean_account = re.sub(r"[:\s]+", "-", clean_account)
        clean_accounts.append(clean_account)

    return ":".join(clean_accounts)


def account_name(context):
    """
    Generates a name for a sub-account. The passed context is one of these
    SWS models: Campus, College, Department, Curriculum
    """
    name = titleize(context.full_name)

    if isinstance(context, Curriculum):
        name = re.sub(r"(\(?(UW )?Bothell( Campus)?\)?|Bth)$", "", name)
        name = re.sub(r"(\(?(UW )?Tacoma( Campus)?\)?|T)$", "", name)
        name = re.sub(r"[\s-]+$", "", name)
        name += f" [{context.label}]"

    return name


def account_id_for_section(section):
    global CACHED_ACCOUNTS, CACHED_OVERRIDES
    if not len(CACHED_ACCOUNTS):
        from sis_provisioner.models.account import Curriculum, SubAccountOverride
        CACHED_ACCOUNTS = Curriculum.objects.accounts_by_curricula()
        CACHED_OVERRIDES = SubAccountOverride.objects.overrides_by_course()

    # Default to the curriculum-based account
    account_id = CACHED_ACCOUNTS.get(section.curriculum_abbr, None)

    # Check for a Continuum-managed override
    lms_owner_accounts = getattr(settings, 'LMS_OWNERSHIP_SUBACCOUNT', {})
    try:
        account_id = lms_owner_accounts[section.lms_ownership]
    except (AttributeError, KeyError):
        if account_id is None and section.course_campus == 'PCE':
            account_id = lms_owner_accounts.get('PCE_NONE', None)

    # Check for section.institute_name override
    try:
        account_id = getattr(
            settings, 'INSTITUTE_NAME_SUBACCOUNT', {})[section.institute_name]
    except KeyError:
        pass

    # Check for an adhoc override
    course_id = section.canvas_course_sis_id()
    if course_id in CACHED_OVERRIDES:
        account_id = CACHED_OVERRIDES[course_id]

    if account_id is None:
        raise AccountPolicyException(f"No account_id for {course_id}")

    return account_id


def get_campus_by_label(label):
    for campus in get_all_campuses():
        if label.lower() == campus.label.lower():
            return campus


def get_college_by_label(campus, label):
    for college in get_all_colleges():
        if (campus.label.lower() == college.campus_label.lower() and
                label.lower() == college.label.lower()):
            return college


def get_department_by_label(college, label):
    for department in get_departments_by_college(college):
        if label.lower() == department.label.lower():
            return department
