# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from logging import getLogger

from django.conf import settings
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from restclients_core.exceptions import DataFailureException

from sis_provisioner.dao.user import (
    can_access_canvas,
    get_person_by_netid,
    user_email,
    user_sis_id,
)
from sis_provisioner.exceptions import UserPolicyException
from sis_provisioner.views.admin import RESTDispatch

logger = getLogger(__name__)


class LoginValidationView(APIView):
    authentication_classes = [TokenAuthentication]  # noqa: RUF012
    permission_classes = [IsAuthenticated]  # noqa: RUF012

    def post(self, request, *args, **kwargs):
        try:
            login_data = request.data['logins']
        except KeyError:
            return RESTDispatch.error_response(400, 'Missing list of logins')

        users = []
        for login in login_data:
            login = login.strip().lower()
            if not any(u.get('login') == login for u in users):
                try:
                    user = {}
                    login = self.strip_domain(login)
                    person = get_person_by_netid(login)
                    user['login'] = person.uwnetid
                    try:
                        user['full_name'] = person.get_formatted_name(
                            '{first} {last}')
                        user['is_person'] = True
                    except AttributeError:
                        user['full_name'] = person.display_name
                        user['is_person'] = False  # UW entity

                    sis_id = user_sis_id(person)
                    if not any(u.get('sis_id') == sis_id for u in users):
                        try:
                            can_access_canvas(user['login'])
                        except UserPolicyException as ex:
                            user['error'] = f'{ex}'

                        user['sis_id'] = sis_id
                        user['email'] = user_email(person)
                        users.append(user)

                except DataFailureException as ex:
                    users.append({'login': login, 'error': f'{ex.msg}'})

                except UserPolicyException as ex:
                    users.append({'login': login, 'error': f'{ex}'})

        return RESTDispatch.json_response({'users': users})

    @staticmethod
    def strip_domain(login):
        try:
            (username, domain) = login.split('@')
            if domain in getattr(settings, 'ALLOWED_ADD_USER_DOMAINS', []):
                return username
        except ValueError:
            pass
        return login
