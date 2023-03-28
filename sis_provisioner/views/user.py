# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


import json
import datetime
from logging import getLogger
from django.conf import settings
from django.utils.decorators import method_decorator
from restclients_core.exceptions import (
    InvalidNetID, InvalidRegID, DataFailureException)
from uw_sws.enrollment import enrollment_search_url_prefix
from uw_pws import PERSON_PREFIX
from uw_saml.decorators import group_required
from sis_provisioner.exceptions import (
    UserPolicyException, InvalidLoginIdException)
from sis_provisioner.dao.canvas import (
    get_user_by_sis_id, create_user, terminate_user_sessions,
    get_all_users_for_person, merge_all_users_for_person)
from sis_provisioner.dao.user import (
    get_person_by_netid, get_person_by_regid, valid_reg_id, can_access_canvas)
from sis_provisioner.models.user import User
from sis_provisioner.views.admin import RESTDispatch

logger = getLogger(__name__)


class UserView(RESTDispatch):
    """ Performs actions on a Course at /api/v1/user/<reg id>.
        GET returns 200 with User model (augmented with person)
        PUT returns 200 and updates User model
    """
    def get(self, request, *args, **kwargs):
        user_id = ''
        if 'user_id' in request.GET:
            user_id = request.GET.get('user_id', '').strip()

        if not len(user_id):
            return self.error_response(400, "Missing User ID")

        try:
            try:
                valid_reg_id(user_id.upper())
                person = get_person_by_regid(user_id.upper())
            except InvalidLoginIdException:
                person = get_person_by_netid(user_id.lower())

            return self.response_for_person(person)

        except DataFailureException as err:
            data = json.loads(err.msg)
            return self.error_response(
                400, "{} {}".format(err.status, err.msg))
        except Exception as err:
            return self.error_response(400, err)

    def post(self, request, *args, **kwargs):
        try:
            rep = json.loads(request.read())
            net_id = self.netid_from_request(rep)
            person = get_person_by_netid(net_id)
            user = User.objects.add_user_by_netid(
                person.uwnetid, priority=User.PRIORITY_IMMEDIATE)
            return self.response_for_person(person)

        except DataFailureException as err:
            data = json.loads(err.msg)
            return self.error_response(
                400, "{} {}".format(err.status, err.msg))
        except Exception as err:
            return self.error_response(400, err)

    def response_for_person(self, person):
        can_view_source_data = self.can_view_source_data(self.request)
        can_terminate_user_sessions = self.can_terminate_user_sessions(
            self.request)

        response = {
            'is_valid': True,
            'display_name': person.display_name,
            'net_id': person.uwnetid,
            'reg_id': person.uwregid,
            'added_date': None,
            'provisioned_date': None,
            'priority': 'normal',
            'queue_id': None,
            'can_merge_users': False,
            'enrollment_url': '/restclients/view/sws{}{}'.format(
                enrollment_search_url_prefix, person.uwregid) if (
                    can_view_source_data) else None,
            'canvas_users': [],
        }

        # Add the provisioning information for this user
        user = User.objects._find_existing(person.uwnetid, person.uwregid)
        if user:
            response.update(user.json_data())

        # Get the Canvas data for this user
        for user in get_all_users_for_person(person):
            user_data = user.json_data()
            try:
                user_data['can_access_canvas'] = can_access_canvas(
                    user.login_id)
            except UserPolicyException:
                user_data['can_access_canvas'] = False

            if can_view_source_data and user.sis_user_id:
                user_data['person_url'] = (
                    '/restclients/view/pws{api_path}/{uwregid}/full.json'
                ).format(api_path=PERSON_PREFIX, uwregid=user.sis_user_id)

            user_data['can_update_sis_id'] = False
            user_data['can_terminate_user_sessions'] = (
                user_data['can_access_canvas'] and
                user_data['last_login'] is not None and
                can_terminate_user_sessions)

            response['canvas_users'].append(user_data)

        if not len(response['canvas_users']):
            try:
                response['can_access_canvas'] = can_access_canvas(
                    person.uwnetid)
            except UserPolicyException:
                response['can_access_canvas'] = False
        elif len(response['canvas_users']) == 1:
            if (response['canvas_users'][0]['sis_user_id'] != person.uwregid and  # noqa
                    self.can_merge_users(self.request)):
                response['canvas_users'][0]['can_update_sis_id'] = True
        else:
            response['can_merge_users'] = self.can_merge_users(self.request)

        return self.json_response(response)


class UserMergeView(UserView):
    def put(self, request, *args, **kwargs):
        reg_id = kwargs.get('reg_id')
        try:
            person = get_person_by_regid(reg_id)
            merge_all_users_for_person(person)
        except DataFailureException as ex:
            return self.error_response(ex.status, message=ex.msg)

        return self.response_for_person(person)


class UserSessionsView(UserView):
    def delete(self, request, *args, **kwargs):
        user_id = kwargs.get('user_id')
        try:
            terminate_user_sessions(user_id)
        except DataFailureException as ex:
            return self.error_response(ex.status, message=ex.msg)

        return self.json_response({'user_id': user_id})
