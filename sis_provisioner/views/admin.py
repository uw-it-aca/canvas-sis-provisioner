# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from sis_provisioner.dao.user import is_group_admin, valid_net_id, valid_reg_id
from sis_provisioner.dao.term import get_current_active_term
from sis_provisioner.models.admin import Admin
from restclients_core.exceptions import DataFailureException
from uw_saml.decorators import group_required
from uw_saml.utils import get_user, is_member_of_group
from logging import getLogger
import json

logger = getLogger(__name__)


def can_view_source_data(request, service=None, url=None):
    return is_member_of_group(request, settings.RESTCLIENTS_ADMIN_GROUP)


@method_decorator(group_required(settings.CANVAS_MANAGER_ADMIN_GROUP),
                  name='dispatch')
class AdminView(View):
    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self._params(request))

    def _params(self, request):
        try:
            term = get_current_active_term()
            curr_year = term.year
            curr_quarter = term.quarter
        except DataFailureException as ex:
            logger.info('GET active term failed: {}'.format(ex))
            curr_year = ''
            curr_quarter = ''

        return {
            'EVENT_UPDATE_FREQ': getattr(
                settings, 'ADMIN_EVENT_GRAPH_FREQ', 10),
            'IMPORT_UPDATE_FREQ': getattr(
                settings, 'ADMIN_IMPORT_STATUS_FREQ', 30),
            'CURRENT_QUARTER': curr_quarter,
            'CURRENT_YEAR': curr_year,
            'can_manage_admin_group': self.can_manage_admin_group(request),
            'can_view_restclients': self.can_view_source_data(request),
            'can_manage_jobs': self.can_manage_jobs(request),
            'can_manage_external_tools': self.can_manage_external_tools(
                request),
            'can_terminate_user_sessions': self.can_terminate_user_sessions(
                request),
            'admin_group': settings.CANVAS_MANAGER_ADMIN_GROUP,
        }

    @staticmethod
    def can_view_source_data(request, service=None, url=None):
        return can_view_source_data(request, service=service, url=url)

    @staticmethod
    def can_manage_admin_group(request):
        return is_group_admin(
            settings.CANVAS_MANAGER_ADMIN_GROUP, get_user(request))

    @staticmethod
    def can_manage_course_expirations(request):
        return Admin.objects.is_account_admin(get_user(request))

    @staticmethod
    def can_manage_jobs(request):
        return Admin.objects.is_account_admin(get_user(request))

    @staticmethod
    def can_manage_external_tools(request):
        return Admin.objects.is_account_admin(get_user(request))

    @staticmethod
    def can_terminate_user_sessions(request):
        return is_member_of_group(request, settings.RESTCLIENTS_ADMIN_GROUP)

    @staticmethod
    def can_merge_users(request):
        return is_member_of_group(request, settings.RESTCLIENTS_ADMIN_GROUP)

    @staticmethod
    def can_create_user_course(request):
        return is_member_of_group(request, settings.RESTCLIENTS_ADMIN_GROUP)


class ImportStatus(AdminView):
    template_name = 'canvas_admin/status.html'


class ManageCourses(AdminView):
    template_name = 'canvas_admin/courses.html'


class ManageUsers(AdminView):
    template_name = 'canvas_admin/users.html'


class ManageGroups(AdminView):
    template_name = 'canvas_admin/groups.html'


class ManageAdmins(AdminView):
    template_name = 'canvas_admin/admins.html'


class ManageJobs(AdminView):
    template_name = 'canvas_admin/jobs.html'


class ManageExternalTools(AdminView):
    template_name = 'canvas_admin/external_tools.html'


class RESTDispatch(AdminView):
    @staticmethod
    def error_response(status, message='', content={}):
        content['error'] = '{}'.format(message)
        return HttpResponse(json.dumps(content),
                            status=status,
                            content_type='application/json')

    @staticmethod
    def json_response(content='', status=200):
        return HttpResponse(json.dumps(content, sort_keys=True),
                            status=status,
                            content_type='application/json')

    @staticmethod
    def regid_from_request(data):
        regid = data.get('reg_id', '').strip().upper()
        valid_reg_id(regid)
        return regid

    @staticmethod
    def netid_from_request(data):
        netid = data.get('net_id', '').strip().lower()
        valid_net_id(netid)
        return netid


class OpenRESTDispatch(View):
    @staticmethod
    def error_response(status, message='', content={}):
        content['error'] = '{}'.format(message)
        return HttpResponse(json.dumps(content),
                            status=status,
                            content_type='application/json')

    @staticmethod
    def json_response(content='', status=200):
        return HttpResponse(json.dumps(content, sort_keys=True),
                            status=status,
                            content_type='application/json')
