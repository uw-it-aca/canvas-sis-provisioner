from django.contrib.auth.decorators import login_required
from sis_provisioner.models import Group
from sis_provisioner.views.rest_dispatch import RESTDispatch


class GroupListView(RESTDispatch):
    """ Performs query of Group models at /api/v1/groups/?.
        GET returns 200 with Group models
    """
    @login_required
    def get(self, request, *args, **kwargs):
        json_rep = {
            'groups': []
        }

        group_list = list(Group.objects.all())
        for group in group_list:
            json_rep['groups'].append(group.json_data())

        return self.json_response(json_rep)
