from django.conf import settings
from uw_gws import GWS
from restclients_core.exceptions import DataFailureException
from sis_provisioner.dao.user import valid_net_id, valid_gmail_id
from sis_provisioner.exceptions import (
    UserPolicyException, GroupPolicyException, GroupNotFoundException,
    GroupUnauthorizedException)
import re


def valid_group_id(group_id):
    try:
        is_valid = GWS()._is_valid_group_id(group_id)
    except TypeError:
        raise GroupPolicyException("Invalid Group ID: %s" % group_id)

    if is_valid:
        RE_GROUP_BLACKLIST = re.compile(r'^(%s).*$' % ('|'.join(
            getattr(settings, 'UW_GROUP_BLACKLIST', []))))
        if RE_GROUP_BLACKLIST.match(group_id):
            raise GroupPolicyException(
                "This group cannot be used in Canvas: %s" % group_id)
    else:
        raise GroupPolicyException("Invalid Group ID: %s" % group_id)


def is_modified_group(group_id, mtime):
    try:
        group = GWS().get_group_by_id(group_id)
        return (group.membership_modified > mtime)
    except DataFailureException as err:
        if err.status == 404:
            return True
        else:
            raise


def get_sis_import_members():
    gws = GWS()

    valid_members = {}
    for group_id in getattr(settings, 'SIS_IMPORT_GROUPS', []):
        for member in gws.get_effective_members(group_id):
            try:
                if member.is_uwnetid():
                    valid_net_id(member.name)
                    valid_members[member.name] = member
            except UserPolicyException as err:
                pass

    return valid_members.values()


def get_effective_members(group_id, act_as=None):
    gws = GWS({'actas': act_as})

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
                raise GroupNotFoundException("Group not found: %s" % group_id)
            elif err.status == 401:
                raise GroupUnauthorizedException(
                    "Group not permitted for %s: %s" % (gws.actas, group_id))
            else:
                raise

        except GroupPolicyException as err:
            raise

        return (valid_members, invalid_members, member_group_ids)

    (valid_members, invalid_members, member_group_ids) = _get_members(group_id)
    return (valid_members.values(), invalid_members.values(), member_group_ids)
