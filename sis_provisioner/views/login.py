from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from sis_provisioner.views.admin import RESTDispatch
from sis_provisioner.dao.user import (
    get_person_by_netid, get_person_by_gmail_id, user_sis_id, user_email,
    user_fullname)
from restclients_core.exceptions import DataFailureException


class LoginValidationView(APIView):
    authentication_classes = [TokenAuthentication]

    def post(self, request, *args, **kwargs):
        try:
            login_data = request.data['logins']
        except KeyError as ex:
            return RESTDispatch.error_response(400, 'Missing list of logins')
        except Exception as ex:
            return RESTDispatch.error_response(400, ex)

        users = []
        for login in login_data:
            user = {}
            try:
                login = login.lower()
                if not any(u.get('login') == login for u in users):
                    try:
                        person = get_person_by_gmail_id(login)
                        user['login'] = person.login_id
                    except InvalidLoginIdException:
                        person = get_person_by_netid(login)
                        user['login'] = person.uwnetid

                    sis_id = user_sis_id(person)
                    if not any(u.get('sis_id') == sis_id for u in users):
                        user['sis_id'] = user_sis_id(person)
                        user['email'] = user_email(person)
                        user['full_name'] = user_fullname(person)

            except DataFailureException as ex:
                user['login'] = login
                user['error'] = ex.msg

            except Exception as ex:
                user['login'] = login
                user['error'] = ex

            users.append(user)

        return RESTDispatch.json_response(users)
