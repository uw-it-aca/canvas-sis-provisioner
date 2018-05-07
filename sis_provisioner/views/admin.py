from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from sis_provisioner.dao.user import is_group_admin
from sis_provisioner.dao.term import get_term_by_date
from sis_provisioner.models.astra import AdminManager
from sis_provisioner.views import group_required, get_user, is_member_of_group
from restclients_core.exceptions import DataFailureException
from datetime import datetime
import json
import re


def _admin(request, template):
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
        'can_manage_admin_group': can_manage_admin_group(request),
        'can_view_restclients': can_view_source_data(request),
        'admin_group': settings.CANVAS_MANAGER_ADMIN_GROUP,
    }
    return render(request, template, params)


@group_required(settings.CANVAS_MANAGER_ADMIN_GROUP)
def ImportStatus(request, template='canvas_admin/status.html'):
    return _admin(request, template)


@group_required(settings.CANVAS_MANAGER_ADMIN_GROUP)
def ManageCourses(request, template='canvas_admin/courses.html'):
    return _admin(request, template)


@group_required(settings.CANVAS_MANAGER_ADMIN_GROUP)
def ManageUsers(request, template='canvas_admin/users.html'):
    return _admin(request, template)


@group_required(settings.CANVAS_MANAGER_ADMIN_GROUP)
def ManageGroups(request, template='canvas_admin/groups.html'):
    return _admin(request, template)


@group_required(settings.CANVAS_MANAGER_ADMIN_GROUP)
def ManageAdmins(request, template='canvas_admin/admins.html'):
    return _admin(request, template)


@group_required(settings.CANVAS_MANAGER_ADMIN_GROUP)
def ManageJobs(request, template='canvas_admin/jobs.html'):
    return _admin(request, template)


@group_required(settings.CANVAS_MANAGER_ADMIN_GROUP)
def ManageExternalTools(request, template='canvas_admin/external_tools.html'):
    params = {'read_only': False if (
        can_manage_external_tools(request)) else True}
    return render(request, template, params)


def can_view_source_data(request):
    return is_member_of_group(request, settings.RESTCLIENTS_ADMIN_GROUP)


def can_manage_admin_group(request):
    return is_group_admin(
        settings.CANVAS_MANAGER_ADMIN_GROUP, get_user(request))


def can_manage_jobs(request):
    return AdminManager().is_account_admin(get_user(request))


def can_manage_external_tools(request):
    return can_manage_jobs(request)
