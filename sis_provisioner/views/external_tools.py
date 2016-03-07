from django.utils.log import getLogger
from sis_provisioner.models import ExternalTool, ExternalToolSubaccount
from sis_provisioner.views.rest_dispatch import RESTDispatch
from userservice.user import UserService
from canvas_admin.views import can_manage_external_tools
from django.utils.timezone import utc
from datetime import datetime
import json


class ExternalToolView(RESTDispatch):
    """ Retrieves an ExternalTool model.
        GET returns 200 with ExternalTool details.
        PUT returns 200.
    """
    def __init__(self):
        self._log = getLogger(__name__)

    def GET(self, request, **kwargs):
        external_tool_id = kwargs['external_tool_id']
        try:
            external_tool = ExternalTool.objects.get(id=external_tool_id)
            return self.json_response(json.dumps(external_tool.json_data()))
        except ExternalTool.DoesNotExist:
            return self.json_response(
                '{"error":"external tool %s not found"}' % external_tool_id,
                status=404)

    def PUT(self, request, **kwargs):
        if not can_manage_external_tools():
            return self.json_response('{"error":"Unauthorized"}', status=401)

        external_tool_id = kwargs['external_tool_id']
        try:
            json_data = json.loads(request.body).get('external_tool', {})
        except Exception as ex:
            self._log.error('PUT ExternalTool error: %s' % ex)
            return self.json_response('{"error": "%s"}' % ex, status=400)

        try:
            external_tool = ExternalTool.objects.get(id=external_tool_id)
        except ExternalTool.DoesNotExist:
            return self.json_response(
                '{"error":"external_tool %s not found"}' % external_tool_id,
                status=404)

        for key, value in json_data.items():
            if hasattr(external_tool, key):
                if key != 'canvas_id':
                    setattr(external_tool, key, value)
                # TODO: handle subaccounts and custom_fields attributes

        external_tool.changed_by = UserService().get_original_user()
        external_tool.changed_date = datetime.utcnow().replace(tzinfo=utc)
        external_tool.save()

        # TODO: update Canvas

        self._log.info('%s updated External Tool "%s"' % (
            external_tool.changed_by, external_tool.name))

        return self.json_response(json.dumps({
            'external_tool': external_tool.json_data()}))

    def POST(self, request, **kwargs):
        if not can_manage_external_tools():
            return self.json_response('{"error":"Unauthorized"}', status=401)

        try:
            json_data = json.loads(request.body).get('external_tool', {})
        except Exception as ex:
            self._log.error('POST ExternalTool error: %s' % ex)
            return self.json_response('{"error": "%s"}' % ex, status=400)

        external_tool = ExternalTool()

        for key, value in json_data.items():
            if hasattr(external_tool, key):
                setattr(external_tool, key, value)
                # TODO: handle subaccounts and custom_fields attributes

        external_tool.changed_by = UserService().get_original_user()
        external_tool.changed_date = datetime.utcnow().replace(tzinfo=utc)
        external_tool.save()

        # TODO: update Canvas

        self._log.info('%s added External Tool "%s"' % (
            external_tool.changed_by, external_tool.name))

        return self.json_response(json.dumps({
            'external_tool': external_tool.json_data()}))

    def DELETE(self, request, **kwargs):
        if not can_manage_external_tools():
            return self.json_response('{"error":"Unauthorized"}', status=401)

        external_tool_id = kwargs['external_tool_id']
        try:
            external_tool = ExternalTool.objects.get(id=external_tool_id)
            external_tool.delete()

            # TODO: delete from Canvas

            self._log.info('%s deleted ExternalTool "%s"' % (
                external_tool.changed_by, external_tool.name))

            return self.json_response(json.dumps({
                'external_tool': external_tool.json_data()}))
        except ExternalTool.DoesNotExist:
            return self.json_response(
                '{"error":"external_tool %s not found"}' % external_tool_id,
                status=404)


class ExternalToolListView(RESTDispatch):
    """ Retrieves a list of ExternalTools.
    """
    def GET(self, request, **kwargs):
        read_only = False if can_manage_external_tools() else True
        external_tools = []
        for external_tool in ExternalTool.objects.all().order_by('name'):
            data = external_tool.json_data()
            data['read_only'] = read_only
            external_tools.append(data)

        return self.json_response(
            json.dumps({'external_tools': external_tools}))
