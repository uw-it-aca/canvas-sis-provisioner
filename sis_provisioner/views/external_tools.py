from logging import getLogger
from sis_provisioner.models import Account
from sis_provisioner.models.external_tools import ExternalTool
from sis_provisioner.views.admin import RESTDispatch, get_user
from sis_provisioner.dao.canvas import get_account_by_id
from uw_canvas.external_tools import ExternalTools
from restclients_core.exceptions import DataFailureException
from django.utils.timezone import utc
from blti.models import BLTIKeyStore
from datetime import datetime
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
                keystore = BLTIKeyStore.objects.get(
                    consumer_key=data['consumer_key'])
                data['config']['shared_secret'] = keystore.shared_secret

        except ExternalTool.DoesNotExist:
            return self.error_response(
                404, "External tool {} not found".format(canvas_id))
        except BLTIKeyStore.DoesNotExist:
            pass

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
            external_tool = ExternalTool.objects.get(canvas_id=canvas_id)
            curr_data = external_tool.json_data()
            keystore = BLTIKeyStore.objects.get(
                consumer_key=curr_data['consumer_key'])
        except ExternalTool.DoesNotExist:
            return self.error_response(
                404, "External_tool {} not found".format(canvas_id))
        except BLTIKeyStore.DoesNotExist:
            keystore = BLTIKeyStore()

        # PUT does not update canvas_id or account_id
        external_tool.config = json.dumps(json_data['config'])
        external_tool.changed_by = get_user(request)
        external_tool.changed_date = datetime.utcnow().replace(tzinfo=utc)
        external_tool.save()

        keystore.consumer_key = json_data['config']['consumer_key']

        shared_secret = json_data['config']['shared_secret']
        if (shared_secret is None or not len(shared_secret)):
            del json_data['config']['shared_secret']
        else:
            keystore.shared_secret = shared_secret

        try:
            new_config = ExternalTools().update_external_tool_in_account(
                external_tool.account.canvas_id, json_data['config']['id'],
                json_data['config'])

            external_tool.canvas_id = new_config.get('id')
            external_tool.config = json.dumps(new_config)
            external_tool.provisioned_date = datetime.utcnow().replace(
                tzinfo=utc)
            external_tool.save()
            if keystore.shared_secret:
                keystore.save()

            logger.info('{} updated External Tool "{}"'.format(
                external_tool.changed_by, external_tool.canvas_id))

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
        canvas_id = json_data['config'].get('id')

        try:
            account = Account.objects.get(canvas_id=account_id)
        except Account.DoesNotExist:
            return self.error_response(
                400, "Unknown account_id {}".format(account_id))

        try:
            external_tool = ExternalTool.objects.get(canvas_id=canvas_id)
            return self.error_response(
                400, "External tool {} already exists".format(ex))
        except ExternalTool.DoesNotExist:
            pass

        external_tool = ExternalTool(canvas_id=canvas_id)
        external_tool.account = account
        external_tool.config = json.dumps(json_data['config'])
        external_tool.changed_by = get_user(request)
        external_tool.changed_date = datetime.utcnow().replace(tzinfo=utc)

        try:
            keystore = BLTIKeyStore.objects.get(
                consumer_key=json_data['config']['consumer_key'])
            # Re-using an existing key/secret (clone?)
            json_data['config']['shared_secret'] = keystore.shared_secret

        except BLTIKeyStore.DoesNotExist:
            keystore = BLTIKeyStore()
            keystore.consumer_key = json_data['config']['consumer_key']

            shared_secret = json_data['config']['shared_secret']
            if (shared_secret is None or not len(shared_secret)):
                if not canvas_id:
                    # New external tool, generate a secret
                    shared_secret = external_tool.generate_shared_secret()
                    keystore.shared_secret = shared_secret
                    json_data['config']['shared_secret'] = shared_secret
                else:
                    # Existing external tool, don't overwrite the secret
                    del json_data['config']['shared_secret']

            keystore.save()

        try:
            if not canvas_id:
                new_config = ExternalTools().create_external_tool_in_account(
                    account_id, json_data['config'])

                logger.info('{} created External Tool "{}"'.format(
                    external_tool.changed_by, new_config.get('id')))

            else:
                new_config = ExternalTools().update_external_tool_in_account(
                    account_id, canvas_id, json_data['config'])

                logger.info('{} updated External Tool "{}"'.format(
                    external_tool.changed_by, new_config.get('id')))

            external_tool.canvas_id = new_config.get('id')
            external_tool.config = json.dumps(new_config)
            external_tool.provisioned_date = datetime.utcnow().replace(
                tzinfo=utc)
            external_tool.save()

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
            external_tool = ExternalTool.objects.get(canvas_id=canvas_id)
            curr_data = external_tool.json_data()
            keystore = BLTIKeyStore.objects.get(
                consumer_key=curr_data['consumer_key'])

        except ExternalTool.DoesNotExist:
            return self.error_response(
                404, "External_tool {} not found".format(canvas_id))
        except BLTIKeyStore.DoesNotExist:
            keystore = None

        try:
            ExternalTools().delete_external_tool_in_account(
                curr_data['account_id'], curr_data['config']['id'])
        except DataFailureException as err:
            if err.status == 404:
                pass
            else:
                return self.error_response(
                    500, "{}: {}".format(err.status, err.msg))

        external_tool.delete()
        if keystore is not None:
            keystore.delete()

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
    """ Retrieves a list of ExternalTools.
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
