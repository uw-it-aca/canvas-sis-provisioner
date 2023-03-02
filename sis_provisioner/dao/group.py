# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.conf import settings
from django.utils.timezone import utc
from uw_gws import GWS
from uw_gws.exceptions import InvalidGroupID
from restclients_core.exceptions import DataFailureException
from sis_provisioner.dao.user import valid_net_id, valid_gmail_id
from sis_provisioner.exceptions import (
    UserPolicyException, GroupPolicyException, GroupNotFoundException,
    GroupUnauthorizedException)
from logging import getLogger
import re

logger = getLogger(__name__)


def valid_group_id(group_id):
    try:
        GWS()._valid_group_id(group_id)
    except InvalidGroupID:
        raise GroupPolicyException("Invalid Group ID: {}".format(group_id))

    RE_GROUP_DISALLOWED = re.compile(r'^({}).*$'.format('|'.join(
        getattr(settings, 'DISALLOWED_UW_GROUPS', []))))
    if RE_GROUP_DISALLOWED.match(group_id):
        raise GroupPolicyException(
            "This group cannot be used in Canvas: {}".format(group_id))


def is_modified_group(group_id, changed_since_dt):
    try:
        group = GWS().get_group_by_id(group_id)
        member_mtime = group.membership_modified.replace(tzinfo=utc)
        return (member_mtime > changed_since_dt)
    except DataFailureException as err:
        if err.status == 404:
            raise GroupNotFoundException(
                "Group not found: {}".format(group_id))
        else:
            raise


def get_group(act_as, group_id):
    return GWS(act_as=act_as).get_group_by_id(group_id)


def search_groups(act_as, **kwargs):
    if not kwargs.get('scope'):
        kwargs['scope'] = 'all'

    if kwargs.get('name') and not kwargs['name'].endswith('*'):
        kwargs['name'] += '*'

    groups = []
    for group in GWS(act_as=act_as).search_groups(**kwargs):
        try:
            valid_group_id(group.name)
            groups.append(group)
        except GroupPolicyException:
            pass

    return groups


def get_sis_import_members():
    valid_members = {}
    group_id = getattr(settings, 'SIS_IMPORT_USERS')
    for member in GWS().get_effective_members(group_id):
        try:
            if member.is_uwnetid():
                valid_net_id(member.name)
                valid_members[member.name] = member
        except UserPolicyException:
            pass

    return list(valid_members.values())


def get_effective_members(group_id, act_as=None):
    gws = GWS(act_as=act_as)

    def _get_members(group_id):
        valid_members = {}
        invalid_members = {}
        member_group_ids = []

        try:
            valid_group_id(group_id)
            for member in gws.get_members(group_id):
                try:
                    if member.is_uwnetid():
                        valid_net_id(member.name)
                        valid_members[member.name] = member

                    elif member.is_eppn():
                        valid_gmail_id(member.name)
                        valid_members[member.name] = member

                    elif member.is_group():
                        (valid_sub, invalid_sub,
                            member_subgroups) = _get_members(member.name)
                        valid_members.update(valid_sub)
                        invalid_members.update(invalid_sub)
                        member_group_ids += [member.name] + member_subgroups

                except (UserPolicyException, GroupPolicyException) as err:
                    member.error = err
                    invalid_members[member.name] = member

        except DataFailureException as err:
            # Group not found or access denied is ok
            if err.status == 404:
                raise GroupNotFoundException(
                    "Group not found: {}".format(group_id))
            elif err.status == 401:
                raise GroupUnauthorizedException(
                    "Group not permitted for {}: {}".format(
                        gws.act_as, group_id))
            else:
                raise

        except GroupPolicyException as err:
            raise

        except RecursionError as err:
            logger.info("Error: {}, Group: {}, Member groups: {}".format(
                err, group_id, member_group_ids))

        return (valid_members, invalid_members, member_group_ids)

    (valid_members, invalid_members, member_group_ids) = _get_members(group_id)
    return (list(valid_members.values()),
            list(invalid_members.values()),
            member_group_ids)
