# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

import re
import json
import datetime
from logging import getLogger
from restclients_core.exceptions import (
    InvalidNetID, InvalidRegID, DataFailureException)
from uw_sws.models import Person
from uw_sws.enrollment import enrollment_search_url_prefix
from uw_pws import PERSON_PREFIX
from sis_provisioner.exceptions import UserPolicyException
from sis_provisioner.dao.canvas import (
    get_user_by_sis_id, create_user, merge_all_users_for_person)
from sis_provisioner.dao.user import (
    get_person_by_netid, get_person_by_regid, get_person_by_gmail_id,
    can_access_canvas)
from sis_provisioner.models.user import User
from sis_provisioner.views.admin import RESTDispatch

logger = getLogger(__name__)


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
                net_id = self.netid_from_request(request.GET)
                person = get_person_by_netid(net_id)
                return self.response_for_person(person)
            elif 'reg_id' in request.GET:
                reg_id = self.regid_from_request(request.GET)
                person = get_person_by_regid(reg_id)
                return self.response_for_person(person)
            else:
                return self.error_response(400, "Unrecognized user ID")

        except DataFailureException as err:
            data = json.loads(err.msg)
            return self.error_response(
                400, "{} {}".format(err.status, data["StatusDescription"]))
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
                net_id = self.netid_from_request(rep)
                user = User.objects.get(net_id=net_id)
                return self.error_response(409, "User already exists")
        except User.DoesNotExist:
            try:
                user = User.objects.add_user_by_netid(
                    net_id, priority=User.PRIORITY_IMMEDIATE)
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
            'enrollment_url': None,
        }

        if self.can_view_source_data(self.request):
            response['person_url'] = (
                '/restclients/view/pws{api_path}/{uwregid}/full.json').format(
                    api_path=PERSON_PREFIX,
                    uwregid=person.uwregid)
            response['enrollment_url'] = (
                '/restclients/view/sws{api_path}{uwregid}').format(
                    api_path=enrollment_search_url_prefix,
                    uwregid=person.uwregid)

        try:
            user = User.objects.get(reg_id=person.uwregid)
            response.update(user.json_data())
            response['can_access_canvas'] = can_access_canvas(person.uwnetid)
        except User.DoesNotExist:
            pass
        except UserPolicyException:
            response['can_access_canvas'] = False

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
            'queue_id': None,
        }

        try:
            user = get_user_by_sis_id(person.sis_user_id)
            response['provisioned_date'] = datetime.datetime.now().isoformat()
            response['display_name'] = user.name
            response['can_access_canvas'] = can_access_canvas(person.login_id)
        except DataFailureException:
            pass
        except UserPolicyException:
            response['can_access_canvas'] = False

        return self.json_response(response)


class UserMergeView(RESTDispatch):
    def get(self, request, *args, **kwargs):
        reg_id = kwargs.get('reg_id')
        try:
            person = get_person_by_regid(reg_id)
            users = get_all_users_for_person()
        except DataFailureException as ex:
            return self.error_response(ex.status, message=ex.msg)

        response = []
        for user in users:
            response.append(user.post_data())
        return self.json_response(response)

    def put(self, request, *args, **kwargs):
        reg_id = kwargs.get('reg_id')
        try:
            person = get_person_by_regid(reg_id)
            user = merge_all_users_for_person(person)
        except DataFailureException as ex:
            return self.error_response(ex.status, message=ex.msg)
