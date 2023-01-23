# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.conf import settings
from restclients_core.exceptions import DataFailureException
from sis_provisioner.models.group import Group
from sis_provisioner.dao.group import (
    valid_group_id, get_effective_members, get_group, search_groups)
from sis_provisioner.exceptions import (
    GroupPolicyException, GroupNotFoundException, GroupUnauthorizedException)
from blti.views import RESTDispatch
import re


class GWSDispatchException(Exception):
    pass


class GWSDispatch(RESTDispatch):
    authorized_role = 'admin'

    def actas_from_request(self, request):
        if hasattr(self, 'blti'):
            return self.blti.user_login_id
        elif request.user.is_authenticated():
            return request.user.username
        elif getattr(settings, 'BLTI_NO_AUTH') and getattr(settings, 'ACT_AS'):
            return settings.ACT_AS
        else:
            raise GWSDispatchException('No Actas')


class GWSGroup(GWSDispatch):
    """ Performs actions on a GWS
        GET returns 200 with Course details.
    """
    def get(self, request, *args, **kwargs):
        try:
            self._actas = self.actas_from_request(request)
            group_id = kwargs['group_id']

            if len(group_id):
                return self._getGWSGroupById(group_id)
            else:
                return self._getGWSGroupsByQuery(request)
        except GroupPolicyException as err:
            return self.error_response(400, err)
        except GWSDispatchException:
            return self.error_response(401, "Unauthorized request")
        except DataFailureException as err:
            if err.status == 404:
                return self.error_response(404, "UW Group not found")
            else:
                return self.error_response(404, err.msg)
        except Exception as err:
            return self.error_response(404, err)

    def _getGWSGroupById(self, group_id):
        valid_group_id(group_id)
        group = get_group(self._actas, group_id)
        return self.json_response({
            'name': group.name, 'title': group.display_name})

    def _getGWSGroupsByQuery(self, request):
        terms = {}
        for q in ['name', 'stem', 'member', 'owner', 'role', 'scope']:
            val = request.GET.get(q)
            if val:
                terms[q] = val
                if q == 'name' or q == 'stem':
                    valid_group_id(val)

        groups = []
        for group in search_groups(self._actas, **terms):
            groups.append({'name': group.name, 'title': group.display_name})

        return self.json_response({'groups': groups})


class GWSGroupMembers(GWSDispatch):
    """ Performs actions on a GWS
        GET returns 200 with Course details.
    """
    def get(self, request, *args, **kwargs):
        try:
            param = kwargs['group_id']
            if re.match(r'^\d+$', param):  # Existing group
                group = Group.objects.get(id=param, is_deleted=None)
                group_id = group.group_id
                act_as = group.added_by
            else:
                group_id = param
                act_as = self.actas_from_request(request)

            (valid_members, invalid_members,
                member_group_ids) = get_effective_members(group_id,
                                                          act_as=act_as)

            return self.json_response({
                "membership": [member.name for member in valid_members],
                "invalid": [member.name for member in invalid_members]
            })

        except (GroupPolicyException, GroupUnauthorizedException) as err:
            return self.error_response(403, err)
        except (Group.DoesNotExist, GroupNotFoundException):
            return self.error_response(404, 'UW Group not found')
        except GWSDispatchException:
            return self.error_response(401, 'Unauthorized request')
        except DataFailureException as err:
            return self.error_response(500, err.msg)
        except Exception as err:
            return self.error_response(404, err)
