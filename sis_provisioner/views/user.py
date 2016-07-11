import re
import json
import datetime
from django.http import HttpResponse
from logging import getLogger
from restclients.canvas.users import Users as CanvasUsers
from restclients.exceptions import InvalidNetID, InvalidRegID
from restclients.exceptions import DataFailureException
from restclients.models.sws import Person
from sis_provisioner.models import User, PRIORITY_IMMEDIATE
from sis_provisioner.views.rest_dispatch import RESTDispatch
from sis_provisioner.views import regid_from_request, netid_from_request
from sis_provisioner.policy import UserPolicy
from sis_provisioner.loader import load_user
from canvas_admin.views import can_view_source_data


class UserView(RESTDispatch):
    """ Performs actions on a Course at /api/v1/user/<reg id>.
        GET returns 200 with User model (augmented with person)
        PUT returns 200 and updates User model
    """
    def __init__(self):
        self._log = getLogger(__name__)
        self._user_policy = UserPolicy()

    def GET(self, request, **kwargs):
        try:
            if 'gmail_id' in request.GET:
                gmail_id = request.GET.get('gmail_id', '').strip()
                person = self._user_policy.get_person_by_gmail_id(gmail_id)
                return self.response_for_google_person(person)
            elif 'net_id' in request.GET:
                net_id = netid_from_request(request.GET)
                person = self._user_policy.get_person_by_netid(net_id)
                return self.response_for_person(person)
            elif 'reg_id' in request.GET:
                reg_id = regid_from_request(request.GET)
                person = self._user_policy.get_person_by_regid(reg_id)
                return self.response_for_person(person)
            else:
                return self.json_response('{"error":"Unrecognized user ID"}',
                                          status=400)

        except DataFailureException as err:
            data = json.loads(err.msg)
            return self.json_response('{"error":"%s %s"}' % (
                err.status, data["StatusDescription"]), status=400)

        except Exception as err:
            return self.json_response('{"error":"%s"}' % err, status=400)

    def POST(self, request, **kwargs):
        try:
            rep = json.loads(request.read())

            if 'gmail_id' in rep:
                gmail_id = rep.get('gmail_id', '').strip()
                person = self._user_policy.get_person_by_gmail_id(gmail_id)
                user = CanvasUsers().create_user(person)
                return HttpResponse()
            else:
                net_id = netid_from_request(rep)
                user = User.objects.get(net_id=net_id)
                return self.json_response('{"error":"User already exists"}',
                                          status=409)
        except User.DoesNotExist:
            try:
                person = self._user_policy.get_person_by_netid(net_id)
                user = load_user(person)
                user.priority = PRIORITY_IMMEDIATE
                user.save()
                return HttpResponse()

            except Exception as err:
                return self.json_response('{"error": "%s"}' % err, status=400)

        except Exception as err:
            return self.json_response('{"error": "%s"}' % err, status=400)

    def response_for_person(self, person):
        response = {
            'is_valid': True,
            'display_name': person.full_name if (
                isinstance(person, Person)) else person.display_name,
            'net_id': person.uwnetid,
            'reg_id': person.uwregid,
            'gmail_id': None,
            'added_date': None,
            'provisioned_date': None,
            'priority': 'normal',
            'queue_id': None,
            'person_url': None,
            'enrollment_url': None
        }

        if can_view_source_data():
            response['person_url'] = '%s/person/%s.json' % (
                '/restclients/view/pws/identity/v1', person.uwregid)
            response['enrollment_url'] = '%s/enrollment.json?reg_id=%s' % (
                '/restclients/view/sws/student/v5', person.uwregid)

        try:
            user = User.objects.get(reg_id=person.uwregid)
            response.update(user.json_data())

        except User.DoesNotExist:
            pass

        return self.json_response(json.dumps(response))

    def response_for_google_person(self, person):
        response = {
            'is_valid': True,
            'display_name': '',
            'net_id': None,
            'reg_id': None,
            'gmail_id': person.login_id,
            'added_date': None,
            'provisioned_date': None,
            'priority': 'normal',
            'queue_id': None
        }

        try:
            user = CanvasUsers().get_user_by_sis_id(person.sis_user_id)
            response['provisioned_date'] = datetime.datetime.now().isoformat()
            response['display_name'] = user.name

        except DataFailureException:
            pass

        return self.json_response(json.dumps(response))
