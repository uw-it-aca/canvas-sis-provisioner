from django.conf import settings
from django.http import HttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from sis_provisioner.views import group_required
import json


@method_decorator(group_required(settings.CANVAS_MANAGER_ADMIN_GROUP),
                  name='dispatch')
class RESTDispatch(View):
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
