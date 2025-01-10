# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


import json
import datetime
from logging import getLogger
from urllib.parse import urlencode
from django.conf import settings
from django.utils.decorators import method_decorator
from restclients_core.exceptions import (
    InvalidNetID, InvalidRegID, DataFailureException)
from uw_sws.registration import registration_res_url_prefix
from uw_pws import PERSON_PREFIX
from uw_saml.decorators import group_required
from sis_provisioner.exceptions import (
    UserPolicyException, InvalidLoginIdException)
from sis_provisioner.dao.canvas import (
    get_user_by_sis_id, create_user, terminate_user_sessions,
    get_all_users_for_person, merge_all_users_for_person)
from sis_provisioner.dao.user import (
    get_person_by_netid, get_person_by_regid, valid_reg_id, can_access_canvas)
from sis_provisioner.dao.term import get_current_active_term
from sis_provisioner.models.user import User
from sis_provisioner.models.course import Course
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
            return self.error_response(400, f"{err.status} {err.msg}")
        except Exception as err:
            return self.error_response(400, err)

    def put(self, request, *args, **kwargs):
        reg_id = kwargs.get("reg_id")
        body = request.read()
        priority = None

        try:
            new_values = json.loads(body)
        except Exception as err:
            return self.error_response(400, f"Unable to parse JSON: {err}")

        try:
            # only priority PUTable right now
            priority_str = new_values.get("priority", "").lower()
            for key, val in User.PRIORITY_CHOICES:
                if val == priority_str:
                    priority = key

            if priority is None:
                return self.error_response(
                    400, f"Invalid priority: '{priority_str}'")

            person = get_person_by_regid(reg_id)
            User.objects.update_priority(person, priority)

            logger.info("{} set priority={} for user {}".format(
                get_user(request), priority, reg_id))
        except DataFailureException as ex:
            return self.error_response(ex.status, message=ex.msg)

        return self.response_for_person(person)

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
            'can_create_user_course': False,
            'masquerade_url': None,
            'enrollment_url': None,
            'canvas_users': [],
        }

        if can_view_source_data:
            curr_term = get_current_active_term()
            response['enrollment_url'] = '/restclients/view/sws{}?{}'.format(
                registration_res_url_prefix, urlencode({
                    'reg_id': person.uwregid,
                    'year': curr_term.year,
                    'quarter': curr_term.quarter,
                    'future_terms': '1',
                    'transcriptable_course': 'all',
                    'verbose': 'true'}))

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
            response['can_access_canvas'] = (
                response['canvas_users'][0]['can_access_canvas'])

            if response['canvas_users'][0]['sis_user_id'] != person.uwregid:
                if self.can_merge_users(self.request):
                    response['canvas_users'][0]['can_update_sis_id'] = True
            else:
                if (self.can_create_user_course(self.request) and
                        response['can_access_canvas']):
                    response['can_create_user_course'] = True

            if (response['can_access_canvas'] and self.can_masquerade_as_user(
                    self.request, response['canvas_users'][0]['login_id'])):
                user_id = response['canvas_users'][0]['id']
                response['masquerade_url'] = (
                    f'https://canvas.uw.edu/users/{{user_id}}/masquerade')
        else:
            response['can_merge_users'] = self.can_merge_users(self.request)

        return self.json_response(response)


class UserMergeView(UserView):
    def put(self, request, *args, **kwargs):
        if not self.can_merge_users(request):
            return self.error_response(401, 'Unauthorized')

        reg_id = kwargs.get('reg_id')
        try:
            person = get_person_by_regid(reg_id)
            merge_all_users_for_person(person)
        except DataFailureException as ex:
            return self.error_response(ex.status, message=ex.msg)

        return self.response_for_person(person)


class UserSessionsView(UserView):
    def delete(self, request, *args, **kwargs):
        if not self.can_terminate_user_sessions(request):
            return self.error_response(401, 'Unauthorized')

        user_id = kwargs.get('user_id')
        try:
            terminate_user_sessions(user_id)
        except DataFailureException as ex:
            return self.error_response(ex.status, message=ex.msg)

        return self.json_response({'user_id': user_id})


class UserCourseView(UserView):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        if not self.can_create_user_course(request):
            return self.error_response(401, 'Unauthorized')

        login_id = kwargs.get('net_id')
        name = json.loads(request.body).get('course_name')

        try:
            can_access_canvas(login_id)
            person = get_person_by_netid(login_id)
            course = Course.objects.create_user_course(person.uwregid, name)
        except DataFailureException as ex:
            return self.error_response(ex.status, message=ex.msg)
        except UserPolicyException as ex:
            return self.error_response(400, f'User not permitted: {login_id}')

        resp_data = course.json_data()
        resp_data['course_url'] = '{host}/courses/{course_id}'.format(
            host=getattr(settings, 'RESTCLIENTS_CANVAS_HOST', ''),
            course_id=resp_data['canvas_course_id'])
        return self.json_response(resp_data)
