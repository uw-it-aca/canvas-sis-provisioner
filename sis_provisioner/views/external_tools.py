# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from sis_provisioner.models import Account
from sis_provisioner.models.external_tools import ExternalTool
from sis_provisioner.views.admin import RESTDispatch, get_user
from restclients_core.exceptions import DataFailureException
from logging import getLogger
import json
import re

logger = getLogger(__name__)


class ExternalToolView(RESTDispatch):
    """ Retrieves an ExternalTool model.
        GET returns 200 with ExternalTool details.
        PUT returns 200.
    """
    def get(self, request, *args, **kwargs):
        canvas_id = kwargs['canvas_id']
        read_only = not self.can_manage_external_tools(request)
        try:
            external_tool = ExternalTool.objects.get(canvas_id=canvas_id)
            data = external_tool.json_data()
            data['read_only'] = read_only

            if not read_only:
                shared_secret = external_tool.get_shared_secret()
                data['config']['shared_secret'] = shared_secret

        except ExternalTool.DoesNotExist:
            return self.error_response(
                404, "ExternalTool {} not found".format(canvas_id))

        return self.json_response({'external_tool': data})

    def put(self, request, *args, **kwargs):
        if not self.can_manage_external_tools(request):
            return self.error_response(401, "Unauthorized")

        canvas_id = kwargs['canvas_id']
        try:
            json_data = json.loads(request.body).get('external_tool', {})
            self._validate(json_data)
        except Exception as ex:
            logger.error('PUT ExternalTool error: {}'.format(ex))
            return self.error_response(400, ex)

        try:
            external_tool = ExternalTool.objects.update_tool(
                canvas_id, json_data['config'], get_user(request))

            logger.info('{} updated ExternalTool {}'.format(
                external_tool.changed_by, external_tool.canvas_id))

        except ExternalTool.DoesNotExist:
            return self.error_response(
                404, "ExternalTool {} not found".format(canvas_id))
        except DataFailureException as err:
            return self.error_response(500, "{}: {}".format(
                err.status, err.msg))

        return self.json_response({
            'external_tool': external_tool.json_data()})

    def post(self, request, *args, **kwargs):
        if not self.can_manage_external_tools(request):
            return self.error_response(401, "Unauthorized")

        try:
            json_data = json.loads(request.body).get('external_tool', {})
            self._validate(json_data)
        except Exception as ex:
            logger.error('POST ExternalTool error: {}'.format(ex))
            return self.error_response(400, ex)

        account_id = json_data['account_id']
        try:
            external_tool = ExternalTool.objects.create_tool(
                account_id, json_data['config'], get_user(request))

            logger.info('{} created ExternalTool {}'.format(
                external_tool.changed_by, external_tool.canvas_id))

        except Account.DoesNotExist:
            return self.error_response(
                400, "Unknown account_id {}".format(account_id))
        except DataFailureException as err:
            return self.error_response(500, "{}: {}".format(
                err.status, err.msg))

        return self.json_response({
            'external_tool': external_tool.json_data()})

    def delete(self, request, *args, **kwargs):
        if not self.can_manage_external_tools(request):
            return self.error_response(401, "Unauthorized")

        canvas_id = kwargs['canvas_id']
        try:
            ExternalTool.objects.delete_tool(canvas_id)
        except ExternalTool.DoesNotExist:
            return self.error_response(
                404, "ExternalTool {} not found".format(canvas_id))
        except DataFailureException as err:
            if err.status == 404:
                pass
            else:
                return self.error_response(
                    500, "{}: {}".format(err.status, err.msg))

        logger.info('{} deleted ExternalTool "{}"'.format(
            external_tool.changed_by, external_tool.canvas_id))

        return self.json_response({
            'external_tool': external_tool.json_data()})

    def _validate(self, json_data):
        account_id = json_data.get('account_id', None)
        if account_id is None or not len(account_id):
            raise Exception('Subaccount ID is required')
        elif re.match(r'^\d+$', account_id) is None:
            raise Exception('Subaccount ID is invalid')

        config = json_data.get('config', {})
        name = config.get('name', None)
        if name is None or not len(name):
            raise Exception('name is required')

        privacy_level = config.get('privacy_level', None)
        if privacy_level is None or not len(privacy_level):
            raise Exception('privacy_level is required')

        consumer_key = config.get('consumer_key', None)
        if consumer_key is None or not len(consumer_key):
            raise Exception('consumer_key is required')


class ExternalToolListView(RESTDispatch):
    """ Retrieves a list of ExternalTool models.
    """
    def get(self, request, *args, **kwargs):
        read_only = not self.can_manage_external_tools(request)
        external_tools = []
        for external_tool in ExternalTool.objects.all():
            data = external_tool.json_data()
            data['read_only'] = read_only
            del data['config']
            external_tools.append(data)

        return self.json_response({'external_tools': external_tools})
