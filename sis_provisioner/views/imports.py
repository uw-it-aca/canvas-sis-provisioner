import re
import json
import dateutil.parser
from django.utils.timezone import utc
from django.utils.log import getLogger
from django.core.management import call_command
from sis_provisioner.models import Import, User
from sis_provisioner.views.rest_dispatch import RESTDispatch


class ImportInvalidException(Exception):
    pass


class ImportView(RESTDispatch):
    """ Retrieves a an Import model]>.
        GET returns 200 with Import details.
        DELETE returns 200.
    """
    def __init__(self):
        self._log = getLogger(__name__)

    def GET(self, request, **kwargs):
        try:
            imp = Import.objects.get(id=kwargs['import_id'])
            return self.json_response(json.dumps(imp.json_data()))
        except Import.DoesNotExist:
            return self.json_response(
                '{"error":"import %s not found"}' % (kwargs['import_id']),
                status=404)
        except ImportInvalidException as err:
            return self.json_response('{"error":"%s"}' % err, status=400)

    def POST(self, request, **kwargs):
        body = json.loads(request.read())
        mode = body.get('mode', None)
        if mode == 'group':
            self._log.info('imports (%s): POST: import_group' % (
                request.user))
            call_command('import_groups')
            json_rep = {"import": "started"}
            return self.json_response(json.dumps(json_rep))
        else:
            self._log.info('imports (%s): POST: unknown command' % (
                request.user))
            return self.json_response('{"error":"unknown import mode"}',
                                      status=400)

    def DELETE(self, request, **kwargs):
        import_id = kwargs['import_id']
        try:
            imp = Import.objects.get(id=import_id)

            self._log.info(
                'imports (%s): DELETE: type: %s, queue_id: %s, '
                'post_status: %s, canvas_state: %s' % (
                    request.user, imp.csv_type, imp.pk, imp.post_status,
                    imp.canvas_state))

            imp.delete()

            return self.json_response('{}')

        except Import.DoesNotExist:
            return self.json_response('{"error":"import %s not found"}' % (
                import_id), status=404)
        except ImportInvalidException as err:
            return self.json_response('{"error":"%s"}' % err, status=400)


class ImportListView(RESTDispatch):
    """ Retrieves a list of Imports at /api/v1/imports/?<criteria[&criteria]>.
        GET returns 200 with Import details.
    """
    def GET(self, request, **kwargs):
        json_rep = {
            'imports': []
        }

        try:
            import_list = list(Import.objects.all())
        except ImportInvalidException as err:
            return self.json_response('{"error":"%s"}' % err, status=400)

        for imp in import_list:
            json_rep['imports'].append(imp.json_data())

        return self.json_response(json.dumps(json_rep))
