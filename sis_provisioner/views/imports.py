# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

import json
from logging import getLogger

from django.core.management import call_command

from sis_provisioner.models import Import
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
            return self.error_response(404, f"Import {import_id} not found")
        except ImportInvalidException as err:
            return self.error_response(400, err)

    def post(self, request, *args, **kwargs):
        body = json.loads(request.read())
        mode = body.get('mode', None)
        if mode == 'group':
            logger.info(f'imports ({request.user}): POST: import_group')
            call_command('import_groups')
            return self.json_response({"import": "started"})
        else:
            logger.info(f'imports ({request.user}): POST: unknown command')
            return self.error_response(400, "Unknown import mode")

    def delete(self, request, *args, **kwargs):
        import_id = kwargs['import_id']
        try:
            imp = Import.objects.get(id=import_id)

            logger.info(
                f'imports ({request.user}): DELETE: type: {imp.csv_type}, '
                f'queue_id: {imp.pk}, post_status: {imp.post_status}, '
                f'canvas_state: {imp.canvas_state}'
            )

            imp.delete()

            return self.json_response()

        except Import.DoesNotExist:
            return self.error_response(404, f"Import {import_id} not found")
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
