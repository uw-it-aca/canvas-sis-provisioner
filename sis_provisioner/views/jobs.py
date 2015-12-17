from django.utils.log import getLogger
from sis_provisioner.models import Job
from sis_provisioner.views.rest_dispatch import RESTDispatch
from canvas_admin.views import can_manage_jobs
import json


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
        if not can_manage_jobs():
            return self.json_response('{"error":"Unauthorized"}', status=401)

        job_id = kwargs['job_id']
        try:
            job = Job.objects.get(id=job_id)

            data = json.loads(request.body).get('job', {})
            if hasattr(data, 'is_active'):
                job.is_active = True if data.get('is_active') else False
                job.save()

            return self.json_response(json.dumps(job.json_data()))
        except Job.DoesNotExist:
            return self.json_response(
                '{"error":"job %s not found"}' % job_id, status=404)


class JobListView(RESTDispatch):
    """ Retrieves a list of Jobs.
    """
    def GET(self, request, **kwargs):
        read_only = False if can_manage_jobs() else True
        jobs = []
        for job in Job.objects.all():
            data = job.json_data()
            data['read_only'] = read_only
            jobs.append(data)

        return self.json_response(json.dumps({'jobs': jobs}))
