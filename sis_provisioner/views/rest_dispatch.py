from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import HttpResponse
from django.views import View
import json
import re


@method_decorator(login_required, name='dispatch')
class RESTDispatch(View):
    @staticmethod
    def error_response(self, status, message='', content={}):
        content['error'] = message
        return HttpResponse(json.dumps(content),
                            status=status,
                            content_type='application/json')

    @staticmethod
    def json_response(self, content='', status=200):
        return HttpResponse(json.dumps(content, sort_keys=True),
                            status=status,
                            content_type='application/json')
