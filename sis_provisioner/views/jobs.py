import re
import json
import dateutil.parser
from django.utils.timezone import utc
from django.utils.log import getLogger
from django.core.management import call_command
from sis_provisioner.models import Job
from sis_provisioner.views.rest_dispatch import RESTDispatch


class JobView(RESTDispatch):
    """ Retrieves a Job model.
        GET returns 200 with Job details.
        PUT returns 200.
    """
    def __init__(self):
        self._log = getLogger(__name__)

    def GET(self, request, **kwargs):
        job_id = kwargs['job_id']
        try:
            job = Job.objects.get(id=job_id)
            return self.json_response(json.dumps(job.json_data()))
        except Job.DoesNotExist:
            return self.json_response(
                '{"error":"job %s not found"}' % job_id, status=404)

    def PUT(self, request, **kwargs):
        job_id = kwargs['job_id']
        try:
            job = Job.objects.get(id=job_id)
            job.is_active = False if (job.is_active is True) else True
            job.save()
            return self.json_response(json.dumps(job.json_data()))
        except Job.DoesNotExist:
            return self.json_response(
                '{"error":"job %s not found"}' % job_id, status=404)


class ImportListView(RESTDispatch):
    """ Retrieves a list of Jobs.
    """
    def GET(self, request, **kwargs):
        jobs = []
        for job in Job.objects.all():
            jobs.append(job.json_data())

        return self.json_response(json.dumps({'jobs': jobs}))
