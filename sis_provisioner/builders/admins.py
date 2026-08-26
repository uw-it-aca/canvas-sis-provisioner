# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from logging import getLogger

from django.conf import settings

from sis_provisioner.builders import Builder
from sis_provisioner.csv.format import AdminCSV
from sis_provisioner.dao.user import DataFailureException, get_person_by_regid
from sis_provisioner.exceptions import UserPolicyException

logger = getLogger('sis_provisioner.dao.astra')


class AdminBuilder(Builder):
    """
    Generates the data for sub-account admins.
    """
    def _init_build(self, **kwargs):
        self.active_ancillary = set()

    def _add_active_ancillary(self, admin):
        if not admin.is_deleted:
            self.active_ancillary.add(f'{admin.reg_id}/{admin.role}')

    def _is_active_ancillary(self, admin):
        return f'{admin.reg_id}/{admin.role}' in self.active_ancillary

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

        except (DataFailureException, UserPolicyException) as err:
            logger.info(
                f'SKIP ADMIN "{admin.net_id}", account: "{account_id}", '
                f'role: "{role}", {err}'
            )
            return

        if str(admin.canvas_id) == settings.RESTCLIENTS_CANVAS_ACCOUNT_ID:
            account_id = ''

        self.data.add(AdminCSV(
            person.uwregid, account_id, role, status=status))

        logger.info(
            f'{action} ADMIN "{person.uwnetid}", account: "{account_id}", '
            f'role: "{role}"'
        )

        if admin.role in settings.ANCILLARY_CANVAS_ROLES:
            self._add_active_ancillary(admin)
            status = 'active' if self._is_active_ancillary(admin) else 'deleted'
            action = 'ADD' if self._is_active_ancillary(admin) else 'REMOVE'

            ancillary_role = settings.ANCILLARY_CANVAS_ROLES.get(
                admin.role).get('canvas_role')
            if ('root' == settings.ANCILLARY_CANVAS_ROLES.get(
                    admin.role).get('account')):
                ancillary_account_id = ''
            else:
                ancillary_account_id = account_id

            self.data.add(AdminCSV(
                person.uwregid, ancillary_account_id, ancillary_role,
                status=status))

            logger.info(
                f'{action} ADMIN "{person.uwnetid}", account: '
                f'"{ancillary_account_id}", role "{ancillary_role}"'
            )
