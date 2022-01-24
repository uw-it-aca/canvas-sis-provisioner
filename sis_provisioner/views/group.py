# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from sis_provisioner.models.group import Group
from sis_provisioner.views.admin import RESTDispatch


class GroupListView(RESTDispatch):
    """ Performs query of Group models at /api/v1/groups/?.
        GET returns 200 with Group models
    """
    def get(self, request, *args, **kwargs):
        json_rep = {
            'groups': []
        }

        group_list = list(Group.objects.all())
        for group in group_list:
            json_rep['groups'].append(group.json_data())

        return self.json_response(json_rep)
