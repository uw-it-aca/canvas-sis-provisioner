from django.http import HttpResponse
from django.views import View
import json


class RESTDispatch(View):
    def error_response(self, status, message='', content={}):
        content['error'] = '%s' % message
        return HttpResponse(json.dumps(content),
                            status=status,
                            content_type='application/json')

    def json_response(self, content='', status=200):
        return HttpResponse(json.dumps(content, sort_keys=True),
                            status=status,
                            content_type='application/json')
