from django.conf import settings
from django.utils.timezone import utc
from sis_provisioner.builders import Builder
from sis_provisioner.csv.format import AdminCSV
from sis_provisioner.dao.canvas import (
    valid_canvas_id, get_account, get_account_by_sis_id, get_all_sub_accounts,
    get_admins)
from sis_provisioner.models import Admin
from sis_provisioner.models.astra import Account
from datetime import datetime
from logging import getLogger

logger = getLogger('astra')


class AdminBuilder(Builder):
    """
    Generates the data for sub-account admins.
    """
    def build(self, **kwargs):
        self.remove_non_astra = kwargs['remove_non_astra']
        self.ancillary_roles = settings.ANCILLARY_CANVAS_ROLES

        root_account_id = kwargs['root_account']
        if valid_canvas_id(root_account_id):
            account = get_account(root_account_id)
        else:
            account = get_account_by_sis_id(root_account_id)

        accounts = [account]
        accounts.extend(get_all_sub_accounts(account.account_id))

        for account in accounts:
            self._process_account(account)

        return self._write()

    def _process_account(self, account):
        account_id = account.sis_account_id
        account_model = Account.objects.add_account(account)

        # reconcile Canvas admins against Admin table
        astra_admins = Admin.objects.filter(canvas_id=account.account_id)
        canvas_admins = get_admins(account.account_id)

        # if account_model.is_root():
        #    pass

        for astra_admin in astra_admins:
            user_id = astra_admin.reg_id
            canvas_role = settings.ASTRA_ROLE_MAPPING[astra_admin.role]
            is_canvas_admin = False
            ancillary_role = None
            ancillary_account = None

            for canvas_admin in canvas_admins:
                if (astra_admin.net_id == canvas_admin.user.login_id and
                        canvas_role == canvas_admin.role):
                    is_canvas_admin = True
                    canvas_admin.in_astra = True
                    break

            if astra_admin.role in self.ancillary_roles:
                ancillary_role = self.ancillary_roles[astra_admin.role].get(
                    'canvas_role')
                ancillary_account = self.ancillary_roles[astra_admin.role].get(
                    'account')

            if (astra_admin.is_deleted and is_canvas_admin):
                # Admin removed in ASTRA and exists in Canvas
                self.remove_admin(user_id, account_id, canvas_role)

                if ancillary_role is not None:
                    if ancillary_account == 'root':
                        account_id = ''
                    self.remove_admin(user_id, account_id, ancillary_role)

                astra_admin.deleted_date = datetime.utcnow().replace(
                    tzinfo=utc)
                astra_admin.save()

            elif not astra_admin.is_deleted:
                # Admin added in ASTRA, may or may not exist in Canvas
                self.add_admin(user_id, account_id, canvas_role)

                if ancillary_role is not None:
                    if ancillary_account == 'root':
                        account_id = ''
                    self.add_admin(user_id, account_id, ancillary_role)

        if self.remove_non_astra:
            for canvas_admin in canvas_admins:
                user_id = canvas_admin.user.sis_user_id
                role = canvas_admin.role
                if not hasattr(canvas_admin, 'in_astra'):
                    logger.info('REMOVE UNK {} from {} with role {}'.format(
                        user_id, account_id, role))

    def add_admin(self, user_id, account_id, role):
        self.data.add(AdminCSV(user_id, account_id, role, status='active'))
        logger.info('ADD {} to {} with role {}'.format(
            user_id, account_id, role))

    def remove_admin(self, user_id, account_id, role):
        self.data.add(AdminCSV(user_id, account_id, role, status='deleted'))
        logger.info('REMOVE {} from {} with role {}'.format(
            user_id, account_id, role))
