import re
import json
from django.conf import settings
from logging import getLogger
from django.db.models import Q
from django.utils.timezone import localtime
from sis_provisioner.models.astra import Admin, Account
from sis_provisioner.views.rest_dispatch import RESTDispatch, OpenRESTDispatch


class AdminSearch(RESTDispatch):
    """ Performs query of Admin models at /api/v1/admins/?.
        GET returns 200 with Admin models
    """
    def __init__(self):
        self._log = getLogger(__name__)

    def GET(self, request, **kwargs):
        json_rep = {
            'admins': []
        }

        for admin in list(Admin.objects.all()):
            json_rep['admins'].append(self._serializeAdmin(admin))

        return self.json_response(json.dumps(json_rep))

    def display_datetime(self, datetime):
        if datetime is None:
                return ""
        datetime = localtime(datetime)
        return datetime.strftime("%m/%d/%Y %l:%M %p")

    def _serializeAdmin(self, admin):
        return {
            'net_id': admin.net_id,
            'reg_id': admin.reg_id,
            'role': admin.role,
            'account_id': admin.account_id,
            'canvas_id': admin.canvas_id,
            'account_link': '%s/accounts/%s' % (
                settings.RESTCLIENTS_CANVAS_HOST, admin.canvas_id),
            'added_date': self.display_datetime(admin.added_date),
            'provisioned_date': self.display_datetime(admin.provisioned_date),
            'is_deleted': True if admin.is_deleted else False,
            'deleted_date': self.display_datetime(admin.deleted_date),
            'queue_id': (admin.queue_id if admin.queue_id else '')
        }


class AccountSearch(RESTDispatch):
    """ Performs query of Account models at /api/v1/accounts/?.
        GET returns 200 with Account models
    """
    def __init__(self):
        self._re_true = re.compile('^(1|true)$', re.I)
        self._log = getLogger(__name__)

    def GET(self, request, **kwargs):
        json_rep = {
            'accounts': []
        }

        filter = {}

        account_type = request.GET.get('type')
        if account_type:
            filter['account_type'] = account_type

        is_blessed = request.GET.get('is_blessed_for_course_request')
        if is_blessed:
            filter['is_blessed_for_course_request'] = 1 if (
                self._is_boolean_true(is_blessed)) else None

        is_deleted = request.GET.get('is_deleted')
        if is_deleted:
            filter['is_deleted'] = 1 if (
                self._is_boolean_true(is_deleted)) else None

        account_list = list(Account.objects.filter(**filter))
        for account in account_list:
            json_rep['accounts'].append(self._serializeAccount(account))

        return self.json_response(json.dumps(json_rep))

    def _is_boolean_true(self, val):
        return self._re_true.match(val)

    def _serializeAccount(self, account):
        return {
            'canvas_id': account.canvas_id,
            'sis_id': account.sis_id,
            'account_name': account.account_name,
            'account_short_name': account.account_short_name,
            'account_type': account.account_type,
            'added_date': account.added_date.isoformat() if (
                account.added_date is not None) else '',
            'is_deleted': account.is_deleted,
            'is_blessed_for_course_request': account.is_blessed_for_course_request
        }


class AccountSoC(OpenRESTDispatch):
    """ Performs query of Account models returning Spans of Control
        for ASTRA consumption
        GET returns 200 with SOC list
    """
    def __init__(self):
        self._log = getLogger(__name__)

    def GET(self, request, **kwargs):
        json_rep = []
        q = Q(account_type=Account.ADHOC_TYPE) | \
            Q(account_type=Account.TEST_TYPE)

        t = request.GET.get('type', 'None')
        if t.lower() == 'academic':
            q = Q(account_type=Account.SDB_TYPE)
        elif t.lower() == 'non-academic':
            q = Q(account_type=Account.ADHOC_TYPE)
        elif t.lower() == 'test-account':
            q = Q(account_type=Account.TEST_TYPE)
        elif t == 'all':
            q = Q(account_type=Account.ROOT_TYPE) | \
                Q(account_type=Account.SDB_TYPE) | \
                Q(account_type=Account.ADHOC_TYPE) | \
                Q(account_type=Account.TEST_TYPE)

        if q:
            for account in list(Account.objects.filter(q)):
                json_rep.append(self._serializeSoC(account))

        return self.json_response(json.dumps(json_rep))

    def _serializeSoC(self, account):
        type_name = 'Unknown'
        if account.is_root():
            type_name = 'Root'
        elif account.is_sdb():
            type_name = 'SDB'
        elif account.is_adhoc():
            type_name = 'Non-Academic'
        elif account.is_test():
            type_name = 'Test-Account'

        return {
            'id': 'canvas_%s' % account.canvas_id,
            'type': type_name,
            'description': account.account_name,
            'short_description': account.account_short_name
        }
