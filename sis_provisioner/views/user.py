import re
import json
import datetime
from logging import getLogger
from django.conf import settings
from django.utils.decorators import method_decorator
from restclients_core.exceptions import (
    InvalidNetID, InvalidRegID, DataFailureException)
from uw_sws.models import Person
from sis_provisioner.dao.canvas import get_user_by_sis_id, create_user
from sis_provisioner.dao.user import (
    get_person_by_netid, get_person_by_regid, get_person_by_gmail_id)
from sis_provisioner.models import User, PRIORITY_IMMEDIATE
from sis_provisioner.views.rest_dispatch import RESTDispatch
from sis_provisioner.views import (
    group_required, regid_from_request, netid_from_request)
from sis_provisioner.views.admin import can_view_source_data


logger = getLogger(__name__)


@method_decorator(group_required(settings.CANVAS_MANAGER_ADMIN_GROUP),
                  name='dispatch')
class UserView(RESTDispatch):
    """ Performs actions on a Course at /api/v1/user/<reg id>.
        GET returns 200 with User model (augmented with person)
        PUT returns 200 and updates User model
    """
    def get(self, request, *args, **kwargs):
        try:
            if 'gmail_id' in request.GET:
                gmail_id = request.GET.get('gmail_id', '').strip()
                person = get_person_by_gmail_id(gmail_id)
                return self.response_for_google_person(person)
            elif 'net_id' in request.GET:
                net_id = netid_from_request(request.GET)
                person = get_person_by_netid(net_id)
                return self.response_for_person(person)
            elif 'reg_id' in request.GET:
                reg_id = regid_from_request(request.GET)
                person = get_person_by_regid(reg_id)
                return self.response_for_person(person)
            else:
                return self.error_response(400, "Unrecognized user ID")

        except DataFailureException as err:
            data = json.loads(err.msg)
            return self.error_response(
                400, "%s %s" % (err.status, data["StatusDescription"]))
        except Exception as err:
            return self.error_response(400, err)

    def post(self, request, *args, **kwargs):
        try:
            rep = json.loads(request.read())

            if 'gmail_id' in rep:
                gmail_id = rep.get('gmail_id', '').strip()
                person = get_person_by_gmail_id(gmail_id)
                user = create_user(person)
                return self.json_response()
            else:
                net_id = netid_from_request(rep)
                user = User.objects.get(net_id=net_id)
                return self.error_response(409, "User already exists")
        except User.DoesNotExist:
            try:
                user = User.objects.add_user(get_person_by_netid(net_id),
                                             priority=PRIORITY_IMMEDIATE)
                return self.json_response()

            except Exception as err:
                return self.error_response(400, err)

        except Exception as err:
            return self.error_response(400, err)

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

        if can_view_source_data(self.request):
            response['person_url'] = '%s/person/%s.json' % (
                '/restclients/view/pws/identity/v1', person.uwregid)
            response['enrollment_url'] = '%s/enrollment.json?reg_id=%s' % (
                '/restclients/view/sws/student/v5', person.uwregid)

        try:
            user = User.objects.get(reg_id=person.uwregid)
            response.update(user.json_data())

        except User.DoesNotExist:
            pass

        return self.json_response(response)

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
            user = get_user_by_sis_id(person.sis_user_id)
            response['provisioned_date'] = datetime.datetime.now().isoformat()
            response['display_name'] = user.name

        except DataFailureException:
            pass

        return self.json_response(response)
