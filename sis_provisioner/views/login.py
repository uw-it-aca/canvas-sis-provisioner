from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from sis_provisioner.views.admin import RESTDispatch
from sis_provisioner.dao.user import (
    get_person_by_netid, get_person_by_gmail_id, user_sis_id, user_email,
    user_fullname)
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
            login = login.lower()
            if not any(u.get('login') == login for u in users):
                try:
                    user = {}
                    try:
                        person = get_person_by_gmail_id(login)
                        user['login'] = person.login_id
                    except UserPolicyException:
                        person = get_person_by_netid(login)
                        user['login'] = person.uwnetid

                    sis_id = user_sis_id(person)
                    if not any(u.get('sis_id') == sis_id for u in users):
                        user['sis_id'] = sis_id
                        user['email'] = user_email(person)
                        name = user_fullname(person)
                        if len(name) == 2:
                            user['first_name'] = name[0]
                            user['last_name'] = name[1]
                            user['full_name'] = ' '.join(name)
                        else:
                            user['first_name'] = None
                            user['last_name'] = None
                            user['full_name'] = name[0]
                        users.append(user)

                except DataFailureException as ex:
                    users.append({'login': login, 'error': ex.msg})

                except UserPolicyException as ex:
                    users.append({'login': login, 'error': '{}'.format(ex)})

        return RESTDispatch.json_response({'users': users})
