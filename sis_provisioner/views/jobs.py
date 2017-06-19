from logging import getLogger
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from sis_provisioner.models import Job
from sis_provisioner.views.rest_dispatch import RESTDispatch
from sis_provisioner.views.admin import can_manage_jobs
from userservice.user import UserService
from django.utils.timezone import utc
from datetime import datetime
import json


logger = getLogger(__name__)


class JobView(RESTDispatch):
    """ Retrieves a Job model.
        GET returns 200 with Job details.
        PUT returns 200.
    """
    def get(self, request, *args, **kwargs):
        job_id = kwargs['job_id']
        try:
            job = Job.objects.get(id=job_id)
            return self.json_response(job.json_data())
        except Job.DoesNotExist:
            return self.error_response(404, "Job %s not found" % job_id)

    @method_decorator(login_required)
    def put(self, request, *args, **kwargs):
        if not can_manage_jobs():
            return self.error_response(401, "Unauthorized")

        job_id = kwargs['job_id']
        try:
            job = Job.objects.get(id=job_id)

            data = json.loads(request.body).get('job', {})
            if 'is_active' in data:
                job.is_active = data['is_active']
                job.changed_by = UserService().get_original_user()
                job.changed_date = datetime.utcnow().replace(tzinfo=utc)
                job.save()

                logger.info('%s %s Job "%s"' % (
                    job.changed_by,
                    'enabled' if job.is_active else 'disabled',
                    job.name))

            return self.json_response({'job': job.json_data()})
        except Job.DoesNotExist:
            return self.error_response(404, "Job %s not found" % job_id)

    @method_decorator(login_required)
    def delete(self, request, *args, **kwargs):
        if not can_manage_jobs():
            return self.error_response(401, "Unauthorized")

        job_id = kwargs['job_id']
        try:
            job = Job.objects.get(id=job_id)
            job.delete()

            logger.info('%s deleted Job "%s"' % (job.changed_by, job.name))

            return self.json_response({'job': job.json_data()})
        except Job.DoesNotExist:
            return self.error_response(404, "Job %s not found" % job_id)


class JobListView(RESTDispatch):
    """ Retrieves a list of Jobs.
    """
    def get(self, request, *args, **kwargs):
        read_only = False if can_manage_jobs() else True
        jobs = []
        for job in Job.objects.all().order_by('title'):
            data = job.json_data()
            data['read_only'] = read_only
            jobs.append(data)

        return self.json_response({'jobs': jobs})
