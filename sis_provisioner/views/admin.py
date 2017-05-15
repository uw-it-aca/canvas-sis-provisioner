from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from sis_provisioner.dao.term import get_term_by_date
from sis_provisioner.models.astra import AdminManager
from userservice.user import UserService
from authz_group import Group
from uw_gws import GWS
from uw_gws.models import GroupUser
from restclients_core.exceptions import DataFailureException
from datetime import datetime
import json
import re


def _admin(request, template):
    if not can_view_support_app():
        return HttpResponseRedirect('/')

    curr_date = datetime.now().date()
    try:
        term = get_term_by_date(curr_date)
        curr_year = term.year
        curr_quarter = term.quarter
    except DataFailureException as ex:
        curr_year = curr_date.year
        curr_quarter = ''

    params = {
        'EVENT_UPDATE_FREQ': settings.ADMIN_EVENT_GRAPH_FREQ,
        'IMPORT_UPDATE_FREQ': settings.ADMIN_IMPORT_STATUS_FREQ,
        'CURRENT_QUARTER': curr_quarter,
        'CURRENT_YEAR': curr_year,
        'can_manage_admin_group': True if can_manage_admin_group() else False,
        'can_view_restclients': True if can_view_source_data() else False,
        'admin_group': settings.CANVAS_MANAGER_ADMIN_GROUP,
    }
    return render(request, template, params)


@login_required
def ImportStatus(request, template='canvas_admin/status.html'):
    return _admin(request, template)


@login_required
def ManageCourses(request, template='canvas_admin/courses.html'):
    return _admin(request, template)


@login_required
def ManageUsers(request, template='canvas_admin/users.html'):
    return _admin(request, template)


@login_required
def ManageGroups(request, template='canvas_admin/groups.html'):
    return _admin(request, template)


@login_required
def ManageAdmins(request, template='canvas_admin/admins.html'):
    return _admin(request, template)


@login_required
def ManageJobs(request, template='canvas_admin/jobs.html'):
    return _admin(request, template)


@login_required
def ManageExternalTools(request, template='canvas_admin/external_tools.html'):
    if not can_view_support_app():
        return HttpResponseRedirect('/')

    params = {'read_only': False if can_manage_external_tools() else True}
    return render(request, template, params)


def can_view_support_app():
    return Group().is_member_of_group(UserService().get_original_user(),
                                      settings.CANVAS_MANAGER_ADMIN_GROUP)


def can_view_source_data():
    return Group().is_member_of_group(UserService().get_original_user(),
                                      settings.RESTCLIENTS_ADMIN_GROUP)


def can_manage_admin_group():
    user = GroupUser(name=UserService().get_original_user(),
                     user_type=GroupUser.UWNETID_TYPE)
    group = GWS().get_group_by_id(settings.CANVAS_MANAGER_ADMIN_GROUP)
    return (user in group.admins or user in group.updaters)


def can_manage_jobs():
    return AdminManager().is_account_admin(UserService().get_original_user())


def can_manage_external_tools():
    return can_manage_jobs()
