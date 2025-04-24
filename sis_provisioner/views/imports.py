# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


import re
import json
import dateutil.parser
from logging import getLogger
from django.core.management import call_command
from sis_provisioner.models import Import
from sis_provisioner.models.user import User
from sis_provisioner.views.admin import RESTDispatch

logger = getLogger(__name__)


class ImportInvalidException(Exception):
    pass


class ImportView(RESTDispatch):
    """ Retrieves a an Import model]>.
        GET returns 200 with Import details.
        DELETE returns 200.
    """
    def get(self, request, *args, **kwargs):
        import_id = kwargs['import_id']
        try:
            imp = Import.objects.get(id=import_id)
            return self.json_response(imp.json_data())
        except Import.DoesNotExist:
            return self.error_response(
                404, "Import {} not found".format(import_id))
        except ImportInvalidException as err:
            return self.error_response(400, err)

    def post(self, request, *args, **kwargs):
        body = json.loads(request.read())
        mode = body.get('mode', None)
        if mode == 'group':
            logger.info(
                'imports ({}): POST: import_group'.format(request.user))
            call_command('import_groups')
            return self.json_response({"import": "started"})
        else:
            logger.info(
                'imports ({}): POST: unknown command'.format(request.user))
            return self.error_response(400, "Unknown import mode")

    def delete(self, request, *args, **kwargs):
        import_id = kwargs['import_id']
        try:
            imp = Import.objects.get(id=import_id)

            logger.info(
                'imports ({}): DELETE: type: {}, queue_id: {}, '
                'post_status: {}, canvas_state: {}'.format(
                    request.user, imp.csv_type, imp.pk, imp.post_status,
                    imp.canvas_state))

            imp.delete()

            return self.json_response()

        except Import.DoesNotExist:
            return self.error_response(
                404, "Import {} not found".format(import_id))
        except ImportInvalidException as err:
            return self.error_response(400, err)


class ImportListView(RESTDispatch):
    """ Retrieves a list of Imports at /api/v1/imports/?<criteria[&criteria]>.
        GET returns 200 with Import details.
    """
    def get(self, request, *args, **kwargs):
        json_rep = {
            'imports': []
        }

        try:
            import_list = Import.objects.all().order_by('added_date')
        except ImportInvalidException as err:
            return self.error_response(400, err)

        for imp in import_list:
            json_rep['imports'].append(imp.json_data())

        return self.json_response(json_rep)
