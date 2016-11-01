from restclients.sws.campus import get_all_campuses
from restclients.sws.college import get_all_colleges
from restclients.sws.curriculum import get_curricula_by_department
from restclients.sws.department import get_departments_by_college
from restclients.models.sws import Curriculum
from sis_provisioner.exceptions import AccountPolicyException
from sis_provisioner.dao import titleize
import string
import re


RE_ACCOUNT_ID = re.compile(r"(?=.*[a-z])[\w\-:& ]", re.I)


def valid_account_id(account_id):
    if (account_id is None or RE_ACCOUNT_ID.match(str(account_id)) is None):
        raise AccountPolicyException("Invalid account ID: %s" % account_id)


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
        name += " [%s]" % context.label

    return name
