from django.conf import settings
from sis_provisioner.builders import Builder
from sis_provisioner.csv.format import AdminCSV
from logging import getLogger

logger = getLogger('astra')


class AdminBuilder(Builder):
    """
    Generates the data for sub-account admins.
    """
    def _process(self, admin):
        account_id = admin.account_id
        role = settings.ASTRA_ROLE_MAPPING[admin.role]
        status = 'deleted' if admin.is_deleted else 'active'
        action = 'REMOVE' if admin.is_deleted else 'ADD'

        if admin.canvas_id == settings.RESTCLIENTS_CANVAS_ACCOUNT_ID:
            account_id = ''

        self.data.add(AdminCSV(admin.reg_id, account_id, role, status=status))

        logger.info('{} ADMIN "{}", account: "{}", role: "{}"'.format(
            action, admin.net_id, account_id, role))

        if admin.role in settings.ANCILLARY_CANVAS_ROLES:
            ancillary_role = settings.ANCILLARY_CANVAS_ROLES.get(
                admin.role).get('canvas_role')
            if ('root' == settings.ANCILLARY_CANVAS_ROLES.get(
                    admin.role).get('account')):
                ancillary_account_id = ''
            else:
                ancillary_account_id = account_id

            self.data.add(AdminCSV(
                admin.reg_id, ancillary_account_id, ancillary_role,
                status=status))

            logger.info('{} ADMIN "{}", account: "{}", role "{}"'.format(
                action, admin.net_id, ancillary_account_id, ancillary_role))
