from django.conf import settings
from django.utils.decorators import method_decorator
from sis_provisioner.models import Group
from sis_provisioner.views.rest_dispatch import RESTDispatch
from sis_provisioner.views import group_required


@method_decorator(group_required(settings.CANVAS_MANAGER_ADMIN_GROUP),
                  name='dispatch')
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
