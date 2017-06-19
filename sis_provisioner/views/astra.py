from django.contrib.auth.decorators import login_required
from sis_provisioner.models.astra import Admin, Account
from sis_provisioner.views.rest_dispatch import RESTDispatch
from logging import getLogger
import re


logger = getLogger(__name__)


class AdminSearch(RESTDispatch):
    """ Performs query of Admin models at /api/v1/admins/?.
        GET returns 200 with Admin models
    """
    @login_required
    def get(self, request, *args, **kwargs):
        admins = []
        for admin in list(Admin.objects.all()):
            admins.append(admin.json_data())

        return self.json_response({'admins': admins})


class AccountSearch(RESTDispatch):
    """ Performs query of Account models at /api/v1/accounts/?.
        GET returns 200 with Account models
    """
    def __init__(self):
        self._re_true = re.compile('^(1|true)$', re.I)

    @login_required
    def get(self, request, *args, **kwargs):
        account_type = request.GET.get('type')
        is_deleted = request.GET.get('is_deleted', '')
        is_deleted = self._is_boolean_true(is_deleted)

        accounts = []
        for account in list(Account.objects.find_by_type(
                account_type=account_type, deleted=is_deleted)):
            accounts.append(account.json_data())

        return self.json_response({'accounts': accounts})

    def _is_boolean_true(self, val):
        return self._re_true.match(val)


class AccountSoC(RESTDispatch):
    """ Performs query of Account models returning Spans of Control
        for ASTRA consumption
        GET returns 200 with SOC list
    """
    def get(self, request, *args, **kwargs):
        account_type = request.GET.get('type', '')

        json_rep = []
        for account in list(Account.objects.find_by_soc(account_type)):
            json_rep.append(account.soc_json_data())

        return self.json_response(json_rep)
