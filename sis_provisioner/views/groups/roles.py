# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from restclients_core.exceptions import DataFailureException
from blti.views import RESTDispatch
from sis_provisioner.dao.canvas import get_course_roles_in_account


class CanvasCourseRoles(RESTDispatch):
    """ Performs actions on a Canvas account course roles
        GET returns 200 with account course roles.
    """
    authorized_role = 'admin'

    def get(self, request, *args, **kwargs):
        roles = []

        try:
            for r in get_course_roles_in_account(self.blti.account_sis_id):
                roles.append(r.label)

            return self.json_response({'roles': roles})

        except DataFailureException as err:
            return self.error_response(500, err.msg)
        except Exception as err:
            return self.error_response(500, err)
