# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.conf import settings
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from sis_provisioner.views.admin import RESTDispatch
from sis_provisioner.dao.user import (
    get_person_by_netid, can_access_canvas, user_sis_id, user_email)
from sis_provisioner.exceptions import UserPolicyException
from restclients_core.exceptions import DataFailureException
from logging import getLogger

logger = getLogger(__name__)


class LoginValidationView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            login_data = request.data['logins']
        except KeyError as ex:
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
                    except AttributeError as ex:
                        user['full_name'] = person.display_name
                        user['is_person'] = False  # UW entity

                    sis_id = user_sis_id(person)
                    if not any(u.get('sis_id') == sis_id for u in users):
                        try:
                            can_access_canvas(user['login'])
                        except UserPolicyException as ex:
                            user['error'] = '{}'.format(ex)

                        user['sis_id'] = sis_id
                        user['email'] = user_email(person)
                        users.append(user)

                except DataFailureException as ex:
                    users.append({'login': login, 'error': ex.msg})

                except UserPolicyException as ex:
                    users.append({'login': login, 'error': '{}'.format(ex)})

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
