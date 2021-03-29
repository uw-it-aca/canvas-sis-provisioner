# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from uw_pws import PWS
from uw_gws import GWS
from uw_gws.models import GroupEntity
from uw_gws.exceptions import InvalidGroupID
from uw_canvas.models import CanvasUser
from restclients_core.exceptions import DataFailureException
from sis_provisioner.exceptions import (
    UserPolicyException, MissingLoginIdException, TemporaryNetidException,
    InvalidLoginIdException)
import re

RE_ADMIN_NETID = re.compile(r"^[a-z]adm_[a-z][a-z0-9]{0,7}$", re.I)
RE_APPLICATION_NETID = re.compile(r"^a_[\w]{1,18}$", re.I)
RE_TEMPORARY_NETID = re.compile(
    r"^(?:wire|event|lib|lawlib|uwctc)[0-9]{4,}$", re.I)
RE_CANVAS_ID = re.compile(r"^\d+$")


def is_group_member(group_id, login_id, act_as=None):
    return GWS(act_as=act_as).is_effective_member(group_id, login_id)


def is_group_admin(group_id, login_id):
    user = GroupEntity(name=login_id, type=GroupEntity.UWNETID_TYPE)
    group = GWS().get_group_by_id(group_id)
    return (user in group.admins or user in group.updaters)


def valid_net_id(login_id):
    if not login_id:
        raise MissingLoginIdException('Missing UWNetID')

    if RE_TEMPORARY_NETID.match(login_id):
        raise TemporaryNetidException('Temporary UWNetID not permitted')

    if not PWS().valid_uwnetid(login_id):
        raise InvalidLoginIdException('Not a valid UWNetID')


def valid_admin_net_id(login_id):
    if RE_ADMIN_NETID.match(login_id) is None:
        raise InvalidLoginIdException('Not a valid Admin UWNetID')


def valid_application_net_id(login_id):
    if RE_APPLICATION_NETID.match(login_id) is None:
        raise InvalidLoginIdException('Not a valid Application UWNetID')


def valid_nonpersonal_net_id(netid):
    try:
        valid_admin_net_id(netid)
    except UserPolicyException:
        try:
            valid_application_net_id(netid)
        except InvalidLoginIdException:
            group = getattr(settings, 'NONPERSONAL_NETID_EXCEPTION_GROUP', '')
            try:
                if (not group or not is_group_member(group, netid)):
                    raise InvalidLoginIdException('UWNetID not permitted')
            except InvalidGroupID:
                raise InvalidLoginIdException('UWNetID not permitted')


def valid_reg_id(regid):
    if not PWS().valid_uwregid(regid):
        raise InvalidLoginIdException('UWNetID not permitted')


def valid_gmail_id(login_id):
    try:
        (username, domain) = login_id.lower().split("@")
        username = username.split("+", 1)[0].replace(".", "")
        if not len(username):
            raise InvalidLoginIdException(
                "Invalid username: {}".format(login_id))
    except Exception:
        raise InvalidLoginIdException("Invalid username: {}".format(login_id))

    if domain not in getattr(settings, 'ALLOWED_LOGIN_DOMAINS', []):
        raise InvalidLoginIdException("Invalid domain: {}".format(login_id))

    return "{}@{}".format(username, domain)


def valid_canvas_user_id(canvas_id):
    if (RE_CANVAS_ID.match(str(canvas_id)) is None):
        raise UserPolicyException("Invalid Canvas ID: {}".format(canvas_id))


def user_sis_id(user):
    return user.uwregid if hasattr(user, 'uwregid') else user.sis_user_id


def user_email(user):
    if hasattr(user, 'uwnetid') and user.uwnetid is not None:
        return '{}@uw.edu'.format(user.uwnetid)
    elif hasattr(user, 'email'):
        return user.email  # CanvasUser
    else:
        raise UserPolicyException('Invalid user')


def user_fullname(user):
    try:
        return user.get_first_last_name()
    except AttributeError:
        if hasattr(user, 'display_name'):
            return (user.display_name,)  # UW Entity
        elif hasattr(user, 'sis_user_id'):
            return (user.email.split('@')[0],)  # CanvasUser
        else:
            raise UserPolicyException('Invalid user')


def can_access_canvas(login_id):
    try:
        valid_gmail_id(login_id)
        return True
    except InvalidLoginIdException:
        pass

    login_group_id = getattr(settings, 'ALLOWED_CANVAS_LOGIN_USERS')
    if not is_group_member(login_group_id, login_id):
        raise UserPolicyException('UWNetID not permitted')
    return True


def get_person_by_netid(netid):
    pws = PWS()
    try:
        valid_net_id(netid)
        person = pws.get_person_by_netid(netid)

    except DataFailureException as err:
        if err.status == 404:  # Non-personal netid?
            valid_nonpersonal_net_id(netid)
            person = pws.get_entity_by_netid(netid)
        else:
            raise

    return person


def get_person_by_regid(regid):
    pws = PWS()
    try:
        person = pws.get_person_by_regid(regid)
        valid_net_id(person.uwnetid)

    except DataFailureException as err:
        if err.status == 404:  # Non-personal regid?
            person = pws.get_entity_by_regid(regid)
            valid_nonpersonal_net_id(person.uwnetid)
        else:
            raise

    return person


def get_person_by_gmail_id(gmail_id):
    return CanvasUser(sis_user_id=valid_gmail_id(gmail_id),
                      login_id=gmail_id.lower(),
                      email=gmail_id)
