# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from sis_provisioner.builders import Builder
from sis_provisioner.csv.format import AdminCSV
from sis_provisioner.dao.user import get_person_by_regid
from sis_provisioner.exceptions import UserPolicyException
from logging import getLogger

logger = getLogger('sis_provisioner.dao.astra')


class AdminBuilder(Builder):
    """
    Generates the data for sub-account admins.
    """
    def _process(self, admin):
        if admin.queue_id is not None:
            self.queue_id = admin.queue_id

        account_id = admin.account.sis_id
        role = settings.ASTRA_ROLE_MAPPING[admin.role]
        status = 'deleted' if admin.is_deleted else 'active'
        action = 'REMOVE' if admin.is_deleted else 'ADD'

        try:
            person = get_person_by_regid(admin.reg_id)
            if not self.add_user_data_for_person(person):
                raise UserPolicyException('Invalid UWNetID')

        except UserPolicyException as err:
            logger.info(
                'SKIP ADMIN "{}", account: "{}", role: "{}", {}'.format(
                    admin.net_id, account_id, role, err))
            return

        if str(admin.canvas_id) == settings.RESTCLIENTS_CANVAS_ACCOUNT_ID:
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
